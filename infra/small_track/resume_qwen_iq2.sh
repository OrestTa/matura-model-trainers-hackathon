#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-qwen35-iq2
OUT=/workspace/codex-small-track/qwen35-iq2
BINARY=/scratch/llama-build/bin/llama-server
mkdir -p "$OUT"
exec 9> "$OUT/inference-resume.lock"
flock -n 9
echo '51149257226c09678f6dea61af8eaf04b00dbc16a7f4d5912e1495c51683980f  '"$OUT/evaluation/answers.jsonl" | sha256sum -c -
# Shared VM host RAM is independent of available GPU memory.
awk '/^MemAvailable:/ {print $2}' /proc/meminfo > "$OUT/host-memavailable-before-kib.txt"
HOST_AVAILABLE_KIB=$(cat "$OUT/host-memavailable-before-kib.txt")
test "$HOST_AVAILABLE_KIB" -ge 6291456
echo 'efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf  '"$BINARY" | sha256sum -c -
echo '4c1ba794e8d6098f4fb6482b4db6e880c80b5ee0b4c64d8668afaf9541163677  '"$ROOT/weights/Qwen3.5-4B-UD-IQ2_XXS.gguf" | sha256sum -c -
echo 'cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864  '"$ROOT/weights/mmproj-F16.gguf" | sha256sum -c -
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$OUT/free-vram-before.txt"
test "$(head -1 "$OUT/free-vram-before.txt")" -gt 10000
"$BINARY" --version > "$OUT/runtime-resume.txt" 2>&1
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" "$BINARY" -m "$ROOT/weights/Qwen3.5-4B-UD-IQ2_XXS.gguf" --mmproj "$ROOT/weights/mmproj-F16.gguf" -ngl 99 -c 8192 -np 1 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18933 >> "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 5
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader > "$OUT/gpu-processes.txt"
OUR_MIB=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | awk -F, -v own="$SERVER" '$1+0==own {gsub(/ /,"",$2); print $2}')
if test -n "$OUR_MIB"; then test "$OUR_MIB" -lt 8192; fi
timeout 900 python3 "$ROOT/infer-resume.py" --root "$ROOT" --output "$OUT/evaluation" --resume --concurrency 1 >> "$OUT/inference.log" 2>&1
