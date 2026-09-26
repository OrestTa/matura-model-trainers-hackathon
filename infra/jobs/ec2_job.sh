#!/usr/bin/env bash
# Runs a job from infra/jobs on a fresh EC2 GPU instance and downloads its results.
# NOTE 2026-09-26: the AWS account was suspended; run the jobs directly on another
# GPU box instead (bash infra/jobs/baselines.sh). Kept in case AWS comes back.
#
#   infra/jobs/ec2_job.sh baselines                  # score every model, draw charts
#   infra/jobs/ec2_job.sh train                      # synthetic data -> adapters -> re-score
#   MODELS=bielik-11b,qwen3-8b infra/jobs/ec2_job.sh baselines
#   TRAIN_MODELS=bielik-11b,qwen3-8b TYPE=p5.48xlarge infra/jobs/ec2_job.sh train
#
# Uses the guarded launcher in infra/aws (credit-only, budget cap, self-terminates at
# the deadline). Code ships as a tarball of HEAD through S3, so the instance needs no
# GitHub access; commit first. A local data/eval/matura.jsonl and
# data/train/synthetic.jsonl are uploaded too. The instance powers off when the job
# ends (STOP_WHEN_DONE=0 keeps it). Job settings (MODELS, MODES, TRAIN_MODELS,
# TEACHER_HF, PER_CATEGORY, REGEN_DATA, EPOCHS, JUDGE_HF, HF_TOKEN) pass through.
source "$(dirname "$0")/../aws/common.sh"
JOB="${1:?job name: baselines or train}"
[ -f "$(dirname "$0")/$JOB.sh" ] || { echo "no such job: $JOB" >&2; exit 1; }
cd "$(git rev-parse --show-toplevel)"

TYPE="${TYPE:-g6e.48xlarge}"   # 8x L40S 48 GB
REGION="${REGION:-$AWS_DEFAULT_REGION}"
NAME="${NAME:-$JOB-$(date -u +%m%d-%H%M)}"
BUCKET="$(bucket_name)"

echo "Uploading code ($(git rev-parse --short HEAD)) to s3://$BUCKET/code/$NAME.tar.gz"
git archive --format=tar.gz HEAD | aws s3 cp - "s3://$BUCKET/code/$NAME.tar.gz" --only-show-errors
for f in data/eval/matura.jsonl data/train/synthetic.jsonl data/train/past_papers.jsonl; do
  [ -f "$f" ] && aws s3 cp "$f" "s3://$BUCKET/$f" --only-show-errors
done

ID=$("$(dirname "$0")/../aws/launch.sh" "$TYPE" "$NAME" "$REGION" | tee /dev/stderr | grep -o 'i-[0-9a-f]\{8,\}' | head -1)
[ -n "$ID" ] || { echo "launch failed" >&2; exit 1; }

echo "Waiting for $ID to register with SSM..."
until [ "$(aws ssm describe-instance-information --region "$REGION" \
          --filters "Key=InstanceIds,Values=$ID" \
          --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = Online ]; do
  sleep 15
done

ENV="BUCKET=$BUCKET NAME=$NAME WORK=/opt/work STOP_WHEN_DONE=${STOP_WHEN_DONE:-1}"
for v in MODELS MODES TRAIN_MODELS TEACHER_HF PER_CATEGORY REGEN_DATA EPOCHS JUDGE_HF HF_TOKEN; do
  [ -n "${!v+x}" ] && ENV="$ENV $v='${!v}'"
done
CMD="mkdir -p /opt/work/repo && aws s3 cp s3://$BUCKET/code/$NAME.tar.gz - | tar xz -C /opt/work/repo && \
$ENV bash /opt/work/repo/infra/jobs/$JOB.sh 2>&1 | tail -60"
echo "Running $JOB on $ID. Progress: aws s3 cp s3://$BUCKET/$NAME/job.log - (synced every 10 min)"
"$(dirname "$0")/../aws/run.sh" "$ID" "$CMD" "$REGION"

mkdir -p "runs/ec2/$NAME"
aws s3 sync "s3://$BUCKET/$NAME/" "runs/ec2/$NAME/" --only-show-errors --exclude "adapters/*"
echo "Report: runs/ec2/$NAME/report/index.html"
