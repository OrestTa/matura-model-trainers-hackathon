#!/usr/bin/env bash
# One GPU: serves Gemma 4 12B QAT + mmproj on llama-server and runs scripts/subtype_sweep.py
# (every candidate of configs/subtype_grid.yaml on its subtype's items, plus the raw baseline).
# Light on purpose: no vLLM venv. Runs in the llama.cpp CUDA server image
# (ghcr.io/ggml-org/llama.cpp:server-cuda, llama-server at /app/llama-server) or on any box
# with LLAMA_SERVER set / buildable (infra/jobs/common.sh ensure_llama_server). Env:
#   PAPERS=dev|heldout|all   SHARD=i/n   SLOTS=24   OUT=work/out/subtype-sweep
#   SWEEP_ARGS="--subtypes open_image --candidates base,think"   (passed through)
set -uo pipefail
cd "$(dirname "$0")/../.."
MODEL="${MODEL:-gemma4-12b}"; PAPERS="${PAPERS:-dev}"; SHARD="${SHARD:-0/1}"; SLOTS="${SLOTS:-24}"
OUT="${OUT:-work/out/subtype-sweep}"; mkdir -p "$OUT"
exec > >(tee -a "$OUT/job.log") 2>&1
step() { echo "== $(date -u +%H:%M:%S) $*"; }

step "deps"
if ! command -v python3 >/dev/null || ! command -v tesseract >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y -qq python3 python3-pip tesseract-ocr tesseract-ocr-pol curl >/dev/null
fi
python3 -m pip install -q --break-system-packages pyyaml huggingface_hub hf_transfer 2>/dev/null \
  || python3 -m pip install -q pyyaml huggingface_hub hf_transfer
tesseract --list-langs 2>/dev/null | grep -qx pol || step "WARNING: no tesseract pol, ocr candidates = base"
[ -s data/eval/matura_all.jsonl ] || { step "no data/eval/matura_all.jsonl (ship it with the job)"; exit 1; }

LLAMA_SERVER="${LLAMA_SERVER:-$(command -v llama-server || echo /app/llama-server)}"
if [ ! -x "$LLAMA_SERVER" ]; then
  unset LLAMA_SERVER; source infra/jobs/common.sh && ensure_llama_server || { step "no llama-server"; exit 1; }
fi

step "downloading $MODEL"
export HF_HUB_ENABLE_HF_TRANSFER=1
read -r GGUF MMPROJ < <(python3 - "$MODEL" <<'PY'
import sys, yaml
from huggingface_hub import hf_hub_download as d
s = yaml.safe_load(open("configs/models.yaml"))["models"][sys.argv[1]]
print(d(s["hf_id"], s["gguf_file"]), d(s["hf_id"], s["mmproj_file"]))
PY
)
[ -s "$GGUF" ] || { step "download failed"; exit 1; }

step "llama-server, $SLOTS slots"
"$LLAMA_SERVER" -m "$GGUF" --mmproj "$MMPROJ" --alias base --host 127.0.0.1 --port 8000 -ngl 999 \
  --parallel "$SLOTS" -c $((SLOTS * 12288)) --jinja -fa on -ctk q8_0 -ctv q8_0 --no-webui \
  > "$OUT/llama-server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 180); do
  curl -sf http://127.0.0.1:8000/v1/models >/dev/null && break
  kill -0 $SRV 2>/dev/null || { tail -30 "$OUT/llama-server.log"; exit 1; }
  sleep 5
done
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv

step "sweep papers=$PAPERS shard=$SHARD"
python3 scripts/subtype_sweep.py --base-url http://127.0.0.1:8000/v1 --papers "$PAPERS" --shard "$SHARD" \
  --concurrency "$SLOTS" --raw --out "$OUT" ${SWEEP_ARGS:-}
rc=$?
step "done (exit $rc): $OUT"
exit $rc
