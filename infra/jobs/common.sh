# Shared setup for the GPU jobs (baselines.sh, train.sh). Source it; don't run it.
# Works on any Linux box with NVIDIA GPUs (Nebius, Modal, a rented server, ...):
#   bash infra/jobs/baselines.sh           # from a checkout of this repo
# Outputs go to $WORK/out (default ./work/out in the repo). When BUCKET is set (the
# EC2 path, infra/jobs/ec2_job.sh), data and results also sync to s3://$BUCKET/$NAME/.
[ -n "${JOBS_COMMON_LOADED:-}" ] && return 0
JOBS_COMMON_LOADED=1
set -uo pipefail
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK="${WORK:-$REPO/work}"; OUT="${OUT:-$WORK/out}"
NAME="${NAME:-$(basename "$0" .sh)-$(date -u +%m%d-%H%M)}"
BUCKET="${BUCKET:-}"
export HF_HOME="${HF_HOME:-$WORK/hf}" HF_HUB_ENABLE_HF_TRANSFER=1
[ -n "${HF_TOKEN:-}" ] && export HF_TOKEN
mkdir -p "$OUT" "$HF_HOME"
exec > >(tee -a "$OUT/job.log") 2>&1

# S3 only when a bucket is configured; otherwise a no-op that reports failure.
s3() { [ -n "$BUCKET" ] && aws s3 "$@" --only-show-errors; }

step() { echo "== $(date -u +%H:%M:%S) $*"; }

step "setting up"
if command -v vllm >/dev/null && python3 -c "import trl, peft, matplotlib" 2>/dev/null; then
  :  # the box already has the stack (e.g. a prepared image)
elif [ ! -x $WORK/venv/bin/vllm ]; then
  python3 -m venv $WORK/venv
  $WORK/venv/bin/pip install -q --upgrade pip
  # vllm pins a compatible torch; the training stack goes on top of it.
  $WORK/venv/bin/pip install -q vllm bitsandbytes hf_transfer pyyaml matplotlib pymupdf \
    trl peft datasets accelerate
fi
[ -f $WORK/venv/bin/activate ] && source $WORK/venv/bin/activate
pip install -q -e "$REPO"
cd "$REPO"

# Eval set: local file, else S3, else build it from the CKE papers.
EVAL=$REPO/data/eval/matura.jsonl
mkdir -p "$(dirname "$EVAL")"
if [ ! -s "$EVAL" ] && ! s3 cp "s3://$BUCKET/data/eval/matura.jsonl" "$EVAL"; then
  step "no eval set yet, building it from the CKE papers"
  if python scripts/fetch_matura.py -o "$EVAL"; then s3 cp "$EVAL" "s3://$BUCKET/data/eval/matura.jsonl"
  else EVAL=$REPO/examples/sample_questions.jsonl; fi
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

sync_out() { s3 sync "$OUT" "s3://$BUCKET/$NAME/"; }

finish() {
  sync_out
  step "done (exit $1); results in $OUT${BUCKET:+ and s3://$BUCKET/$NAME/}"
  # Power off only on the throwaway EC2 instances (bucket set), never on a shared box.
  if [ -n "$BUCKET" ] && [ "${STOP_WHEN_DONE:-1}" = 1 ]; then
    echo "Powering off (instance terminates)"
    shutdown -h +1
  fi
  exit "$1"
}
