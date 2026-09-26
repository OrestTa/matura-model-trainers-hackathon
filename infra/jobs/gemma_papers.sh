#!/usr/bin/env bash
# One GPU, no vLLM: serves a llama.cpp model from configs/models.yaml (default the think8k Gemma)
# the way scripts/serve_exam.sh does (same slots and context, mmproj for pictures, no router
# process) and answers each paper's organisers'-format package with scripts/run_exam.py.
# The lean twin of rehearsal.sh for the llama.cpp CUDA image (infra/modal/claude_gemma.py). Env:
#   MODEL=gemma4-12b-think8k  PAPERS="probny-2026-01"  MODE=raw  EVAL=data/eval/matura_all.jsonl
#   OUT=work/out/gemma-papers  LLAMA_SERVER=/app/llama-server
set -uo pipefail
cd "$(dirname "$0")/../.."
MODEL="${MODEL:-gemma4-12b-think8k}"; PAPERS="${PAPERS:-probny-2026-01}"; MODE="${MODE:-raw}"
EVAL="${EVAL:-data/eval/matura_all.jsonl}"; OUT="${OUT:-work/out/gemma-papers}"; WORK="${WORK:-work}"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/job.log") 2>&1
step() { echo "== $(date -u +%H:%M:%S) $*"; }
[ -s "$EVAL" ] || { step "no $EVAL"; exit 1; }

LLAMA_SERVER="${LLAMA_SERVER:-$(command -v llama-server || ls /app/llama-server 2>/dev/null)}"
export LD_LIBRARY_PATH="$(dirname "$LLAMA_SERVER"):${LD_LIBRARY_PATH:-}"
spec() { python3 -c "import yaml; print(yaml.safe_load(open('configs/models.yaml'))['models']['$MODEL'].get('$1') or '')"; }
SLOTS="$(spec parallel)"; SLOTS="${SLOTS:-16}"; CTX="$(spec ctx_per_slot)"; CTX="${CTX:-8192}"

step "downloading $MODEL"
read -r GGUF MMPROJ < <(python3 - "$MODEL" <<'PY'
import sys, yaml
from huggingface_hub import hf_hub_download as d
s = yaml.safe_load(open("configs/models.yaml"))["models"][sys.argv[1]]
print(d(s["hf_id"], s["gguf_file"]), d(s["hf_id"], s["mmproj_file"]) if s.get("mmproj_file") else "")
PY
)
[ -s "$GGUF" ] || { step "download failed"; exit 1; }

step "llama-server, $SLOTS slots x $CTX"
"$LLAMA_SERVER" -m "$GGUF" ${MMPROJ:+--mmproj "$MMPROJ"} --alias base --host 127.0.0.1 --port 8000 -ngl 999 \
  --parallel "$SLOTS" -c $((SLOTS * CTX)) --jinja -fa on --no-webui > "$OUT/llama-server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 180); do
  curl -sf http://127.0.0.1:8000/v1/models >/dev/null && break
  kill -0 $SRV 2>/dev/null || { tail -30 "$OUT/llama-server.log"; exit 1; }
  sleep 5
done
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv

rc=0
printf "paper\titems\tseconds\n" > "$OUT/timing.tsv"
for p in $PAPERS; do
  step "paper $p ($MODE)"
  python3 scripts/make_exam_package.py "$p" --eval "$EVAL" -o "$WORK/packages/$p" || { rc=1; continue; }
  mkdir -p "$OUT/$p"
  t0=$(date +%s)
  python3 scripts/run_exam.py "$WORK/packages/$p" --model "$MODEL" --mode "$MODE" --concurrency "${CONCURRENCY:-$SLOTS}" \
    -o "$OUT/$p/answers.json" || rc=1
  n=$(python3 -c "import json; print(len(json.load(open('$WORK/packages/$p/exam.json'))['items']))")
  printf "%s\t%s\t%s\n" "$p" "$n" "$(( $(date +%s) - t0 ))" | tee -a "$OUT/timing.tsv"
done
step "done (exit $rc): $OUT"
exit $rc
