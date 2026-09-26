#!/usr/bin/env bash
# Exam dress rehearsal: the exact on-stage path on past papers, timed.
# Builds an organisers'-format package per paper (scripts/make_exam_package.py), starts
# scripts/serve_exam.sh MODEL, answers each package with scripts/run_exam.py, and writes
# $OUT/<paper>/answers.json (+ .log.jsonl) and $OUT/timing.tsv. Grade the answers with
# scripts/grade_batches.py afterwards. Env:
#   MODEL=gemma4-12b              key from configs/models.yaml
#   PAPERS="2023-05 2024-05 2025-05 2026-05"
#   MODE=adapters                 run_exam.py mode (raw = bare-model submission)
source "$(dirname "$0")/common.sh"
MODEL="${MODEL:-gemma4-12b}"; PAPERS="${PAPERS:-2023-05 2024-05 2025-05 2026-05}"; MODE="${MODE:-adapters}"

python -c "import json; r=json.loads(open('$EVAL').readline()); exit(0 if 'images' in r or not r.get('needs_image') else 1)" \
  || { step "eval set has no pictures, rebuilding with --images"; python scripts/fetch_matura.py --images -o "$EVAL"; }
[ "$(python -c "import yaml; print(yaml.safe_load(open('configs/models.yaml'))['models']['$MODEL'].get('server',''))")" = llamacpp ] \
  && { ensure_llama_server || { step "llama.cpp build failed"; finish 1; }; }

step "downloading $MODEL while online"
python - "$MODEL" <<'PY'
import sys, yaml
from huggingface_hub import hf_hub_download, snapshot_download
s = yaml.safe_load(open("configs/models.yaml"))["models"][sys.argv[1]]
if s.get("gguf_file"):
    for f in (s["gguf_file"], s.get("mmproj_file")):
        f and print(hf_hub_download(s["hf_id"], f))
else:
    print(snapshot_download(s["hf_id"]))
PY

# llama-server can ignore SIGTERM, and serve_exam's router on :8080 outlives it: kill both hard,
# or the next rehearsal's run_exam talks to a stale router.
cleanup() {
  [ -n "$SERVE" ] && kill $SERVE 2>/dev/null; pkill -f "matura_router serve" 2>/dev/null
  pkill -f "llama-server.*--port 8000" 2>/dev/null; pkill -f "vllm serve.*--port 8000" 2>/dev/null
  sleep 5; pkill -9 -f "llama-server.*--port 8000" 2>/dev/null; pkill -9 -f "matura_router serve" 2>/dev/null
}
SERVE=
cleanup   # leftovers from an earlier run, BEFORE starting ours (after, it killed our own server)
trap cleanup EXIT
step "serving $MODEL offline (serve_exam.sh)"
mkdir -p work "$OUT"
bash scripts/serve_exam.sh "$MODEL" > "$OUT/serve_exam.log" 2>&1 &
SERVE=$!
for _ in $(seq 360); do
  curl -sf http://127.0.0.1:8000/v1/models >/dev/null && break
  kill -0 $SERVE 2>/dev/null || { cat "$OUT/serve_exam.log"; finish 1; }
  sleep 5
done

status=0
printf "paper\titems\tseconds\n" > "$OUT/timing.tsv"
for p in $PAPERS; do
  python scripts/make_exam_package.py "$p" --eval "$EVAL" -o "$WORK/packages/$p"
  mkdir -p "$OUT/$p"
  t0=$(date +%s)
  python scripts/run_exam.py "$WORK/packages/$p" --model "$MODEL" --mode "$MODE" --concurrency "${CONCURRENCY:-16}" \
    -o "$OUT/$p/answers.json" || status=1
  n=$(python -c "import json; print(len(json.load(open('$WORK/packages/$p/exam.json'))['items']))")
  printf "%s\t%s\t%s\n" "$p" "$n" "$(( $(date +%s) - t0 ))" | tee -a "$OUT/timing.tsv"
done
finish $status
