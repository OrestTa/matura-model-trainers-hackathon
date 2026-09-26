#!/usr/bin/env python3
"""Waits until the GPU has room for a job, so several jobs can share one card.

    python3 infra/jobs/gpu_admit.py <job-name> <need-gb> [gpu-index]

Admits the job once the GPU's free memory, minus what recently admitted jobs have
reserved but not yet allocated, is at least <need-gb>. A reservation is a file in
$GPU_RESERVATIONS (default /workspace/work/gpu_reservations) and counts for
RESERVE_S seconds (default 600, long enough for a vLLM server or trainer to load),
or until the job's log ($WORK/<job>.log) says it finished, whichever comes first.
A lock file makes admission one job at a time. Stdlib only.
"""
import fcntl
import os
import subprocess
import sys
import time

name, need = sys.argv[1], float(sys.argv[2])
gpu = sys.argv[3] if len(sys.argv) > 3 else "0"
root = os.environ.get("GPU_RESERVATIONS", "/workspace/work/gpu_reservations")
hold = float(os.environ.get("RESERVE_S", 600))
logs = os.environ.get("WORK", "/workspace/work")
os.makedirs(root, exist_ok=True)


def free_gb() -> float:
    out = subprocess.run(["nvidia-smi", "-i", gpu, "--query-gpu=memory.free",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return float(out.stdout.split()[0]) / 1024


def finished(job: str) -> bool:
    """A job that died early must not keep its reservation for the full RESERVE_S."""
    try:
        with open(os.path.join(logs, f"{job}.log"), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            return b"done (exit" in f.read()
    except OSError:
        return False


def reserved_gb() -> float:
    total, now = 0.0, time.time()
    for f in os.listdir(root):
        path = os.path.join(root, f)
        if f.endswith(".gb") and now - os.path.getmtime(path) < hold and not finished(f[:-3]):
            total += float(open(path).read() or 0)
    return total


last = 0.0
while True:
    with open(os.path.join(root, ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        avail = free_gb() - reserved_gb()
        if avail >= need:
            with open(os.path.join(root, f"{name}.gb"), "w") as f:
                f.write(str(need))
            print(f"{time.strftime('%H:%M:%S')} GPU admitted {name}: needs {need:.0f} GB, "
                  f"{avail:.0f} GB available", flush=True)
            sys.exit(0)
    if time.time() - last > 600:
        print(f"{time.strftime('%H:%M:%S')} {name} waiting for {need:.0f} GB of GPU memory "
              f"({avail:.0f} GB available)", flush=True)
        last = time.time()
    time.sleep(30)
