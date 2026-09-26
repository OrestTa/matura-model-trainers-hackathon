#!/usr/bin/env bash
# One GPU: serves Gemma 4 12B QAT + mmproj on llama-server and runs scripts/subtype_sweep.py
# (every candidate of configs/subtype_grid.yaml on its subtype's items, plus the raw baseline).
# Light on purpose: no vLLM venv. Runs in the llama.cpp CUDA server image
# (ghcr.io/ggml-org/llama.cpp:server-cuda, llama-server at /app/llama-server) or on any box
# with LLAMA_SERVER set / buildable (infra/jobs/common.sh ensure_llama_server). Env:
#   PAPERS=dev|heldout|all   SHARD=i/n   SLOTS=16   OUT=work/out/subtype-sweep
#   RAW=" " or RAW=none (skip the raw baseline in this shard)
#   SWEEP_ARGS="--subtypes open_image --candidates base,think"   (passed through)
#   SMOKE=2   end-to-end smoke first: 2 items per subtype, every candidate; fails (exit 3) on any blank
#             answer or llama-server restart, so a broken setup costs minutes, not a shard of H100 time.
set -uo pipefail
cd "$(dirname "$0")/../.."
MODEL="${MODEL:-gemma4-12b-think8k}"; PAPERS="${PAPERS:-dev}"; SHARD="${SHARD:-0/1}"; SLOTS="${SLOTS:-16}"
OUT="${OUT:-work/out/subtype-sweep}"; mkdir -p "$OUT"
exec > >(tee -a "$OUT/job.log") 2>&1
step() { echo "== $(date -u +%H:%M:%S) $*"; }

RAWFLAG="$RAWFLAG"; [ "$RAWFLAG" = none ] && RAWFLAG=" "
step "deps"
if ! command -v python3 >/dev/null || ! command -v tesseract >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y -qq python3 python3-pip tesseract-ocr tesseract-ocr-pol curl >/dev/null
fi
python3 -m pip install -q --break-system-packages pyyaml huggingface_hub hf_transfer 2>/dev/null \
  || python3 -m pip install -q pyyaml huggingface_hub hf_transfer
tesseract --list-langs 2>/dev/null | grep -qx pol || step "WARNING: no tesseract pol, ocr candidates = base"
[ -s data/eval/matura_all.jsonl ] || { step "no data/eval/matura_all.jsonl (ship it with the job)"; exit 1; }

LLAMA_SERVER="${LLAMA_SERVER:-$(command -v llama-server || ls /app/llama-server 2>/dev/null || find / -xdev -name llama-server -type f 2>/dev/null | head -1)}"
if [ ! -x "${LLAMA_SERVER:-}" ]; then
  unset LLAMA_SERVER; source infra/jobs/common.sh && ensure_llama_server || { step "no llama-server"; exit 1; }
fi

# The llama.cpp images keep libllama*.so next to the binary (/app), outside the loader path.
export LD_LIBRARY_PATH="$(dirname "$LLAMA_SERVER"):${LD_LIBRARY_PATH:-}"
"$LLAMA_SERVER" --version >/dev/null 2>&1 || { "$LLAMA_SERVER" --version; step "llama-server doesn't start"; exit 1; }

step "downloading $MODEL"
export HF_HUB_ENABLE_HF_TRANSFER=1
# As on stage: an answer lost to runaway thinking is asked again with thinking off (openai_compat).
export THINK_FALLBACK="${THINK_FALLBACK:-1}"
read -r GGUF MMPROJ < <(python3 - "$MODEL" <<'PY'
import sys, yaml
from huggingface_hub import hf_hub_download as d
s = yaml.safe_load(open("configs/models.yaml"))["models"][sys.argv[1]]
print(d(s["hf_id"], s["gguf_file"]), d(s["hf_id"], s["mmproj_file"]))
PY
)
[ -s "$GGUF" ] || { step "download failed"; exit 1; }

step "llama-server, $SLOTS slots"
# CUDA graphs off and f16 KV: with graphs and q8_0 KV the prebuilt image aborted in
# ggml_backend_cuda_synchronize on H100 every few minutes (subtype-z-*, 26 Sep).
export GGML_CUDA_DISABLE_GRAPHS=1
# Supervised: a crash (e.g. an image the vision encoder chokes on) restarts the server; the
# sweep's requests retry a refused connection, so a crash costs seconds, not the shard.
(
  while true; do
    "$LLAMA_SERVER" -m "$GGUF" --mmproj "$MMPROJ" --alias base --host 127.0.0.1 --port 8000 -ngl 999 \
      --parallel "$SLOTS" -c $((SLOTS * 24576)) --jinja -fa on --no-webui \
      >> "$OUT/llama-server.log" 2>&1
    echo "== $(date -u +%H:%M:%S) llama-server exited ($?), restarting; log tail:"; tail -25 "$OUT/llama-server.log"
    sleep 2
  done
) &
SRV=$!
trap 'kill $SRV 2>/dev/null; pkill -f llama-server' EXIT
for _ in $(seq 180); do
  curl -sf http://127.0.0.1:8000/v1/models >/dev/null && break
  sleep 5
done
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv

if [ -n "${SMOKE:-}" ]; then
  step "smoke: $SMOKE items per subtype"
  python3 scripts/subtype_sweep.py --base-url http://127.0.0.1:8000/v1 --papers "$PAPERS" --per-subtype "$SMOKE" \
    --concurrency "$SLOTS" $RAWFLAG --out "$OUT/smoke" ${SWEEP_ARGS:-}
  blanks=$(cat "$OUT"/smoke/*/*/answers.jsonl | python3 -c "import sys,json;print(sum(1 for l in sys.stdin if not json.loads(l).get('answer','').strip()))")
  restarts=$(grep -c "llama-server exited" "$OUT/job.log")
  step "smoke: $blanks blank answers, $restarts server restarts"
  [ "$blanks" = 0 ] && [ "$restarts" = 0 ] || { step "SMOKE FAILED"; exit 3; }
fi

step "sweep papers=$PAPERS shard=$SHARD"
python3 scripts/subtype_sweep.py --base-url http://127.0.0.1:8000/v1 --papers "$PAPERS" --shard "$SHARD" \
  --concurrency "$SLOTS" $RAWFLAG --emit --out "$OUT" ${SWEEP_ARGS:-}
rc=$?
step "done (exit $rc): $OUT"
exit $rc
