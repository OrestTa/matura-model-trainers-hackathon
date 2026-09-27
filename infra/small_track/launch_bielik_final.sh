#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-bielik-final-verification
OUT=/workspace/codex-small-track/bielik-final-verification
MODEL=/scratch/codex-bielik-cap-2135/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf
BINARY=/scratch/llama-build/bin/llama-server
mkdir -p "$OUT"
exec 9> "$OUT/run.lock"
flock -n 9
awk '/^MemAvailable:/ {print $2}' /proc/meminfo > "$OUT/host-memavailable-before-kib.txt"
test "$(cat "$OUT/host-memavailable-before-kib.txt")" -ge 6291456
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$OUT/free-vram-before.txt"
test "$(head -1 "$OUT/free-vram-before.txt")" -gt 10000
echo '90c3ff5f451864151793476df8ad8364b8b23e2e6cd20de7a007eeeba10a8a3e  '"$MODEL" | sha256sum -c -
echo 'efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf  '"$BINARY" | sha256sum -c -
"$BINARY" --version > "$OUT/runtime.txt" 2>&1
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" "$BINARY" -m "$MODEL" -ngl 99 -c 32768 -np 4 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18935 > "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 5
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader > "$OUT/gpu-processes.txt"
timeout 900 python3 "$ROOT/infer.py" --root "$ROOT" --output "$OUT/evaluation" > "$OUT/inference.log" 2>&1
