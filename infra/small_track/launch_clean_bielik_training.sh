#!/usr/bin/env bash
# Parent-approved launch only. Stage script must have completed first.
set -euo pipefail
umask 077
ROOT_DIR=${1:?own scratch root required}
case "$ROOT_DIR" in /workspace/codex-small-track-clean-v3*) ;; *) exit 2;; esac
PY="$ROOT_DIR/venv/bin/python"
CONVERTER_ROOT="$ROOT_DIR/source/llama.cpp-694ec235484b3b0bf827ab7992a512d285f0e66b"
export PYTHONPATH="$CONVERTER_ROOT/gguf-py"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 CUDA_VISIBLE_DEVICES=0
RUN=clean-v3-full-epoch
mkdir -p "$ROOT_DIR/output"
[ ! -e "$ROOT_DIR/output/$RUN" ] || { echo 'Refusing to replace prior output' >&2; exit 2; }
# GNU timeout owns this process tree only; it never targets another agent's process.
timeout --signal=TERM --kill-after=15s 900s "$PY" "$ROOT_DIR/train_bielik_real_native.py" \
 --model "$ROOT_DIR/model" --data "$ROOT_DIR/data" --output-root "$ROOT_DIR/output" \
 --converter "$CONVERTER_ROOT/convert_lora_to_gguf.py" --run "$RUN" --steps 0 \
 --routes closed_without_images,closed_with_images,open_without_images,open_with_images,essay \
 --gpu-memory-fraction 0.20 \
 --expected-data-manifest-sha256 da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab \
 > "$ROOT_DIR/training.log" 2>&1
