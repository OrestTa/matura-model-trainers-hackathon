#!/usr/bin/env bash
# Runs on the GPU instance (started by infra/jobs/ec2_baselines.sh, via SSM as root).
# Expects the repo unpacked in /opt/work/repo. Env:
#   BUCKET, NAME          S3 bucket and run name (outputs go to s3://$BUCKET/$NAME/)
#   MODELS=all            keys from configs/models.yaml
#   MODES=raw,routed      baseline modes
#   HF_TOKEN              needed for gated models (Gemma)
#   JUDGE_HF=Qwen/Qwen3-32B  open model that grades open answers (last 2 GPUs); "" = no judge
#   STOP_WHEN_DONE=1      power off (= terminate) when finished, to save credits
set -uo pipefail
: "${BUCKET:?}" "${NAME:?}"
MODELS="${MODELS:-all}"; MODES="${MODES:-raw,routed}"; JUDGE_HF="${JUDGE_HF-Qwen/Qwen3-32B}"
WORK=/opt/work; OUT=$WORK/out; REPO=$WORK/repo
export HF_HOME=$WORK/hf HF_HUB_ENABLE_HF_TRANSFER=1
[ -n "${HF_TOKEN:-}" ] && export HF_TOKEN
mkdir -p "$OUT" "$HF_HOME"
exec > >(tee -a "$OUT/job.log") 2>&1

echo "== $(date -u) setting up"
if [ ! -x $WORK/venv/bin/vllm ]; then
  python3 -m venv $WORK/venv
  $WORK/venv/bin/pip install -q --upgrade pip
  $WORK/venv/bin/pip install -q vllm bitsandbytes hf_transfer pyyaml matplotlib pymupdf
fi
source $WORK/venv/bin/activate
pip install -q -e "$REPO"

EVAL=$REPO/data/eval/matura.jsonl
mkdir -p "$(dirname "$EVAL")"
if ! aws s3 cp "s3://$BUCKET/data/eval/matura.jsonl" "$EVAL" --only-show-errors; then
  echo "No eval set in S3, building it from the CKE papers"
  python "$REPO/scripts/fetch_matura.py" -o "$EVAL" || EVAL=$REPO/examples/sample_questions.jsonl
fi

ALL=($(nvidia-smi --query-gpu=index --format=csv,noheader))
JUDGE_ARGS=()
if [ -n "$JUDGE_HF" ] && [ ${#ALL[@]} -ge 4 ]; then
  n=${#ALL[@]}
  JUDGE_ARGS=(--judge-hf "$JUDGE_HF" --judge-gpus "${ALL[n-2]},${ALL[n-1]}")
  ALL=("${ALL[@]:0:n-2}")
elif [ -n "$JUDGE_HF" ]; then
  echo "Fewer than 4 GPUs: no judge, open answers without keywords stay unscored"
fi
GPUS=$(IFS=,; echo "${ALL[*]}")
echo "== $(date -u) baselines: models=$MODELS modes=$MODES gpus=$GPUS judge=${JUDGE_HF:-none} eval=$EVAL"
cd "$REPO"
python scripts/run_baselines.py --eval "$EVAL" --models "$MODELS" --modes "$MODES" \
  --gpus "$GPUS" --out "$OUT/baselines" "${JUDGE_ARGS[@]}"
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
