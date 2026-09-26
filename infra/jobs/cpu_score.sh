#!/usr/bin/env bash
# Scores one GGUF on CPU (no GPU, no vLLM): scripts/cpu_serve.py + run_baselines.py --base-url.
# Made for Solari sandboxes (infra/solari/sol_job.py), works on any Linux box with Python 3.10+.
#   MODEL=qwen3-0.6b GGUF_REPO=unsloth/Qwen3-0.6B-GGUF GGUF_FILE=Qwen3-0.6B-Q8_0.gguf \
#     bash infra/jobs/cpu_score.sh
# MODEL is a configs/models.yaml key (for routing/prompt settings); MODES (default raw,routed),
# EVAL (default data/eval/matura.jsonl), MODELS_CONFIG (default configs/models.yaml), ROUTES (default configs/routes.yaml),
# TEXT_ONLY=1, JUDGE_URL/JUDGE_MODEL pass through. OCR=1 installs tesseract (pol) first, for configs/routes_ocr.yaml.
# GGUF_PATH=/path/model.gguf skips the download. Outputs in $OUT; last line "done (exit N)".
set -uo pipefail
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK="${WORK:-$REPO/work}"; OUT="${OUT:-$WORK/out/cpu_score}"
export HF_HOME="${HF_HOME:-$WORK/hf}"
mkdir -p "$OUT" "$HF_HOME"
exec > >(tee -a "$OUT/job.log") 2>&1
step() { echo "== $(date -u +%H:%M:%S) $*"; }
finish() { rc=$?; kill "${SRV:-}" 2>/dev/null; echo "== $(date -u +%H:%M:%S) done (exit $rc); out $OUT"; }
trap finish EXIT
cd "$REPO"

step "setting up (job ${JOB_ID:-$NAME})"
VENV="$WORK/venv-cpu"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
source "$VENV/bin/activate"
python -c "import llama_cpp" 2>/dev/null || pip install -q llama-cpp-python \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu || exit 1
pip install -q fastapi uvicorn jinja2 huggingface_hub pyyaml && pip install -q -e "$REPO" || exit 1
if [ -n "${OCR:-}" ]; then
  command -v tesseract >/dev/null || { apt-get update -qq && apt-get install -y -qq tesseract-ocr tesseract-ocr-pol >/dev/null; } || exit 1
  tesseract --list-langs 2>/dev/null | grep -qx pol || { echo "tesseract pol missing"; exit 1; }
  pip install -q pymupdf || exit 1
fi

if [ -z "${GGUF_PATH:-}" ]; then
  step "downloading $GGUF_REPO/$GGUF_FILE"
  GGUF_PATH=$(python -c "from huggingface_hub import hf_hub_download as d; print(d('$GGUF_REPO', '$GGUF_FILE'))") || exit 1
fi
ls -la "$GGUF_PATH"

step "serving on CPU ($(nproc) cores)"
python scripts/cpu_serve.py "$GGUF_PATH" --port 8000 --threads "$(nproc)" > "$OUT/cpu_serve.log" 2>&1 &
SRV=$!
for _ in $(seq 120); do curl -sf localhost:8000/v1/models >/dev/null && break; sleep 5; done
curl -sf localhost:8000/v1/models >/dev/null || { tail "$OUT/cpu_serve.log"; exit 1; }

step "scoring $MODEL (${MODES:-raw,routed})"
python scripts/run_baselines.py --models "$MODEL" --base-url http://localhost:8000/v1 \
  --modes "${MODES:-raw,routed}" --routes "${ROUTES:-$REPO/configs/routes.yaml}" --models-config "${MODELS_CONFIG:-$REPO/configs/models.yaml}" --eval "${EVAL:-$REPO/data/eval/matura.jsonl}" --out "$OUT" \
  --concurrency 1 ${TEXT_ONLY:+--text-only} \
  ${JUDGE_URL:+--judge-url "$JUDGE_URL" --judge-model "${JUDGE_MODEL:-judge}"}
