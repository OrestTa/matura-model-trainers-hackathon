#!/usr/bin/env bash
# The exact on-stage harness: the pre-quantized base model plus its LoRA adapters in
# vLLM, and the router in front of it as an OpenAI-style endpoint on :8080.
#   bash scripts/serve_exam.sh bielik-11b
# Env: CHECKPOINT (default work/checkpoints/<model>), ADAPTERS (default
# work/adapters/<model>), ROUTER_PORT=8080, GPU=0. Everything runs offline.
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:?usage: serve_exam.sh <model key from configs/models.yaml>}"
CHECKPOINT="${CHECKPOINT:-work/checkpoints/$MODEL}"
ADAPTERS="${ADAPTERS:-work/adapters/$MODEL}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1  # no stats.vllm.ai call

# The checkpoint is bitsandbytes 4-bit, which vLLM 0.28+ can't load: same pin as infra/jobs/common.sh.
VLLM_PIN="${VLLM_PIN:-0.27.1}"
have=$(python -c "import vllm; print(vllm.__version__)" 2>/dev/null || echo none)
[ "$have" = "$VLLM_PIN" ] || { echo "vLLM $have found, need $VLLM_PIN: pip install vllm==$VLLM_PIN (before going offline)"; exit 1; }

# The shipped model (weights + adapters) must be at most finetuned_limit_gb (8.8 GB).
python scripts/quantize_checkpoint.py --check "$CHECKPOINT" --finetuned --adapters "$ADAPTERS"
KB=$(python -c "import yaml; print((yaml.safe_load(open('configs/routes.yaml')).get('rag') or {}).get('path', ''))")
[ -n "$KB" ] && [ -s "$KB" ] && echo "RAG: $KB" \
  || echo "WARNING: no RAG knowledge base at '$KB' (scripts/build_kb.py or the plwiki index; set rag.path)"

LORA=()
for d in "$ADAPTERS"/*/; do
  [ -f "$d/adapter_config.json" ] && LORA+=("$(basename "$d")=${d%/}")
done
[ ${#LORA[@]} -gt 0 ] && LORA=(--enable-lora --max-loras ${#LORA[@]} --max-lora-rank 64 --lora-modules "${LORA[@]}")
echo "adapters: ${LORA[*]:-none (base model only)}"

CUDA_VISIBLE_DEVICES="${GPU:-0}" vllm serve "$CHECKPOINT" --served-model-name base \
  --quantization bitsandbytes --port 8000 --max-model-len 8192 "${LORA[@]}" > work/exam-vllm.log 2>&1 &
VLLM=$!
trap 'kill $VLLM 2>/dev/null' EXIT
until curl -sf http://127.0.0.1:8000/v1/models >/dev/null; do
  kill -0 $VLLM 2>/dev/null || { echo "vLLM died, see work/exam-vllm.log"; exit 1; }
  sleep 5
done
python -m matura_router serve --port "${ROUTER_PORT:-8080}"
