#!/usr/bin/env python3
"""Runs the GPU jobs in infra/jobs on a Labqoat Forgehand session, over HTTPS only.

Forgehand (app.forgehand.app) gives a workspace (persistent /workspace) and GPU
sessions attached to it. We drive a session through its JupyterLab (REST API plus
terminal websocket), so no SSH is needed: Claude's cloud sandbox can't reach port 22.

    pip install requests websocket-client; npm install -g @qforge/forgehand
    export FORGEHAND_TOKEN=fh_...       # Settings -> Access tokens (or run `fh login`)
    infra/forgehand/fh_job.py classes                     # GPU classes and prices
    infra/forgehand/fh_job.py start --class <slug>        # prints the session id
    infra/forgehand/fh_job.py run <session> baselines MODELS=qwen3-8b JUDGE_HF=
    infra/forgehand/fh_job.py log <session>               # tail of the job log
    infra/forgehand/fh_job.py exec <session> 'nvidia-smi' # any shell command
    infra/forgehand/fh_job.py fetch <session> runs/fh/<name>  # summaries + report
    infra/forgehand/fh_job.py stop <session>              # billing stops; /workspace kept

`run` ships `git archive HEAD` (commit first) plus local data/eval/matura.jsonl and
data/train/synthetic.jsonl, unpacks them into /workspace/repo, and starts the job
detached with nohup. Outputs go to /workspace/work/out/<job>-<time>/, the log to
/workspace/work/<job>-<time>.log; the venv and adapters live in /workspace/work; Hugging Face
downloads are cached in /team/hf so every session and workspace reuses them.
WORKSPACE (default: the team workspace below) selects another workspace.
WAIT_GPU=1 makes `run` wait until the GPU is free (the team may run only one GPU session).
start, run, stop and a `log` that sees the job finish update docs/STATUS.md on main.
"""
import base64, io, json, os, re, shlex, ssl, subprocess, sys, tarfile, time, uuid
from urllib.parse import urlparse

import requests
import websocket

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jobs"))
from status import update as status  # docs/STATUS.md, committed and pushed on each change

WORKSPACE = os.environ.get("WORKSPACE", "01a0dd4b-4c82-73b7-8d65-9b217e851030")
REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                      text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
OWNER = os.environ.get("OWNER", "Forgehand wrapper")
CA = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")


def fh(*args):
    """Calls the fh CLI with --json and returns the parsed output."""
    env = dict(os.environ, NODE_USE_ENV_PROXY="1")
    r = subprocess.run(["fh", *args, "--json"], capture_output=True, text=True, env=env)
    if r.returncode:
        sys.exit(f"fh {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


class Jupyter:
    """A logged-in JupyterLab of one session: REST calls and terminal commands."""

    def __init__(self, session):
        handoff = fh("session", "jupyter", session)["url"]
        self.http = requests.Session()
        r = self.http.get(handoff, allow_redirects=True, timeout=60)
        r.raise_for_status()
        u = urlparse(r.url)
        path = re.split(r"/(lab|tree|login)\b", u.path)[0].rstrip("/")
        self.base = f"{u.scheme}://{u.netloc}{path}"
        tok = dict(p.split("=", 1) for p in (urlparse(handoff).query or "").split("&") if "=" in p)
        if "token" in tok:
            self.http.headers["Authorization"] = f"token {tok['token']}"
        xsrf = self.http.cookies.get("_xsrf")
        if xsrf:
            self.http.headers["X-XSRFToken"] = xsrf
        self.api("GET", "/api/status")

    def api(self, method, path, **kw):
        r = self.http.request(method, self.base + path, timeout=300, **kw)
        if r.status_code >= 400:
            sys.exit(f"{method} {path}: {r.status_code} {r.text[:300]}")
        return r.json() if r.content else None

    def put_file(self, path, data):
        """Uploads bytes to a path relative to the Jupyter root (parents must exist)."""
        body = {"type": "file", "format": "base64", "content": base64.b64encode(data).decode()}
        self.api("PUT", "/api/contents/" + path, json=body)

    def get_file(self, path):
        m = self.api("GET", "/api/contents/" + path, params={"content": 1, "format": "base64"})
        return base64.b64decode(m["content"])

    def sh(self, cmd, timeout=600):
        """Runs a bash command in a fresh terminal (cwd = Jupyter root); returns its output."""
        name = self.api("POST", "/api/terminals")["name"]
        ws_url = self.base.replace("https://", "wss://").replace("http://", "ws://")
        headers = [f"{k}: {v}" for k, v in self.http.headers.items() if k in ("Authorization",)]
        cookie = "; ".join(f"{c.name}={c.value}" for c in self.http.cookies)
        proxy = urlparse(os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "")
        ws = websocket.create_connection(
            f"{ws_url}/terminals/websocket/{name}", header=headers, cookie=cookie or None,
            http_proxy_host=proxy.hostname, http_proxy_port=proxy.port,
            proxy_type="http" if proxy.hostname else None,
            sslopt={"ca_certs": CA} if CA else {}, timeout=timeout)
        mark = uuid.uuid4().hex[:12]
        # stty -echo keeps the command itself out of the captured output.
        script = f"stty -echo; {{ {cmd}\n}} 2>&1; echo; echo __END_{mark}_$?\n"
        ws.send(json.dumps(["stdin", script]))
        out, deadline = "", time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            if msg[0] == "stdout":
                out += msg[1]
                m = re.search(rf"__END_{mark}_(\d+)", out)
                if m:
                    break
        ws.close()
        self.api("DELETE", f"/api/terminals/{name}")
        m = re.search(rf"__END_{mark}_(\d+)", out)
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out[: m.start()] if m else out)
        # Drop the echoed command (it can arrive before stty -echo takes effect).
        text = text.replace("\r", "").split(f"echo __END_{mark}_$?", 1)[-1].strip()
        return text, (int(m.group(1)) if m else None)


def code_tarball(extra):
    """git archive of HEAD plus untracked data files, as one tar.gz."""
    head = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=REPO,
                          capture_output=True, check=True).stdout
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as out, \
            tarfile.open(fileobj=io.BytesIO(head)) as src:
        for m in src.getmembers():
            out.addfile(m, src.extractfile(m) if m.isfile() else None)
        for rel in extra:
            if os.path.isfile(os.path.join(REPO, rel)):
                out.add(os.path.join(REPO, rel), arcname=rel)
    return buf.getvalue()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "classes":
        subprocess.run(["fh", "classes"], env=dict(os.environ, NODE_USE_ENV_PROXY="1"))
    elif cmd == "start":
        cls = args[args.index("--class") + 1] if "--class" in args else None
        s = fh("session", "start", WORKSPACE, *(["--class", cls] if cls else []), "--wait")
        print(s["id"], s.get("state"), s.get("cls") or cls or "")
        status(f"fh-session-{s['id'][:8]}", state=s.get("state", "running"),
               where=f"Forgehand {s.get('cls') or cls or 'default GPU'}",
               what="GPU session (billed while it exists)", owner=OWNER)
    elif cmd == "ls":
        for s in fh("session", "ls", WORKSPACE):
            print(s["id"], s.get("state"), s.get("cls"), s.get("costMicroUsd", 0) / 1e6, "USD")
    elif cmd == "stop":
        fh("session", "stop", args[0])
        print("stopping", args[0])
        status(f"fh-session-{args[0][:8]}", state="stopped", owner=OWNER)
    elif cmd == "exec":
        out, code = Jupyter(args[0]).sh(args[1], timeout=int(os.environ.get("TIMEOUT", 600)))
        print(out)
        sys.exit(code or 0)
    elif cmd == "run":
        session, job, env = args[0], args[1], args[2:]
        name = os.environ.get("NAME") or f"{job}-{time.strftime('%m%d-%H%M', time.gmtime())}"
        j = Jupyter(session)
        root, _ = j.sh("pwd")
        rel = os.path.relpath("/workspace", root) if root.startswith("/") else "/workspace"
        rel = "" if rel == "." else rel + "/"  # Jupyter rejects "./" and hidden (dot) paths
        tar = code_tarball(["data/eval/matura.jsonl", "data/train/synthetic.jsonl"])
        j.sh(f"mkdir -p {rel}work/upload")
        j.put_file(f"{rel}work/upload/{name}.tar.gz", tar)
        env_s = " ".join(shlex.quote(e) for e in env)
        # WAIT_GPU=1: the team has one GPU session, so queue behind whatever holds the card.
        wait = ("while [ $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | "
                "sort -n | tail -1) -gt 2000 ]; do echo waiting for a free GPU; sleep 60; done"
                if os.environ.get("WAIT_GPU") == "1" else "")
        # Fresh code dir per run; venv, adapters and HF cache are shared across runs.
        script = (f"set -e\nmkdir -p /workspace/runs/{name} /workspace/work /team/hf\n"
                  f"tar xzf /workspace/work/upload/{name}.tar.gz -C /workspace/runs/{name}\n"
                  f"cd /workspace/runs/{name}\n{wait}\n"
                  f"export WORK=/workspace/work OUT=/workspace/work/out/{name} HF_HOME=/team/hf "
                  f"NAME={name} {env_s}\nexec bash infra/jobs/{job}.sh\n")
        j.put_file(f"{rel}work/upload/{name}.sh", script.encode())
        # setsid detaches the job from the terminal, which is deleted right after.
        run = (f"setsid nohup bash /workspace/work/upload/{name}.sh > /workspace/work/{name}.log "
               f"2>&1 < /dev/null & sleep 3; echo started pid $!")
        out, _ = j.sh(run)
        print(out)
        print(f"job {name}: log with `fh_job.py log {session} {name}`")
        status(name, state="running", where=f"Forgehand session {session[:8]}",
               what=" ".join([job, *env]), out=f"/workspace/work/out/{name}", owner=OWNER)
    elif cmd == "log":
        j = Jupyter(args[0])
        pat = f"/workspace/work/{args[1]}.log" if len(args) > 1 else "$(ls -t /workspace/work/*.log | head -1)"
        out, _ = j.sh(f"tail -n {os.environ.get('LINES', 40)} {pat}; nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader")
        print(out)
        # The job's last line is "== HH:MM:SS done (exit N); ..." (infra/jobs/common.sh).
        done = re.findall(r"done \(exit (\d+)\)", out)
        if len(args) > 1 and done:
            status(args[1], state="done" if done[-1] == "0" else f"failed (exit {done[-1]})", owner=OWNER)
    elif cmd == "fetch":
        session, dest = args[0], args[1]
        name = os.environ.get("NAME")
        j = Jupyter(session)
        src = f"/workspace/work/out/{name}" if name else "$(ls -td /workspace/work/out/*/ | head -1)"
        out, code = j.sh(f"cd {src} && tar czf /workspace/work/upload/fetch.tgz --exclude='*.safetensors' "
                         f"--exclude='vllm-*.log' . && pwd")
        if code:
            sys.exit(out)
        root, _ = j.sh("pwd")
        data = j.get_file(os.path.relpath("/workspace/work/upload/fetch.tgz", root))
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            t.extractall(dest)
        print(f"{out.splitlines()[-1]} -> {dest}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
