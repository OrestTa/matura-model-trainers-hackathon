"""Scores every candidate base model on the eval set, one model per GPU in parallel.

For each model in configs/models.yaml this starts a vLLM server on its own GPU,
runs the eval in each requested mode, and writes
    runs/baselines/<model>/<mode>/{answers.jsonl,summary.json}

Modes: raw    = one generic prompt, the untouched base model (the official baseline)
       routed = the router's per-type prompts and post-processing, still no adapters
       adapters = the full harness with LoRA adapters (needs --adapters-dir)

    python scripts/run_baselines.py --eval data/eval/matura.jsonl --gpus 0,1,2,3
    python scripts/run_baselines.py --models qwen3-8b --base-url http://localhost:8000/v1
    python scripts/run_baselines.py --gpus 0 --gpu-budget-gb 34   # many models on one GPU

With --gpu-budget-gb, models share the (first) GPU instead of taking one GPU each:
each vLLM server is capped at its model's memory estimate (models.yaml `gpu_gb`, else
disk_gb + 5 GB for the KV cache and activations), servers start one at a time, and a model starts as
soon as its estimate fits both in what's left of the budget and in the GPU's free memory
(other jobs share the card).

Then draw the charts with scripts/plot_baselines.py.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.backends.openai_compat import OpenAICompatBackend  # noqa: E402
from matura_router.evaluate import evaluate, load_rows  # noqa: E402
from matura_router.router import Router  # noqa: E402

print_lock = threading.Lock()


def log(msg: str):
    with print_lock:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def wait_ready(url: str, proc: subprocess.Popen | None, timeout: float = 1800) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"vLLM exited with code {proc.returncode}")
        try:
            urllib.request.urlopen(url + "/models", timeout=5)
            return
        except Exception:
            time.sleep(5)
    raise TimeoutError(f"{url} not ready after {timeout}s")


def served_weights(key: str, spec: dict) -> str:
    """The pre-quantized exam checkpoint when it exists (scripts/quantize_checkpoint.py),
    so baselines score exactly what we submit; else the HF weights."""
    ckpt = Path(spec.get("checkpoint") or ROOT / "work/checkpoints" / key)
    return str(ckpt) if (ckpt / "config.json").exists() else spec["hf_id"]


def start_vllm(key: str, spec: dict, vcfg: dict, gpu: str, port: int, log_path: Path,
               adapters_dir: Path | None, util: float | None = None) -> subprocess.Popen:
    cmd = ["vllm", "serve", served_weights(key, spec), "--served-model-name", "base",
           "--port", str(port), "--max-model-len", str(vcfg.get("max_model_len", 8192)),
           "--gpu-memory-utilization", f"{util or vcfg.get('gpu_memory_utilization', 0.9):.3f}"]
    if spec.get("quantization"):
        cmd += ["--quantization", spec["quantization"]]
    if adapters_dir:
        mods = [f"{d.name}={d}" for d in sorted((adapters_dir / key).glob("*"))
                if (d / "adapter_config.json").exists()]  # a crashed run leaves only checkpoints/
        if mods:
            cmd += ["--enable-lora", "--max-loras", str(len(mods)), "--max-lora-rank", "64",
                    "--lora-modules", *mods]
    cmd += list(vcfg.get("extra_args", [])) + list(spec.get("vllm_args", []))
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpu}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"[{key}] GPU {gpu}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)


def run_model(key: str, spec: dict, base_url: str, rows: list[dict], args) -> None:
    backend = OpenAICompatBackend(base_url=base_url, base_model="base",
                                  extra_body=spec.get("extra_body"))
    router = Router.from_config(args.routes, backend=backend)
    if "rag" in args.modes and router.retriever is None:
        sys.exit("mode rag needs the knowledge base in configs/routes.yaml (rag.path); "
                 "without it rag = routed and the comparison measures nothing")
    judge = None
    if args.judge_url:
        jb = OpenAICompatBackend(base_url=args.judge_url, base_model=args.judge_model,
                                 api_key=os.environ.get("JUDGE_API_KEY", "none"),
                                 extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        from matura_router.backends import GenerationParams
        judge = lambda p: jb.chat([{"role": "user", "content": p}], None,  # noqa: E731
                                  GenerationParams(max_tokens=8))

    for mode in args.modes:
        out_dir = Path(args.out) / key / mode
        out_dir.mkdir(parents=True, exist_ok=True)
        results, summary = evaluate(router, rows, mode=mode, concurrency=args.concurrency,
                                    judge=judge, use_gold_category=args.gold_category)
        summary.update(model=key, mode=mode, eval=str(args.eval), judge=args.judge_hf or args.judge_url,
                       served=served_weights(key, spec),
                       **{k: spec.get(k) for k in ("hf_id", "params_b", "disk_gb", "quantization")})
        ship = Path(summary["served"]) / "ship.json"
        if ship.exists():  # measured size of the checkpoint we actually ship
            summary["disk_gb"] = json.loads(ship.read_text())["size_gb"]
        with open(out_dir / "answers.jsonl", "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        log(f"[{key}] {mode}: {summary['pct']}% ({summary['scored']}/{summary['n']} scored, "
            f"{summary['errors']} errors, {summary['wall_s']}s)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"))
    p.add_argument("--models", default="all", help="comma list of keys from models.yaml")
    p.add_argument("--models-config", default=str(ROOT / "configs/models.yaml"))
    p.add_argument("--routes", default=str(ROOT / "configs/routes.yaml"))
    p.add_argument("--modes", default="raw,routed")
    p.add_argument("--gpus", default="0", help="one model per GPU at a time, e.g. 0,1,2,3")
    p.add_argument("--base-url", help="use an already running server (single model only)")
    p.add_argument("--adapters-dir", help="adapters/<model>/<category>/ for mode 'adapters'")
    p.add_argument("--out", default=str(ROOT / "runs/baselines"))
    p.add_argument("--concurrency", type=int, default=32)
    p.add_argument("--gpu-budget-gb", type=float, default=0,
                   help="share one GPU between models within this many GB (0 = one model per GPU)")
    p.add_argument("--gold-category", action="store_true",
                   help="route by the eval set's category instead of the classifier")
    p.add_argument("--judge-url", help="OpenAI-compatible endpoint that grades open answers")
    p.add_argument("--judge-model", default="judge")
    p.add_argument("--judge-hf", help="start this HF model with vLLM as the judge, e.g. Qwen/Qwen3-32B")
    p.add_argument("--judge-gpus", default="", help="GPUs reserved for the judge, e.g. 6,7")
    p.add_argument("--text-only", action="store_true", help="skip items that need an image")
    args = p.parse_args()
    args.modes = args.modes.split(",")

    cfg = yaml.safe_load(Path(args.models_config).read_text())
    models = cfg["models"]
    # "all" = every model we could ship; the -bf16 reference entries are over the size limit.
    # Local checkpoints (hf_id is a path, e.g. the DAPT-merged model) join "all" only once they exist.
    limit = float(cfg.get("ship_limit_gb", 8.0))
    keys = ([k for k in models if not k.endswith("-bf16") and float(models[k].get("disk_gb", 0)) <= limit
             and not (models[k]["hf_id"].startswith("/") and not Path(models[k]["hf_id"]).exists())]
            if args.models == "all" else args.models.split(","))
    unknown = [k for k in keys if k not in models]
    if unknown:
        p.error(f"unknown models: {unknown}")
    rows = load_rows(args.eval)
    if args.text_only:
        rows = [r for r in rows if not r.get("needs_image")]
    log(f"{len(rows)} eval rows from {args.eval}; models: {', '.join(keys)}")

    judge_proc = None
    if args.judge_hf:
        judge_proc = start_judge(args)
    try:
        run_all(p, args, cfg, models, keys, rows)
    finally:
        if judge_proc:
            stop(judge_proc)


def start_judge(args) -> subprocess.Popen:
    """Serves a larger open model that grades open answers against the CKE key."""
    gpus = args.judge_gpus or "0"
    port = 8099
    cmd = ["vllm", "serve", args.judge_hf, "--served-model-name", "judge", "--port", str(port),
           "--max-model-len", "8192", "--tensor-parallel-size", str(len(gpus.split(",")))]
    log_path = Path(args.out) / "judge_vllm.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"[judge] GPU {gpus}: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": gpus},
                            stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
    args.judge_url = f"http://127.0.0.1:{port}/v1"
    args.judge_model = "judge"
    wait_ready(args.judge_url, proc)
    log("[judge] ready")
    return proc


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(60)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_all(p, args, cfg, models, keys, rows):

    if args.base_url:
        if len(keys) != 1:
            p.error("--base-url needs exactly one --models entry")
        wait_ready(args.base_url, None, timeout=60)
        run_model(keys[0], models[keys[0]], args.base_url, rows, args)
        return

    if args.gpu_budget_gb:
        run_shared_gpu(args, cfg, models, keys, rows)
        return

    todo: queue.Queue = queue.Queue()
    for k in keys:
        todo.put(k)
    failures = []

    def worker(gpu: str):
        port = 8100 + int(gpu.split(",")[0])
        while True:
            try:
                key = todo.get_nowait()
            except queue.Empty:
                return
            proc = None
            try:
                proc = start_vllm(key, models[key], cfg.get("vllm", {}), gpu, port,
                                  Path(args.out) / key / "vllm.log",
                                  Path(args.adapters_dir) if args.adapters_dir else None)
                url = f"http://127.0.0.1:{port}/v1"
                wait_ready(url, proc)
                run_model(key, models[key], url, rows, args)
            except Exception as e:  # noqa: BLE001
                log(f"[{key}] FAILED: {e} (see {Path(args.out) / key / 'vllm.log'})")
                failures.append(key)
            finally:
                if proc:
                    stop(proc)

    threads = [threading.Thread(target=worker, args=(g,)) for g in args.gpus.split(",")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if failures:
        log(f"failed models: {failures}")
        sys.exit(1)


def gpu_total_gb(gpu: str) -> float:
    out = subprocess.run(["nvidia-smi", "-i", gpu, "--query-gpu=memory.total",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return float(out.stdout.split()[0]) / 1024


def gpu_free_gb(gpu: str) -> float:
    out = subprocess.run(["nvidia-smi", "-i", gpu, "--query-gpu=memory.free",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return float(out.stdout.split()[0]) / 1024


def model_gb(spec: dict) -> float:
    """GPU memory one vLLM server needs: weights as served plus KV cache and overhead."""
    return float(spec.get("gpu_gb") or max(8.0, float(spec.get("disk_gb", 8)) + 5))


def run_shared_gpu(args, cfg, models, keys, rows):
    """Runs every model at once on one GPU, as many as fit in --gpu-budget-gb."""
    gpu = args.gpus.split(",")[0]
    total = gpu_total_gb(gpu)
    budget = {"free": args.gpu_budget_gb}
    fits = threading.Condition()
    starting = threading.Lock()  # vLLM sizes its cache from free memory: start one at a time
    failures = []
    # Biggest first, so a large model isn't starved by a stream of small ones.
    order = sorted(keys, key=lambda k: -model_gb(models[k]))
    too_big = [k for k in order if model_gb(models[k]) > args.gpu_budget_gb]
    if too_big:
        log(f"over the {args.gpu_budget_gb} GB budget, skipped: {too_big}")
        failures += too_big
    log(f"sharing GPU {gpu} ({total:.0f} GB): " +
        ", ".join(f"{k}={model_gb(models[k]):.0f}GB" for k in order if k not in too_big))

    def worker(i: int, key: str):
        need = model_gb(models[key])
        proc = None
        port = 8100 + i
        admitted = False
        try:
            # One server starts at a time, and only once its memory is actually free on the
            # card (other jobs share it) and within the budget; free memory is read while no
            # other server is still loading.
            with starting:
                with fits:
                    while not (budget["free"] >= need and gpu_free_gb(gpu) >= need + 1):
                        fits.wait(30)
                    budget["free"] -= need
                    admitted = True
                proc = start_vllm(key, models[key], cfg.get("vllm", {}), gpu, port,
                                  Path(args.out) / key / "vllm.log",
                                  Path(args.adapters_dir) if args.adapters_dir else None,
                                  util=min(0.95, need / total))
                url = f"http://127.0.0.1:{port}/v1"
                wait_ready(url, proc)
            run_model(key, models[key], url, rows, args)
        except Exception as e:  # noqa: BLE001
            log(f"[{key}] FAILED: {e} (see {Path(args.out) / key / 'vllm.log'})")
            failures.append(key)
        finally:
            if proc:
                stop(proc)
            if admitted:
                with fits:
                    budget["free"] += need
                    fits.notify_all()

    threads = [threading.Thread(target=worker, args=(i, k))
               for i, k in enumerate(order) if k not in too_big]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if failures:
        log(f"failed models: {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
