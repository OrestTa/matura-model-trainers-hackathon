#!/bin/bash
set -euo pipefail
ROOT=/workspace/codex-small-track-all-papers-v2
BASE=/workspace/codex-small-track-clean-v3
PY="$BASE/venv/bin/python"
CONVERTER="$BASE/source/llama.cpp-694ec235484b3b0bf827ab7992a512d285f0e66b"
mkdir -p "$ROOT/output"
exec 9> "$ROOT/train.lock"
flock -n 9
awk '/^MemAvailable:/ {print $2}' /proc/meminfo > "$ROOT/host-memavailable-before-kib.txt"
test "$(cat "$ROOT/host-memavailable-before-kib.txt")" -ge 6291456
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits > "$ROOT/gpu-free-before-mib.txt"
test "$(head -1 "$ROOT/gpu-free-before-mib.txt")" -gt 12000
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$CONVERTER/gguf-py"
"$PY" "$ROOT/preflight.py" "$ROOT"
"$PY" -c 'import torch,transformers,peft; print("runtime",torch.__version__,transformers.__version__,peft.__version__,flush=True)'
timeout --signal=TERM --kill-after=15s 900s "$PY" "$ROOT/train.py" --model "$BASE/model" --data "$ROOT/data" --output-root "$ROOT/output" --converter "$CONVERTER/convert_lora_to_gguf.py" --run all-papers-full-epoch --steps 0 --routes closed_without_images,closed_with_images,open_without_images,open_with_images,essay --gpu-memory-fraction 0.20 --expected-data-manifest-sha256 ef4bd556304c7a856622ca06dfa5cc3a410c5ac859452ef93a0e405774136c07 --all-official-papers --resume-existing --checkpoint-every 10
