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
mkdir -p work "$OUT"
# llama-server on H100 sometimes aborts mid-paper ("CUDA error: an illegal instruction" in
# ggml_backend_cuda_synchronize, seen with both the ghcr image and our sm90 build): every later
# request is refused. So a paper that comes back >10% blank (run_exam exit 2) or whose server died
# is re-run on a fresh server, with CUDA graphs off and half the concurrency, up to 2 more times;
# the attempt with the fewest blanks is kept.
start_server() {
  [ -n "$SERVE" ] && cleanup
  step "serving $MODEL offline (serve_exam.sh)${1:+, $1}"
  bash scripts/serve_exam.sh "$MODEL" >> "$OUT/serve_exam.log" 2>&1 &
  SERVE=$!
  for _ in $(seq 360); do
    curl -sf http://127.0.0.1:8000/v1/models >/dev/null && return 0
    kill -0 $SERVE 2>/dev/null || { tail -50 "$OUT/serve_exam.log"; return 1; }
    sleep 5
  done
  return 1
}
blanks() { python -c "import json; a=json.load(open('$1'))['answers']; print(sum(not str(x.get('answer') or '').strip() for x in a))" 2>/dev/null || echo 9999; }
start_server || { step "server never came up"; tail -50 "$OUT/serve_exam.log"; finish 1; }

status=0
printf "paper\titems\tseconds\n" > "$OUT/timing.tsv"
for p in $PAPERS; do
  python scripts/make_exam_package.py "$p" --eval "$EVAL" -o "$WORK/packages/$p"
  mkdir -p "$OUT/$p"
  t0=$(date +%s); conc="${CONCURRENCY:-16}"; best=9999
  for attempt in 1 2 3; do
    python scripts/run_exam.py "$WORK/packages/$p" --model "$MODEL" --mode "$MODE" --concurrency "$conc" \
      -o "$OUT/$p/try$attempt.json"; rc=$?
    b=$(blanks "$OUT/$p/try$attempt.json")
    step "$p attempt $attempt: exit $rc, $b blank"
    if [ "$b" -lt "$best" ]; then best=$b; cp "$OUT/$p/try$attempt.json" "$OUT/$p/answers.json"
      [ -f "$OUT/$p/try$attempt.json.log.jsonl" ] && cp "$OUT/$p/try$attempt.json.log.jsonl" "$OUT/$p/answers.json.log.jsonl"; fi
    alive=1; curl -sf http://127.0.0.1:8000/v1/models >/dev/null || alive=0
    [ "$rc" != 2 ] && [ "$alive" = 1 ] && break
    [ "$attempt" = 3 ] && break
    tail -20 work/exam-vllm.log 2>/dev/null | grep -iE "error|abort" | tail -3
    export GGML_CUDA_DISABLE_GRAPHS=1; conc=$(( conc > 2 ? conc / 2 : 1 ))
    start_server "retry $((attempt + 1)): CUDA graphs off, concurrency $conc" || { step "restart failed"; break; }
  done
  n=$(python -c "import json; print(len(json.load(open('$WORK/packages/$p/exam.json'))['items']))")
  # A dead server gives all-blank answers: keep them out of answers.json so nobody grades a 0.
  if [ "$best" -ge "$n" ]; then
    step "$p: every answer blank"; mv -f "$OUT/$p/answers.json" "$OUT/$p/answers.FAILED.json" 2>/dev/null; status=1
  elif [ $(( best * 10 )) -gt "$n" ]; then
    step "$p: still $best/$n blank after retries"; status=1
  fi
  printf "%s\t%s\t%s\n" "$p" "$n" "$(( $(date +%s) - t0 ))" | tee -a "$OUT/timing.tsv"
done
finish $status
