"""The per-subtype sweep (infra/jobs/subtype_sweep.sh) on Modal H100s, N shards in parallel.

    modal run infra/modal/subtype_modal.py --shards 8 --papers dev --name subtype-m1
    modal run infra/modal/subtype_modal.py --shards 4 --papers heldout --name subtype-ho \\
        --sweep-args "--selected --candidates base"
    modal volume get claude-matura-subtype out/subtype-m1 results/subtype/     # then commit results/subtype/subtype-m1

Image: llama.cpp's CUDA server image (llama-server prebuilt in /app, no build), plus Python.
The repo (with data/eval incl. images/ and data/kb/passages.jsonl) is copied from this checkout,
so copy /mnt/project-files/data into data/ first if it's missing. HF_TOKEN is forwarded if set.
Each shard writes out/<name>/shard-<i>/<group>/<candidate>/answers.jsonl on the volume.
"""
import os
import subprocess
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[2]
VOL = "/vol"
volume = modal.Volume.from_name("claude-matura-subtype", create_if_missing=True)
image = (
    modal.Image.from_registry("ghcr.io/ggml-org/llama.cpp:full-cuda", add_python="3.12")
    .apt_install("tesseract-ocr", "tesseract-ocr-pol", "curl")
    .pip_install("pyyaml", "huggingface_hub", "hf_transfer")
    .add_local_dir(REPO, "/src", ignore=[".git", "work", "runs", "adapters", "models", "**/__pycache__",
                                          "**/*.safetensors", "**/*.gguf"])
)
app = modal.App("claude-matura-subtype", image=image)


# Not H100: the prebuilt llama.cpp image's CUDA kernels abort on sm90 ("illegal instruction", 26 Sep).
GPU = os.environ.get("SUBTYPE_GPU", "L40S")


@app.function(gpu=GPU, volumes={VOL: volume}, timeout=3 * 3600,
              secrets=[modal.Secret.from_dict({"HF_TOKEN": os.environ.get("HF_TOKEN", "")})])
def shard(i: int, n: int, papers: str, name: str, sweep_args: str, extra_env: str = "") -> int:
    subprocess.run("rm -rf /repo && cp -r /src /repo", shell=True, check=True)
    assert Path("/repo/data/eval/matura_all.jsonl").exists(), "ship data/eval (copy from /mnt/project-files/data)"
    env = dict(os.environ, LLAMA_SERVER="/app/llama-server", HF_HOME=f"{VOL}/hf", PAPERS=papers,
               SHARD=f"{i}/{n}", OUT=f"{VOL}/out/{name}/shard-{i}", SWEEP_ARGS=sweep_args,
               **dict(kv.split("=", 1) for kv in extra_env.split() if "=" in kv))
    code = subprocess.run(["bash", "/repo/infra/jobs/subtype_sweep.sh"], env=env).returncode
    volume.commit()
    return code


@app.local_entrypoint()
def main(shards: int = 8, papers: str = "dev", name: str = "subtype-modal", sweep_args: str = "", env: str = ""):
    """env: space-separated KEY=VALUE for the job (MODEL=gemma4-12b-think8k SMOKE=1 SLOTS=8 RAW=' ')."""
    codes = list(shard.starmap([(i, shards, papers, name, sweep_args, env) for i in range(shards)]))
    print("exit codes:", codes, f"-> modal volume get claude-matura-subtype out/{name} results/subtype/")
