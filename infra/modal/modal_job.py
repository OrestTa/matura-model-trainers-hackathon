"""Runs a GPU job from infra/jobs (baselines or train) on Modal.

    modal run infra/modal/modal_job.py --job baselines
    modal run --detach infra/modal/modal_job.py --job baselines --gpu L40S:2 --env "MODELS=qwen3-8b JUDGE_HF="
    modal run --detach infra/modal/modal_job.py --job train --gpu H100:8 --env "TRAIN_MODELS=bielik-11b"

The job script runs unchanged (see infra/jobs/common.sh): the image already has vLLM
and the training stack, the repo is copied in from this checkout (commit not needed),
and data/eval/matura.jsonl and data/train/synthetic.jsonl go along when present
locally. Outputs, adapters and the Hugging Face cache live on the Modal volume
`matura-jobs`:

    modal volume ls matura-jobs out/
    modal volume get matura-jobs out/<name> runs/modal/      # report/index.html inside
    modal volume get matura-jobs work/adapters runs/modal/adapters

`--env` passes job settings (MODELS, MODES, JUDGE_HF, TRAIN_MODELS, EPOCHS, ...).
Start and finish are recorded in docs/STATUS.md (without --detach, so the wrapper sees
the end). HF_TOKEN is forwarded from your shell when set (needed for Gemma only).
Default GPU is 4x L40S: two score models, two serve the Qwen3-32B judge.
"""
import os
import sys
import shlex
import subprocess
import time
from pathlib import Path

import modal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
from status import update as status  # docs/STATUS.md, committed and pushed on each change

REPO = Path(__file__).resolve().parents[2]
VOL = "/vol"
volume = modal.Volume.from_name("matura-jobs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl", "procps")
    .pip_install("vllm", "bitsandbytes", "hf_transfer", "pyyaml", "matplotlib", "pymupdf",
                 "trl", "peft", "datasets", "accelerate", "requests")
    .add_local_dir(REPO, "/src", ignore=[".git", "work", "runs", "adapters", "models",
                                          "**/__pycache__", "**/*.safetensors", "**/*.gguf"])
)
# data/ is gitignored and may be missing from the checkout; ship what exists.
for rel in ("data/eval/matura.jsonl", "data/train/synthetic.jsonl"):
    if (REPO / rel).is_file():
        image = image.add_local_file(REPO / rel, f"/src/{rel}")

app = modal.App("matura-jobs", image=image)


@app.function(gpu="L40S:4", volumes={VOL: volume}, timeout=24 * 3600)
def run_job(job: str, env: str, name: str) -> int:
    """Copies the repo to a writable dir and runs infra/jobs/<job>.sh with outputs on the volume."""
    subprocess.run("rm -rf /repo && cp -r /src /repo", shell=True, check=True)
    job_env = dict(os.environ, REPO="/repo", WORK=f"{VOL}/work", OUT=f"{VOL}/out/{name}",
                   HF_HOME=f"{VOL}/hf", NAME=name)
    job_env.update(dict(kv.split("=", 1) for kv in shlex.split(env)))
    # Commit the volume every few minutes so partial results survive a crash or timeout.
    proc = subprocess.Popen(["bash", f"/repo/infra/jobs/{job}.sh"], env=job_env)
    while proc.poll() is None:
        time.sleep(60)
        if int(time.time()) % 300 < 60:
            volume.commit()
    volume.commit()
    return proc.returncode


@app.local_entrypoint()
def main(job: str = "baselines", gpu: str = "L40S:4", env: str = ""):
    name = f"{job}-{time.strftime('%m%d-%H%M', time.gmtime())}"
    print(f"{job} on {gpu} as {name}; outputs in volume matura-jobs at out/{name}")
    env_extra = {"HF_TOKEN": os.environ["HF_TOKEN"]} if os.environ.get("HF_TOKEN") else {}
    status(name, state="running", where=f"Modal {gpu}", what=f"{job} {env}".strip(),
           out=f"modal volume matura-jobs:out/{name}", owner="Modal wrapper")
    try:
        code = run_job.with_options(gpu=gpu, env=env_extra).remote(job, env, name)
    except BaseException as e:
        status(name, state=f"failed ({type(e).__name__})")
        raise
    status(name, state="done" if code == 0 else f"failed (exit {code})")
    print(f"{name} finished with exit {code}. Fetch: modal volume get matura-jobs out/{name} runs/modal/")
