#!/usr/bin/env python3
"""Fail-fast checks for a GPU job, run by the job wrapper before it waits for GPU memory.

    python infra/jobs/preflight.py baselines      # uses MODELS, MODELS_CONFIG, EVAL from env
    python infra/jobs/preflight.py train          # uses TRAIN_MODELS
    python infra/jobs/preflight.py dapt           # uses DAPT_MODEL

Checks, per model: the stored size is within ship_limit_gb, the weights are in the HF cache
(downloads them now if not, so a gated or missing repo fails here, not an hour in), the
config parses and vLLM knows the architecture (vLLM models), and llama-server exists and
links CUDA (GGUF models). Also that the eval set exists and, for vision models, carries its
pictures. Prints one line per problem and exits 1 on any, so the job ends before it takes
the GPU. It does not load the model on the GPU; the job's first request does that.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("WORK", "/workspace/work"))
job = sys.argv[1] if len(sys.argv) > 1 else "baselines"
problems = []


def fail(msg):
    problems.append(msg)
    print(f"PREFLIGHT FAIL: {msg}", flush=True)


def models_for_job():
    cfg_path = REPO / os.environ.get("MODELS_CONFIG", "configs/models.yaml")
    cfg = yaml.safe_load(open(cfg_path))
    models, limit = cfg["models"], cfg.get("ship_limit_gb", 8.0)
    if job == "baselines":
        keys = os.environ.get("MODELS", "all")
        keys = [k for k in models if models[k].get("disk_gb", 0) <= limit] if keys == "all" \
            else keys.split(",")
    elif job == "train":
        keys = os.environ.get("TRAIN_MODELS", "bielik-11b").split(",")
    elif job == "dapt":
        keys = [os.environ.get("DAPT_MODEL", "bielik-11b")]
    else:
        keys = []
    return models, limit, keys


def check_weights(key, spec):
    from huggingface_hub import hf_hub_download, snapshot_download
    hf_id = spec.get("train_hf_id") if job in ("train", "dapt") and spec.get("train_hf_id") else spec["hf_id"]
    if hf_id.startswith("/"):
        # Made by an earlier job in the chain (e.g. a DAPT merge); it exists only later.
        if job == "baselines" and not Path(hf_id).exists():
            fail(f"{key}: local model {hf_id} does not exist")
        return None
    try:
        if spec.get("server") == "llamacpp":
            hf_hub_download(hf_id, spec["gguf_file"])
            if spec.get("vision") and spec.get("mmproj_file"):
                hf_hub_download(hf_id, spec["mmproj_file"])
            return None
        return snapshot_download(hf_id, allow_patterns=["*.json", "*.safetensors", "*.model",
                                                        "*.txt", "*.jinja", "*.py"])
    except Exception as e:  # noqa: BLE001
        fail(f"{key}: cannot get weights {hf_id}: {type(e).__name__}: {str(e)[:160]}")
        return None


def check_vllm(key, path):
    """Parses the config with vLLM's transformers and checks the architecture is supported."""
    py = WORK / "venv-py312/bin/python"
    if not py.exists():
        fail("vLLM venv missing at $WORK/venv-py312 (common.sh builds it)")
        return
    code = ("import json,sys; from transformers import AutoConfig; from vllm import ModelRegistry;"
            "p=sys.argv[1]; AutoConfig.from_pretrained(p);"
            "a=json.load(open(p+'/config.json')).get('architectures',[]);"
            "s=set(ModelRegistry.get_supported_archs());"
            "bad=[x for x in a if x not in s]; print('unsupported', bad) if bad else None;"
            "sys.exit(1 if bad else 0)")
    r = subprocess.run([str(py), "-c", code, path], capture_output=True, text=True, timeout=300)
    if r.returncode:
        err = (r.stdout + r.stderr).strip().splitlines()
        fail(f"{key}: vLLM can't load it: {err[-1][:200] if err else 'unknown error'}")


def check_llama_server():
    server = Path(os.environ.get("LLAMA_SERVER", WORK / "llama.cpp/build/bin/llama-server"))
    if not os.access(server, os.X_OK):
        fail(f"llama-server missing at {server} (build it first: infra/jobs/common.sh ensure_llama_server)")
        return
    libs = subprocess.run(["ldd", str(server)], capture_output=True, text=True).stdout
    if "cuda" not in libs.lower() and not list(server.parent.glob("libggml-cuda*")):
        fail(f"{server} is not a CUDA build")


def check_eval(needs_images):
    ev = Path(os.environ.get("EVAL", REPO / "data/eval/matura.jsonl"))
    if not ev.is_file() or ev.stat().st_size == 0:
        fail(f"eval set {ev} missing or empty")
        return
    if needs_images:
        rows = [json.loads(line) for line in open(ev)]
        with_img = [r for r in rows if r.get("images")]
        if not with_img:
            fail(f"vision model but {ev} has no 'images' (build it with fetch_matura.py --images)")
            return
        missing = [p for r in with_img for p in r["images"] if not (ev.parent / p).exists()
                   and not (REPO / p).exists() and not Path(p).exists()]
        if missing:
            fail(f"{len(missing)} image files named in {ev} are missing, e.g. {missing[0]}")


def main():
    models, limit, keys = models_for_job()
    vision = False
    for key in keys:
        spec = models.get(key)
        if spec is None:
            fail(f"{key}: not in the models config")
            continue
        if spec.get("disk_gb", 0) > limit:
            fail(f"{key}: {spec['disk_gb']} GB stored is over the {limit} GB base limit")
        vision |= bool(spec.get("vision"))
        path = check_weights(key, spec)
        if spec.get("server") == "llamacpp":
            check_llama_server()
        elif path and job == "baselines":
            check_vllm(key, path)
    if job == "baselines":
        check_eval(vision)
    if problems:
        print(f"PREFLIGHT: {len(problems)} problem(s); not starting {job}", flush=True)
        sys.exit(1)
    print(f"PREFLIGHT OK: {job} {','.join(keys)}", flush=True)


if __name__ == "__main__":
    main()
