#!/usr/bin/env bash
# The exact on-stage harness: the pre-quantized base model plus its LoRA adapters in
# vLLM, and the router in front of it as an OpenAI-style endpoint on :8080.
#   bash scripts/serve_exam.sh bielik-11b
# Env: CHECKPOINT (default work/checkpoints/<model>), ADAPTERS (default
# work/adapters/<model>), ROUTER_PORT=8080, GPU=0. Everything runs offline.
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:?usage: serve_exam.sh <model key from configs/models.yaml>}"
# A pre-quantized checkpoint: ours (scripts/quantize_checkpoint.py) if it exists, else the
# entry's own pre-quantized HF weights (e.g. bielik-11b-v3 = speakleash's AWQ), from the HF cache.
spec() { python -c "import yaml,sys; print(yaml.safe_load(open('configs/models.yaml'))['models']['$MODEL'].get('$1') or '')"; }
QUANT="$(spec quantization)"
SERVER="$(spec server)"
if [ -z "${CHECKPOINT:-}" ] && [ "$SERVER" = llamacpp ]; then
  # GGUF entries (gemma4-12b, qwen3.5-9b): the one .gguf file from the HF cache, on llama.cpp.
  CHECKPOINT="$(HF_HUB_OFFLINE=1 python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('$(spec hf_id)', '$(spec gguf_file)'))")"
fi
if [ -z "${CHECKPOINT:-}" ]; then
  CHECKPOINT="work/checkpoints/$MODEL"
  if [ ! -f "$CHECKPOINT/config.json" ] && [ -z "$QUANT" ]; then
    CHECKPOINT="$(HF_HUB_OFFLINE=1 python -c "from huggingface_hub import snapshot_download; print(snapshot_download('$(spec hf_id)'))")"
  fi
fi
ADAPTERS="${ADAPTERS:-work/adapters/$MODEL}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1  # no stats.vllm.ai call

# The checkpoint is bitsandbytes 4-bit, which vLLM 0.28+ can't load: same pin as infra/jobs/common.sh.
VLLM_PIN="${VLLM_PIN:-0.27.1}"
if [ "$SERVER" = llamacpp ]; then
  LLAMA_SERVER="${LLAMA_SERVER:-work/llama.cpp/build/bin/llama-server}"
  [ -x "$LLAMA_SERVER" ] || { echo "no llama-server at $LLAMA_SERVER: build it before going offline (infra/jobs/common.sh ensure_llama_server)"; exit 1; }
else
have=$(python -c "import vllm; print(vllm.__version__)" 2>/dev/null || echo none)
[ "$have" = "$VLLM_PIN" ] || { echo "vLLM $have found, need $VLLM_PIN: pip install vllm==$VLLM_PIN (before going offline)"; exit 1; }
fi

# Base weights at most ship_limit_gb (8.0 GB), base + adapters at most finetuned_limit_gb (8.8 GB).
python scripts/quantize_checkpoint.py --check "$CHECKPOINT" --adapters "$ADAPTERS"
# Text entries with `ocr: true` read the pictures' printed text with Tesseract (offline).
if [ "$(spec ocr)" = True ]; then
  command -v tesseract >/dev/null && tesseract --list-langs 2>/dev/null | grep -qx pol \
    || { echo "ocr: true needs tesseract with Polish: apt-get install -y tesseract-ocr tesseract-ocr-pol (before going offline)"; exit 1; }
  echo "OCR: tesseract pol (run_exam.py --model $MODEL turns it on)"
fi
KB=$(python -c "import yaml; print((yaml.safe_load(open('configs/routes.yaml')).get('rag') or {}).get('path', ''))")
[ -n "$KB" ] && [ -s "$KB" ] && echo "RAG: $KB" \
  || echo "WARNING: no RAG knowledge base at '$KB' (scripts/build_kb.py or the plwiki index; set rag.path)"

LORA=()
for d in "$ADAPTERS"/*/; do
  [ -f "$d/adapter_config.json" ] && LORA+=("$(basename "$d")=${d%/}")
done
[ ${#LORA[@]} -gt 0 ] && LORA=(--enable-lora --max-loras ${#LORA[@]} --max-lora-rank 64 --lora-modules "${LORA[@]}")
echo "adapters: ${LORA[*]:-none (base model only)}"

if [ "$SERVER" = llamacpp ]; then
  # Same flags as run_baselines.py start_llamacpp: 16 slots of 8192 tokens. Adapters would be
  # GGUF LoRAs (--lora); none are trained for the GGUF bases yet.
  # GGUF LoRAs from train.sh (adapters/<model>/<type>/adapter.gguf), applied to every request.
  # One adapter for all types (SINGLE_ADAPTER=1) is the supported case on llama.cpp.
  LORA=()
  for f in $(ls "$ADAPTERS"/*/adapter.gguf 2>/dev/null | xargs -r -n1 readlink -f | sort -u); do LORA+=(--lora "$f"); done
  [ ${#LORA[@]} -gt 2 ] && echo "WARNING: several GGUF LoRAs would all apply at once; train with SINGLE_ADAPTER=1"
  echo "llama.cpp LoRA: ${LORA[*]:-none}"
  SLOTS="$(spec parallel)"; SLOTS="${SLOTS:-16}"; CTX="$(spec ctx_per_slot)"; CTX="${CTX:-8192}"  # long thinking needs longer slots
  MMPROJ=()   # vision projector: run_exam.py --model $MODEL then sends the exam's PNGs
  [ "$(spec vision)" = True ] && [ -n "$(spec mmproj_file)" ] && MMPROJ=(--mmproj "$(HF_HUB_OFFLINE=1 python -c \
    "from huggingface_hub import hf_hub_download; print(hf_hub_download('$(spec hf_id)', '$(spec mmproj_file)'))")")
  CUDA_VISIBLE_DEVICES="${GPU:-0}" "$LLAMA_SERVER" -m "$CHECKPOINT" --alias base --host 127.0.0.1 \
    --port 8000 -ngl 999 --parallel "$SLOTS" -c "$((SLOTS * CTX))" --jinja -fa on --no-webui "${MMPROJ[@]}" "${LORA[@]}" > work/exam-vllm.log 2>&1 &
else
CUDA_VISIBLE_DEVICES="${GPU:-0}" vllm serve "$CHECKPOINT" --served-model-name base \
  ${QUANT:+--quantization "$QUANT"} --port 8000 --max-model-len 8192 "${LORA[@]}" > work/exam-vllm.log 2>&1 &
fi
VLLM=$!
trap 'kill $VLLM 2>/dev/null' EXIT
until curl -sf http://127.0.0.1:8000/v1/models >/dev/null; do
  kill -0 $VLLM 2>/dev/null || { echo "vLLM died, see work/exam-vllm.log"; exit 1; }
  sleep 5
done
echo "ready: python scripts/run_exam.py <package dir> --model $MODEL -o answers.json (in another shell)"
python -m matura_router serve --port "${ROUTER_PORT:-8080}"
