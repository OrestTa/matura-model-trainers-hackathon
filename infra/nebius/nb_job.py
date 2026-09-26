#!/usr/bin/env python3
"""Runs a GPU job from infra/jobs (baselines, train, dapt) as a Nebius Serverless AI Job.

    python infra/nebius/nb_job.py setup                        # once per session: CLI profile, bucket, S3 key
    python infra/nebius/nb_job.py launch --job baselines --env "MODELS=qwen3-8b MODES=raw"
    python infra/nebius/nb_job.py launch --job train --platform gpu-h100-sxm --preset 1gpu-16vcpu-200gb
    python infra/nebius/nb_job.py status [NAME]                # state + log tail; records the end in docs/STATUS.md
    python infra/nebius/nb_job.py fetch NAME                   # outputs -> runs/nebius/NAME/
    python infra/nebius/nb_job.py cancel NAME

Why Serverless AI Jobs and not a VM: outbound SSH is blocked from the cloud sessions,
and a job needs no SSH. The container is the pinned vllm/vllm-openai image; the job
script runs unchanged (see infra/jobs/common.sh). Like the Modal runner, the repo is
shipped from this checkout (commit not needed) together with the gitignored data files,
as a tarball in the bucket. OUT is synced to s3://$NEBIUS_BUCKET/out/<name>/ every few
minutes and at the end, so partial results survive a crash or timeout.

Credentials come only from the environment (Project settings), never from the repo:
    NEBIUS_SERVICE_ACCOUNT_ID, NEBIUS_PUBLIC_KEY_ID, NEBIUS_PRIVATE_KEY_B64 (base64 PEM),
    NEBIUS_PROJECT_ID; optional NEBIUS_BUCKET (default matura-jobs-<project suffix>),
    NEBIUS_REGION (default eu-north1), HF_TOKEN (forwarded to the job).
`setup` creates an S3 access key for the service account and keeps it in ~/.nebius/s3.env
(outside the repo), reusing it when present.
"""
import argparse
import base64
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from status import update as status  # docs/STATUS.md, committed and pushed on each change

REPO = Path(__file__).resolve().parents[2]
HOME = Path.home() / ".nebius"
NEBIUS = str(HOME / "bin" / "nebius")
S3_ENV = HOME / "s3.env"
REGION = os.environ.get("NEBIUS_REGION", "eu-north1")
S3_ENDPOINT = f"https://storage.{REGION}.nebius.cloud"
IMAGE = "vllm/vllm-openai:v0.27.1"  # vLLM stays on 0.27.1 (see common.sh)
DATA = ("data/eval/matura.jsonl", "data/eval/matura_all.jsonl",
        "data/train/synthetic.jsonl", "data/train/past_papers.jsonl", "data/eval/images", "data/kb")
SKIP = {".git", "work", "runs", "adapters", "models", "__pycache__", ".venv", ".run-venv", "secrets"}


def project():
    return os.environ["NEBIUS_PROJECT_ID"]


def bucket():
    return os.environ.get("NEBIUS_BUCKET") or f"matura-jobs-{project()[-8:]}"


def nb(*args, check=True, parse=True):
    """Runs the nebius CLI; returns parsed JSON output (or text with parse=False)."""
    cmd = [NEBIUS, *args] + (["--format", "json"] if parse else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"nebius {' '.join(args[:3])} failed:\n{r.stderr.strip()}")
    if not parse:
        return r.stdout
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def s3_env():
    env = dict(os.environ, AWS_ENDPOINT_URL=S3_ENDPOINT, AWS_DEFAULT_REGION=REGION)
    for line in S3_ENV.read_text().splitlines():
        k, _, v = line.partition("=")
        env[k] = v
    return env


def aws(*args):
    subprocess.run(["aws", "s3", *args, "--only-show-errors"], env=s3_env(), check=True)


def setup(_):
    if not Path(NEBIUS).exists():
        subprocess.run("curl -sSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash",
                       shell=True, check=True, stdin=subprocess.DEVNULL)
    subprocess.run("command -v aws >/dev/null || python3 -m pip install -q awscli", shell=True, check=True)
    key = HOME / "sa-key.pem"
    key.write_bytes(base64.b64decode(os.environ["NEBIUS_PRIVATE_KEY_B64"]))
    key.chmod(0o600)
    nb("profile", "create", "matura", "--endpoint", "api.nebius.cloud",
       "--service-account-id", os.environ["NEBIUS_SERVICE_ACCOUNT_ID"],
       "--public-key-id", os.environ["NEBIUS_PUBLIC_KEY_ID"],
       "--private-key-file-path", str(key), "--parent-id", project(), parse=False, check=False)
    nb("profile", "activate", "matura", parse=False, check=False)
    who = nb("iam", "whoami")
    print("authenticated as", (who or {}).get("service_account_profile", {}).get("info", {}).get("metadata", {}).get("name", "?"))
    if not S3_ENV.exists():
        k = nb("iam", "v2", "access-key", "create", "--parent-id", project(), "--name", f"matura-{int(time.time())}",
               "--account-service-account-id", os.environ["NEBIUS_SERVICE_ACCOUNT_ID"],
               "--secret-delivery-mode", "inline")
        status_ = k.get("status", k)
        S3_ENV.write_text(f"AWS_ACCESS_KEY_ID={status_['aws_access_key_id']}\n"
                          f"AWS_SECRET_ACCESS_KEY={status_['secret']}\n")
        S3_ENV.chmod(0o600)
    if nb("storage", "bucket", "get-by-name", "--parent-id", project(), "--name", bucket(), check=False) is None:
        nb("storage", "bucket", "create", "--parent-id", project(), "--name", bucket())
    print(f"ready: bucket {bucket()}, S3 key in {S3_ENV}")


ENTRY = r"""
set -uo pipefail
# Images without pip (e.g. ghcr.io/ggml-org/llama.cpp:full-cuda for subtype_sweep) get it from apt.
command -v pip >/dev/null || { apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y python3-pip >/dev/null 2>&1; }
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -q ${PIP_PKGS:-awscli trl peft datasets accelerate bitsandbytes hf_transfer pyyaml matplotlib pymupdf} >/tmp/pip.log 2>&1 \
  || { tail -20 /tmp/pip.log; exit 1; }
apt-get -qq update >/dev/null 2>&1 && apt-get -qq install -y git curl procps >/dev/null 2>&1
command -v python >/dev/null || ln -sf "$(command -v python3)" /usr/local/bin/python  # vllm image has only python3
mkdir -p /repo && aws s3 cp "s3://$NB_BUCKET/src/$NAME.tgz" - --only-show-errors | tar xz -C /repo || exit 1
export REPO=/repo WORK=/work OUT=/work/out/$NAME HF_HOME=/work/hf STOP_WHEN_DONE=0 VENV=/nonexistent
mkdir -p "$OUT"
sync() { aws s3 sync "$OUT" "s3://$NB_BUCKET/out/$NAME/" --only-show-errors; }
( while sleep 300; do sync; done ) & SYNCER=$!
bash /repo/infra/jobs/$JOB.sh; code=$?
kill $SYNCER; echo "$code" > "$OUT/EXIT_CODE"; sync
exit $code
"""


def launch(a):
    name = a.name or f"nb-{a.job}-{time.strftime('%m%d-%H%M', time.gmtime())}"
    tgz = HOME / f"{name}.tgz"
    with tarfile.open(tgz, "w:gz") as t:
        t.add(REPO, arcname=".", filter=lambda ti: None if SKIP & set(Path(ti.name).parts)
              or ti.name.endswith((".safetensors", ".gguf")) or (ti.name.startswith("./data/")
              and ti.isfile() and not any(ti.name[2:] == d or ti.name[2:].startswith(d + "/") for d in DATA)) else ti)
        for rel in DATA:  # data/ is gitignored; cloud sessions keep it in the project's shared folder
            shared = Path("/mnt/project-files") / rel
            if not (REPO / rel).exists() and shared.exists():
                t.add(shared, arcname=f"./{rel}")
    aws("cp", str(tgz), f"s3://{bucket()}/src/{name}.tgz")
    tgz.unlink()
    creds = s3_env()
    env = {"NAME": name, "JOB": a.job, "NB_BUCKET": bucket(), "AWS_ENDPOINT_URL": S3_ENDPOINT,
           "AWS_DEFAULT_REGION": REGION, "AWS_ACCESS_KEY_ID": creds["AWS_ACCESS_KEY_ID"],
           "AWS_SECRET_ACCESS_KEY": creds["AWS_SECRET_ACCESS_KEY"]}
    if os.environ.get("HF_TOKEN"):
        env["HF_TOKEN"] = os.environ["HF_TOKEN"]
    env.update(dict(kv.split("=", 1) for kv in shlex.split(a.env)))
    args = ["ai", "job", "create", "--name", name, "--image", a.image, "--platform", a.platform,
            "--preset", a.preset, "--disk-size", a.disk, "--timeout", a.timeout, "--async",
            "--container-command", "bash", "--args", f"-c {shlex.quote(ENTRY)}"]
    args += ["--preemptible", "--follows-spot-price"] if a.preemptible else ["--on-demand"]
    for k, v in env.items():
        args += ["--env", f"{k}={v}"]
    nb(*args, parse=False)
    where = f"Nebius {a.platform} {a.preset}"
    status(name, state="running", where=where, what=f"{a.job} {a.env}".strip(),
           out=f"s3://{bucket()}/out/{name}", owner=a.owner)
    print(f"launched {name} on {where}; `python {sys.argv[0]} status {name}`")


def job_state(name):
    j = nb("ai", "job", "get-by-name", "--parent-id", project(), "--name", name, check=False)
    return (j or {}).get("status", {}).get("state", "UNKNOWN"), j


def show(a):
    if not a.name:
        print(nb("ai", "job", "list", "--parent-id", project(), parse=False, check=False))
        return
    state, _ = job_state(a.name)
    print("state:", state)
    print(nb("ai", "job", "logs", a.name, parse=False, check=False)[-4000:])
    if state in ("COMPLETED", "SUCCEEDED", "FAILED", "CANCELLED", "ERROR"):
        status(a.name, state="done" if state in ("COMPLETED", "SUCCEEDED") else f"failed ({state})")


def fetch(a):
    dest = REPO / "runs" / "nebius" / a.name
    aws("sync", f"s3://{bucket()}/out/{a.name}/", str(dest))
    print("fetched to", dest)


def cancel(a):
    _, j = job_state(a.name)
    nb("ai", "job", "cancel", "--id", j["metadata"]["id"], parse=False)
    status(a.name, state="cancelled")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=setup)
    l = sub.add_parser("launch")
    l.add_argument("--job", default="baselines", help="infra/jobs/<job>.sh")
    l.add_argument("--env", default="", help='job settings, e.g. "MODELS=qwen3-8b MODES=raw"')
    l.add_argument("--platform", default="gpu-h100-sxm", help="gpu-h100-sxm, gpu-h200-sxm, gpu-l40s-d, ...")
    l.add_argument("--preset", default="1gpu-16vcpu-200gb")
    l.add_argument("--disk", default="250Gi")
    l.add_argument("--timeout", default="12h")
    l.add_argument("--preemptible", action="store_true", help="spot VM: cheaper, can be stopped")
    l.add_argument("--name")
    l.add_argument("--image", default=IMAGE, help="container image (default the pinned vLLM one)")
    l.add_argument("--owner", default="Nebius runner")
    l.set_defaults(fn=launch)
    for cmd, fn in (("status", show), ("fetch", fetch), ("cancel", cancel)):
        s = sub.add_parser(cmd)
        s.add_argument("name", nargs="?" if cmd == "status" else None)
        s.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
