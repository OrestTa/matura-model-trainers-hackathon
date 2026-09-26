#!/usr/bin/env bash
# Runs on the GPU instance (started by infra/jobs/ec2_baselines.sh, via SSM as root).
# Expects the repo unpacked in /opt/work/repo. Env:
#   BUCKET, NAME          S3 bucket and run name (outputs go to s3://$BUCKET/$NAME/)
#   MODELS=all            keys from configs/models.yaml
#   MODES=raw,routed      baseline modes
#   HF_TOKEN              needed for gated models (Gemma)
#   STOP_WHEN_DONE=1      power off (= terminate) when finished, to save credits
set -uo pipefail
: "${BUCKET:?}" "${NAME:?}"
MODELS="${MODELS:-all}"; MODES="${MODES:-raw,routed}"
WORK=/opt/work; OUT=$WORK/out; REPO=$WORK/repo
export HF_HOME=$WORK/hf HF_HUB_ENABLE_HF_TRANSFER=1
[ -n "${HF_TOKEN:-}" ] && export HF_TOKEN
mkdir -p "$OUT" "$HF_HOME"
exec > >(tee -a "$OUT/job.log") 2>&1

echo "== $(date -u) setting up"
if [ ! -x $WORK/venv/bin/vllm ]; then
  python3 -m venv $WORK/venv
  $WORK/venv/bin/pip install -q --upgrade pip
  $WORK/venv/bin/pip install -q vllm bitsandbytes hf_transfer pyyaml matplotlib
fi
source $WORK/venv/bin/activate
pip install -q -e "$REPO"

EVAL=$REPO/data/eval/matura.jsonl
mkdir -p "$(dirname "$EVAL")"
if ! aws s3 cp "s3://$BUCKET/data/eval/matura.jsonl" "$EVAL" --only-show-errors; then
  echo "No eval set at s3://$BUCKET/data/eval/matura.jsonl, using the sample questions"
  EVAL=$REPO/examples/sample_questions.jsonl
fi

GPUS=$(nvidia-smi --query-gpu=index --format=csv,noheader | paste -sd,)
echo "== $(date -u) baselines: models=$MODELS modes=$MODES gpus=$GPUS eval=$EVAL"
cd "$REPO"
python scripts/run_baselines.py --eval "$EVAL" --models "$MODELS" --modes "$MODES" \
  --gpus "$GPUS" --out "$OUT/baselines"
status=$?
python scripts/plot_baselines.py --runs "$OUT/baselines" --out "$OUT/report"

aws s3 sync "$OUT" "s3://$BUCKET/$NAME/" --only-show-errors --exclude "*/vllm.log"
aws s3 sync "$OUT" "s3://$BUCKET/$NAME/" --only-show-errors --exclude "*" --include "*/vllm.log"
echo "== $(date -u) done (exit $status); results in s3://$BUCKET/$NAME/"

if [ "${STOP_WHEN_DONE:-1}" = 1 ]; then
  echo "Powering off (instance terminates)"
  shutdown -h +1
fi
exit $status
