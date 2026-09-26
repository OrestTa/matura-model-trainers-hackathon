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

# Inside the container this file is /root/modal_job.py, without the repo around it.
if modal.is_local():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))
    from status import update as status  # docs/STATUS.md, committed and pushed on each change
    REPO = Path(__file__).resolve().parents[2]
else:
    REPO = Path("/src")
VOL = "/vol"
volume = modal.Volume.from_name("matura-jobs", create_if_missing=True)

# llama.cpp's CUDA image: a prebuilt llama-server in /app for the GGUF models (Gemma 4), and
# the llama.cpp repo in /opt/llama.cpp for convert_lora_to_gguf.py (train.sh's GGUF LoRAs).
image = (
    modal.Image.from_registry("ghcr.io/ggml-org/llama.cpp:full-cuda", add_python="3.12")
    .entrypoint([])
    .apt_install("git", "curl", "procps")
    .run_commands("git clone -q --depth 1 https://github.com/ggml-org/llama.cpp /opt/llama.cpp")
    .pip_install("vllm==0.27.1", "bitsandbytes", "hf_transfer", "pyyaml", "matplotlib", "pymupdf",
                 "trl", "peft", "datasets", "accelerate", "requests")
    .add_local_dir(REPO, "/src", ignore=[".git", "work", "runs", "adapters", "models",
                                          "**/__pycache__", "**/*.safetensors", "**/*.gguf"])
)
# data/ is gitignored and may be missing from the checkout; ship what exists.
for rel in ("data/eval/matura.jsonl", "data/train/synthetic.jsonl", "data/train/past_papers.jsonl"):
    if modal.is_local() and (REPO / rel).is_file():
        image = image.add_local_file(REPO / rel, f"/src/{rel}")

app = modal.App("matura-jobs", image=image)


# HF token for Hub calls (unauthenticated ones got reset mid-run): Modal secret claude-hf.
@app.function(gpu="L40S:4", volumes={VOL: volume}, timeout=24 * 3600,
              secrets=[modal.Secret.from_name("claude-hf")])
def run_job(job: str, env: str, name: str) -> int:
    """Copies the repo to a writable dir and runs infra/jobs/<job>.sh with outputs on the volume."""
    subprocess.run("rm -rf /repo && cp -r /src /repo", shell=True, check=True)
    # WORK is per container (adapters of parallel jobs must not mix); llama.cpp comes from the image.
    subprocess.run("mkdir -p /work && ln -sfn /opt/llama.cpp /work/llama.cpp", shell=True, check=True)
    job_env = dict(os.environ, REPO="/repo", WORK="/work", OUT=f"{VOL}/out/{name}", HF_HOME="/work/hf",
                   NAME=name, LLAMA_SERVER="/app/llama-server",
                   LD_LIBRARY_PATH="/app:" + os.environ.get("LD_LIBRARY_PATH", ""))
    job_env.update(dict(kv.split("=", 1) for kv in shlex.split(env)))
    if job == "check":  # preflight: GPU, llama-server, the Python stack
        return subprocess.run("nvidia-smi -L && /app/llama-server --version && python3 -c 'import sys, vllm, trl, peft, "
                              "transformers; print(sys.version, vllm.__version__, transformers.__version__)' "
                              "&& ls /opt/llama.cpp/convert_lora_to_gguf.py", shell=True, env=job_env).returncode
    # Eval set with pictures (held-out papers) and the past-paper training items, when not shipped.
    prep = ("cd /repo && pip install -q -e . && python3 scripts/fetch_matura.py --images -o data/eval/matura.jsonl "
            "&& python3 scripts/fetch_matura.py --papers all -o data/eval/matura_all.jsonl")
    if job == "train" and job_env.get("PAST_PAPERS", "1") == "1":
        prep += " && python3 scripts/build_train_from_papers.py"
    if not Path("/repo/data/eval/matura.jsonl").is_file() or job == "train":
        subprocess.run(prep, shell=True, env=job_env, check=True)
    # Commit the volume every few minutes so partial results survive a crash or timeout.
    proc = subprocess.Popen(["bash", f"/repo/infra/jobs/{job}.sh"], env=job_env)
    while proc.poll() is None:
        time.sleep(60)
        if int(time.time()) % 300 < 60:
            volume.commit()
    volume.commit()
    return proc.returncode


@app.local_entrypoint()
def main(job: str = "baselines", gpu: str = "L40S:4", env: str = "", name: str = "", stop_utc: str = ""):
    """stop_utc="20:15": the container is killed at that UTC time today (hard stop)."""
    name = name or f"{job}-{time.strftime('%m%d-%H%M', time.gmtime())}"
    timeout = 24 * 3600
    if stop_utc:
        h, m = map(int, stop_utc.split(":"))
        now = time.gmtime()
        timeout = max(60, (h * 60 + m - now.tm_hour * 60 - now.tm_min) * 60)
    print(f"{job} on {gpu} as {name}; outputs in volume matura-jobs at out/{name}")
    env_extra = {"HF_TOKEN": os.environ["HF_TOKEN"]} if os.environ.get("HF_TOKEN") else {}
    if job == "check":
        print("check exit", run_job.with_options(gpu=gpu).remote(job, env, name))
        return
    status(name, state="running", where=f"Modal {gpu}", what=f"{job} {env}".strip(),
           out=f"modal volume matura-jobs:out/{name}", owner="Modal wrapper")
    try:
        code = run_job.with_options(gpu=gpu, env=env_extra, timeout=timeout).remote(job, env, name)
    except BaseException as e:
        status(name, state=f"failed ({type(e).__name__})")
        raise
    status(name, state="done" if code == 0 else f"failed (exit {code})")
    print(f"{name} finished with exit {code}. Fetch: modal volume get matura-jobs out/{name} runs/modal/")
