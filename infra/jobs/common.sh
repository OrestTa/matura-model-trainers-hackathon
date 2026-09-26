# Shared setup for jobs that run ON the GPU instance. Source it; don't run it.
# Expects the repo unpacked in /opt/work/repo, and BUCKET and NAME set
# (outputs go to s3://$BUCKET/$NAME/).
[ -n "${JOBS_COMMON_LOADED:-}" ] && return 0
JOBS_COMMON_LOADED=1
set -uo pipefail
: "${BUCKET:?}" "${NAME:?}"
WORK=/opt/work; OUT=$WORK/out; REPO=$WORK/repo
export HF_HOME=$WORK/hf HF_HUB_ENABLE_HF_TRANSFER=1
[ -n "${HF_TOKEN:-}" ] && export HF_TOKEN
mkdir -p "$OUT" "$HF_HOME"
exec > >(tee -a "$OUT/job.log") 2>&1

step() { echo "== $(date -u +%H:%M:%S) $*"; }

step "setting up"
if [ ! -x $WORK/venv/bin/vllm ]; then
  python3 -m venv $WORK/venv
  $WORK/venv/bin/pip install -q --upgrade pip
  # vllm pins a compatible torch; the training stack goes on top of it.
  $WORK/venv/bin/pip install -q vllm bitsandbytes hf_transfer pyyaml matplotlib pymupdf \
    trl peft datasets accelerate
fi
source $WORK/venv/bin/activate
pip install -q -e "$REPO"
cd "$REPO"

# Eval set: from S3 if uploaded, else build it from the CKE papers.
EVAL=$REPO/data/eval/matura.jsonl
mkdir -p "$(dirname "$EVAL")"
if ! aws s3 cp "s3://$BUCKET/data/eval/matura.jsonl" "$EVAL" --only-show-errors; then
  step "no eval set in S3, building it from the CKE papers"
  python scripts/fetch_matura.py -o "$EVAL" && aws s3 cp "$EVAL" "s3://$BUCKET/data/eval/matura.jsonl" --only-show-errors \
    || EVAL=$REPO/examples/sample_questions.jsonl
fi

GPU_LIST=($(nvidia-smi --query-gpu=index --format=csv,noheader))
step "${#GPU_LIST[@]} GPUs, eval set $EVAL"

# Serves a HF model with vLLM on the given GPUs and waits until it answers.
# Usage: serve_vllm <hf_id> <gpus csv> <port> <served-name>; sets SERVED_PID.
serve_vllm() {
  local tp; tp=$(echo "$2" | tr ',' '\n' | wc -l)
  CUDA_VISIBLE_DEVICES=$2 vllm serve "$1" --served-model-name "$4" --port "$3" \
    --tensor-parallel-size "$tp" --max-model-len 16384 --gpu-memory-utilization 0.9 \
    > "$OUT/vllm-$4.log" 2>&1 &
  SERVED_PID=$!
  for _ in $(seq 360); do
    curl -sf "http://127.0.0.1:$3/v1/models" >/dev/null && return 0
    kill -0 $SERVED_PID 2>/dev/null || { echo "vLLM for $1 died, see $OUT/vllm-$4.log"; return 1; }
    sleep 10
  done
  return 1
}

sync_out() { aws s3 sync "$OUT" "s3://$BUCKET/$NAME/" --only-show-errors; }

finish() {
  sync_out
  step "done (exit $1); results in s3://$BUCKET/$NAME/"
  if [ "${STOP_WHEN_DONE:-1}" = 1 ]; then
    echo "Powering off (instance terminates)"
    shutdown -h +1
  fi
  exit "$1"
}
