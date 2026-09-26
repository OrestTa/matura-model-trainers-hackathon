#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-qwen35-iq2
OUT=/workspace/codex-small-track/qwen35-iq2
BINARY=/scratch/llama-build/bin/llama-server
mkdir -p "$OUT"
# Shared VM host RAM is independent of available GPU memory.
awk '/^MemAvailable:/ {print $2}' /proc/meminfo > "$OUT/host-memavailable-before-kib.txt"
HOST_AVAILABLE_KIB=$(cat "$OUT/host-memavailable-before-kib.txt")
test "$HOST_AVAILABLE_KIB" -ge 6291456
echo 'efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf  '"$BINARY" | sha256sum -c -
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$OUT/free-vram-before.txt"
test "$(head -1 "$OUT/free-vram-before.txt")" -gt 10000
"$BINARY" --version > "$OUT/runtime.txt" 2>&1
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" "$BINARY" -m "$ROOT/weights/Qwen3.5-4B-UD-IQ2_XXS.gguf" --mmproj "$ROOT/weights/mmproj-F16.gguf" -ngl 99 -c 16384 -np 2 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18933 > "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 5
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader > "$OUT/gpu-processes.txt"
OUR_MIB=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | awk -F, -v own="$SERVER" '$1+0==own {gsub(/ /,"",$2); print $2}')
if test -n "$OUR_MIB"; then test "$OUR_MIB" -lt 8192; fi
timeout 900 python3 "$ROOT/infer.py" --root "$ROOT" --output "$OUT/evaluation" > "$OUT/inference.log" 2>&1
