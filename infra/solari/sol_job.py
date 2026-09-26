#!/usr/bin/env python3
"""Runs CPU jobs from infra/jobs on Solari sandboxes (getsolari.com), over HTTPS only.

Solari has NO GPUs: a sandbox is a microVM with at most 8 vCPU, 16 GB RAM and a 20 GB disk.
Use it for CPU work that must not touch the GPU VM: scoring small GGUF quants with
scripts/cpu_serve.py (job `cpu_score`), data prep, and API-based judging.
Driven through the REST API (POST /sandboxes, /exec, signed file URLs); no SSH, no SDK.

    pip install requests
    export SOLARI_API_KEY=slr_live_...      # Project settings env var; never in chat or the repo
    infra/solari/sol_job.py start [--cpu 8] [--mem 16384] [--disk 20]   # prints the sandbox id
    infra/solari/sol_job.py ls
    infra/solari/sol_job.py run <sbx> cpu_score JOB_ID=matura-infer-qwen3-0.6b-may2023-20260926-1700-ab12 \
        MODEL=qwen3-0.6b GGUF_REPO=unsloth/Qwen3-0.6B-GGUF GGUF_FILE=Qwen3-0.6B-Q8_0.gguf
    infra/solari/sol_job.py log <sbx> [name]      # tail of the job log
    infra/solari/sol_job.py exec <sbx> 'nproc; free -g'
    infra/solari/sol_job.py fetch <sbx> <name> results/solari/<name>   # the job's $OUT, no weights
    infra/solari/sol_job.py stop <sbx>            # kills it; billing stops

`run` ships `git archive HEAD` (commit first) plus the local eval/train data and data/kb,
unpacks it to /root/runs/<name>, and starts infra/jobs/<job>.sh detached. Outputs go to
/root/work/out/<name>, the log to /root/work/<name>.log. NAME defaults to JOB_ID when given
(the G-018 job_id), else <job>-<time>. start, run, stop and a `log` that sees the job finish
update docs/STATUS.md on main (NO_PUSH=1 to skip the push).
Sandboxes pause after IDLE_MIN (default 120) minutes without API activity and lose running
processes, so poll `log` now and then during a long job, or pass a larger IDLE_MIN at start.
"""
import io, json, os, re, shlex, subprocess, sys, tarfile, time, uuid
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jobs"))
from status import update as status  # docs/STATUS.md, committed and pushed on each change

API = os.environ.get("SOLARI_API", "https://api.getsolari.com")
REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                      text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
OWNER = os.environ.get("OWNER", "Solari wrapper")
DATA = ["data/eval/matura.jsonl", "data/eval/matura_all.jsonl", "data/eval/matura_img.jsonl", "data/train/synthetic.jsonl",
        "data/train/past_papers.jsonl", "data/eval/images", "data/kb"]
MAX_UPLOAD = 32 * 1024 * 1024  # PUT /files/upload limit


def api(method, path, **kw):
    key = os.environ.get("SOLARI_API_KEY")
    if not key:
        sys.exit("SOLARI_API_KEY is not set")
    r = requests.request(method, API + path, timeout=kw.pop("timeout", 120),
                         headers={"Authorization": f"Bearer {key}", **kw.pop("headers", {})}, **kw)
    if r.status_code >= 400:
        sys.exit(f"{method} {path}: {r.status_code} {r.text[:400]}")
    return r.json() if r.content else None


def sid(s):
    return quote(s, safe="")


def sh(sbx, cmd, timeout=600):
    """Runs a shell line in the sandbox; returns (stdout+stderr, exit code)."""
    r = api("POST", f"/sandboxes/{sid(sbx)}/exec", timeout=timeout + 30,
            json={"cmd": "bash", "args": ["-lc", cmd], "timeoutMs": timeout * 1000})
    return (r.get("stdout", "") + r.get("stderr", "")).rstrip(), r.get("exitCode")


def put_file(sbx, path, data):
    url = api("GET", f"/sandboxes/{sid(sbx)}/files/upload-url", params={"path": path})["url"]
    for off in range(0, max(len(data), 1), MAX_UPLOAD):  # >32 MB: upload parts, join in the guest
        part = path if len(data) <= MAX_UPLOAD else f"{path}.part{off // MAX_UPLOAD:03d}"
        if part != path:
            url = api("GET", f"/sandboxes/{sid(sbx)}/files/upload-url", params={"path": part})["url"]
        r = requests.put(url, data=data[off:off + MAX_UPLOAD], timeout=600,
                         headers={"Content-Type": "application/octet-stream"})
        r.raise_for_status()
    if len(data) > MAX_UPLOAD:
        sh(sbx, f"cat {path}.part* > {path} && rm -f {path}.part*")


def get_file(sbx, path):
    url = api("GET", f"/sandboxes/{sid(sbx)}/files/download-url", params={"path": path})["url"]
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    return r.content


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
            if os.path.exists(os.path.join(REPO, rel)):
                out.add(os.path.join(REPO, rel), arcname=rel)
    return buf.getvalue()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    opt = lambda k, d: args[args.index(k) + 1] if k in args else d
    if cmd == "start":
        body = {"template": "base", "cpu": int(opt("--cpu", 8)), "memMb": int(opt("--mem", 16384)),
                "diskGb": int(opt("--disk", 20)), "metadata": {"project": "matura"},
                "timeoutMs": int(os.environ.get("IDLE_MIN", 120)) * 60_000,
                "lifecycle": {"onTimeout": "pause"}}
        s = api("POST", "/sandboxes", json=body, headers={"Idempotency-Key": str(uuid.uuid4())})
        print(s["sandboxId"], "expires", s.get("expiresAt"))
        status(f"sol-{s['sandboxId'][-8:]}", state="running",
               where=f"Solari sandbox {body['cpu']} vCPU/{body['memMb'] // 1024} GB (CPU only)",
               what="Solari CPU sandbox (billed to free credits while running)", owner=OWNER)
    elif cmd == "ls":
        r = api("GET", "/sandboxes")
        for s in r.get("sandboxes", r.get("data", [])) if isinstance(r, dict) else r:
            print(s.get("sandboxId"), s.get("state"), s.get("cpu"), s.get("memMb"), s.get("expiresAt"))
    elif cmd == "stop":
        api("DELETE", f"/sandboxes/{sid(args[0])}")
        print("killed", args[0])
        status(f"sol-{args[0][-8:]}", state="stopped", owner=OWNER)
    elif cmd == "exec":
        out, code = sh(args[0], args[1], timeout=int(os.environ.get("TIMEOUT", 600)))
        print(out)
        sys.exit(code or 0)
    elif cmd == "run":
        sbx, job, env = args[0], args[1], args[2:]
        kv = dict(e.split("=", 1) for e in env if "=" in e)
        name = kv.pop("NAME", None) or os.environ.get("NAME") or kv.get("JOB_ID") \
            or f"{job}-{time.strftime('%m%d-%H%M%S', time.gmtime())}"
        env = [f"{k}={v}" for k, v in kv.items()]
        sh(sbx, "mkdir -p /root/work/upload")
        put_file(sbx, f"/root/work/upload/{name}.tar.gz", code_tarball(DATA))
        env_s = " ".join(shlex.quote(e) for e in env)
        script = (f"set -e\nmkdir -p /root/runs/{name} /root/work /root/hf\n"
                  f"tar xzf /root/work/upload/{name}.tar.gz -C /root/runs/{name}\n"
                  f"cd /root/runs/{name}\n"
                  f"export WORK=/root/work OUT=/root/work/out/{name} HF_HOME=/root/hf "
                  f"NAME={name} {env_s}\nexec bash infra/jobs/{job}.sh\n")
        put_file(sbx, f"/root/work/upload/{name}.sh", script.encode())
        out, _ = sh(sbx, f"setsid nohup bash /root/work/upload/{name}.sh > /root/work/{name}.log "
                         f"2>&1 < /dev/null & sleep 3; echo started pid $!")
        print(out)
        print(f"job {name}: log with `sol_job.py log {sbx} {name}`")
        status(name, state="running", where=f"Solari sandbox {sbx[-8:]} (CPU)",
               what=" ".join([job, *env]), out=f"solari:/root/work/out/{name}", owner=OWNER)
    elif cmd == "log":
        sbx = args[0]
        pat = f"/root/work/{args[1]}.log" if len(args) > 1 else "$(ls -t /root/work/*.log | head -1)"
        out, _ = sh(sbx, f"tail -n {os.environ.get('LINES', 40)} {pat}; uptime")
        print(out)
        done = re.findall(r"done \(exit (\d+)\)", out)  # last line of infra/jobs/common.sh jobs
        if len(args) > 1 and done:
            status(args[1], state="done" if done[-1] == "0" else f"failed (exit {done[-1]})", owner=OWNER)
    elif cmd == "fetch":
        sbx, name, dest = args[0], args[1], args[2]
        out, code = sh(sbx, f"cd /root/work/out/{name} && tar czf /root/work/upload/fetch-{name}.tgz "
                            f"--exclude='*.gguf' --exclude='*.safetensors' . && echo ok")
        if code:
            sys.exit(out)
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(get_file(sbx, f"/root/work/upload/fetch-{name}.tgz"))) as t:
            t.extractall(dest)
        print(f"/root/work/out/{name} -> {dest}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
