#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-bielik-cap-2135
OUT=/workspace/codex-small-track/bielik-cap-2135
mkdir -p "$ROOT" "$OUT"
MODEL="$ROOT/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf"
curl -fL --max-time 120 --retry 0 -o "$MODEL" 'https://huggingface.co/second-state/Bielik-1.5B-v3.0-Instruct-GGUF/resolve/6c316d2be07dee472901150c3f3e9d4f725a4706/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf'
echo '90c3ff5f451864151793476df8ad8364b8b23e2e6cd20de7a007eeeba10a8a3e  '"$MODEL" | sha256sum -c -
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$OUT/free-vram-before.txt"
test "$(head -1 "$OUT/free-vram-before.txt")" -gt 10000
/scratch/llama-build/bin/llama-server --version > "$OUT/runtime.txt" 2>&1
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" /scratch/llama-build/bin/llama-server -m "$MODEL" -ngl 99 -c 8192 -np 1 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18931 > "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 3
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader > "$OUT/gpu-processes.txt"
timeout 300 python3 "$ROOT/infer.py" --root "$ROOT" --candidate "$ROOT/candidate.jsonl" --base-only --port 18931 --concurrency 1 --server-seccomp --output "$OUT/evaluation" > "$OUT/inference.log" 2>&1
