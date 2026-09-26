#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-bielik-clean-v3-pair
OUT=/workspace/codex-small-track/bielik-clean-v3-pair
ADAPTERS=/workspace/codex-small-track-clean-v3/output/clean-v3-full-epoch
MODEL=/scratch/codex-bielik-cap-2135/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf
BINARY=/scratch/llama-build/bin/llama-server
mkdir -p "$OUT"
# Shared VM host RAM is independent of available GPU memory.
awk '/^MemAvailable:/ {print $2}' /proc/meminfo > "$OUT/host-memavailable-before-kib.txt"
HOST_AVAILABLE_KIB=$(cat "$OUT/host-memavailable-before-kib.txt")
test "$HOST_AVAILABLE_KIB" -ge 6291456
echo '90c3ff5f451864151793476df8ad8364b8b23e2e6cd20de7a007eeeba10a8a3e  '"$MODEL" | sha256sum -c -
echo 'efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf  '"$BINARY" | sha256sum -c -
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$OUT/free-vram-before.txt"
test "$(head -1 "$OUT/free-vram-before.txt")" -gt 10000
"$BINARY" --version > "$OUT/runtime.txt" 2>&1
LORAS="$ADAPTERS/closed_without_images/adapter-f16.gguf,$ADAPTERS/open_without_images/adapter-f16.gguf,$ADAPTERS/closed_with_images/adapter-f16.gguf,$ADAPTERS/open_with_images/adapter-f16.gguf,$ADAPTERS/essay/adapter-f16.gguf"
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" "$BINARY" -m "$MODEL" --lora "$LORAS" --lora-init-without-apply -ngl 99 -c 16384 -np 2 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18932 > "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 5
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader > "$OUT/gpu-processes.txt"
OUR_MIB=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | awk -F, -v own="$SERVER" '$1+0==own {gsub(/ /,"",$2); print $2}')
if test -n "$OUR_MIB"; then test "$OUR_MIB" -lt 8192; fi
timeout 900 python3 "$ROOT/infer.py" --root "$ROOT" --adapter-root "$ADAPTERS" --port 18932 --output "$OUT/evaluation" > "$OUT/inference.log" 2>&1
