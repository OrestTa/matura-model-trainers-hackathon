"""Gemma 4 12B (GGUF on llama.cpp) GPU jobs on Modal, one GPU per job, no vLLM.

    modal run --detach infra/modal/claude_gemma.py --job papers --env "PAPERS=probny-2026-01 MODE=raw"
    modal run --detach infra/modal/claude_gemma.py --job subtype --env "PAPERS=dev SHARD=0/4"
    modal run infra/modal/claude_gemma.py --job eval          # (re)build the eval set on the volume

Jobs: `papers` = infra/jobs/gemma_papers.sh (organisers' packages through run_exam.py),
`subtype` = infra/jobs/subtype_sweep.sh. Image: the llama.cpp CUDA server image plus Python
and Tesseract. The eval set (CKE papers with pictures, all 16) is built once into the
volume `claude-matura` at eval/ and reused. Outputs: claude-matura:out/<name>/

    modal volume get claude-matura out/<name> runs/modal/

App and volume carry the claude- prefix so they are told apart from other agents' Modal work.
"""
import os
import shlex
import subprocess
import time
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[2]
VOL = "/vol"
volume = modal.Volume.from_name("claude-matura", create_if_missing=True)

image = (
    modal.Image.from_registry("ghcr.io/ggml-org/llama.cpp:server-cuda", add_python="3.12")
    .entrypoint([])
    .apt_install("curl", "procps", "tesseract-ocr", "tesseract-ocr-pol")
    .pip_install("pyyaml", "huggingface_hub", "hf_transfer", "pymupdf", "requests")
    .add_local_dir(REPO, "/src", ignore=[".git", "work", "runs", "adapters", "models", "data",
                                          "**/__pycache__", "**/*.safetensors", "**/*.gguf"])
)
app = modal.App("claude-matura-gemma", image=image)


def _eval_set():
    """Copies the volume's eval set into /repo/data/eval (building it on first use)."""
    src = Path(VOL) / "eval"
    if not (src / "matura_all.jsonl").is_file():
        subprocess.run("cd /repo && python3 scripts/fetch_matura.py --papers all --images "
                       f"{src}/images -o {src}/matura_all.jsonl", shell=True, check=True)
        volume.commit()
    # image paths in the jsonl are absolute (/vol/eval/images/...), valid in every container
    subprocess.run(f"mkdir -p /repo/data/eval && cp {src}/matura_all.jsonl /repo/data/eval/", shell=True, check=True)


@app.function(gpu="L40S", volumes={VOL: volume}, timeout=4 * 3600)
def run_job(job: str, env: str, name: str) -> int:
    subprocess.run("rm -rf /repo && cp -r /src /repo", shell=True, check=True)
    _eval_set()
    if job == "eval":
        return 0
    out = f"{VOL}/out/{name}"
    job_env = dict(os.environ, OUT=out, WORK="/work", HF_HOME=f"{VOL}/hf", HF_HUB_ENABLE_HF_TRANSFER="1",
                   LLAMA_SERVER="/app/llama-server", EVAL="/repo/data/eval/matura_all.jsonl", NAME=name)
    job_env.update(dict(kv.split("=", 1) for kv in shlex.split(env)))
    script = {"papers": "gemma_papers.sh", "subtype": "subtype_sweep.sh"}[job]
    proc = subprocess.Popen(["bash", f"/repo/infra/jobs/{script}"], env=job_env, cwd="/repo")
    last = time.time()
    while proc.poll() is None:
        time.sleep(20)
        if time.time() - last > 180:  # partial results survive a crash or the hard stop
            volume.commit()
            last = time.time()
    volume.commit()
    return proc.returncode


@app.local_entrypoint()
def main(job: str = "papers", gpu: str = "L40S", env: str = "", name: str = ""):
    name = name or f"claude-{job}-{time.strftime('%m%d-%H%M%S', time.gmtime())}"
    print(f"{job} on {gpu} as {name}; outputs in volume claude-matura at out/{name}")
    code = run_job.with_options(gpu=gpu, env={"HF_TOKEN": os.environ["HF_TOKEN"]} if os.environ.get("HF_TOKEN") else {}
                                ).remote(job, env, name)
    print(f"{name} finished with exit {code}. Fetch: modal volume get claude-matura out/{name} runs/modal/")
