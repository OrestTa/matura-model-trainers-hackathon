#!/usr/bin/env bash
# Runs the model baselines on an EC2 GPU instance and downloads the charts.
#
#   infra/jobs/ec2_baselines.sh                         # all models, raw + routed
#   MODELS=bielik-11b,qwen3-8b TYPE=g6e.12xlarge infra/jobs/ec2_baselines.sh
#
# Uses the guarded launcher in infra/aws (credit-only, budget cap, self-terminates at
# the deadline). Code ships as a tarball of HEAD through S3, so the instance needs
# no GitHub access. If data/eval/matura.jsonl exists locally it is uploaded as the
# eval set; otherwise the instance uses the one already in S3, or the samples.
# The instance powers off (terminates) when the job ends; set STOP_WHEN_DONE=0 to keep it.
source "$(dirname "$0")/../aws/common.sh"
cd "$(git rev-parse --show-toplevel)"

TYPE="${TYPE:-g6e.12xlarge}"   # 4x L40S 48 GB: four models at a time
REGION="${REGION:-$AWS_DEFAULT_REGION}"
NAME="${NAME:-baselines-$(date -u +%m%d-%H%M)}"
MODELS="${MODELS:-all}"; MODES="${MODES:-raw,routed}"
BUCKET="$(bucket_name)"

echo "Uploading code ($(git rev-parse --short HEAD)) to s3://$BUCKET/code/$NAME.tar.gz"
git archive --format=tar.gz HEAD | aws s3 cp - "s3://$BUCKET/code/$NAME.tar.gz" --only-show-errors
if [ -f data/eval/matura.jsonl ]; then
  aws s3 cp data/eval/matura.jsonl "s3://$BUCKET/data/eval/matura.jsonl" --only-show-errors
fi

ID=$("$(dirname "$0")/../aws/launch.sh" "$TYPE" "$NAME" "$REGION" | tee /dev/stderr | grep -o 'i-[0-9a-f]\{8,\}' | head -1)
[ -n "$ID" ] || { echo "launch failed" >&2; exit 1; }

echo "Waiting for $ID to register with SSM..."
until [ "$(aws ssm describe-instance-information --region "$REGION" \
          --filters "Key=InstanceIds,Values=$ID" \
          --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = Online ]; do
  sleep 15
done

CMD="mkdir -p /opt/work/repo && aws s3 cp s3://$BUCKET/code/$NAME.tar.gz - | tar xz -C /opt/work/repo && \
BUCKET=$BUCKET NAME=$NAME MODELS=$MODELS MODES=$MODES HF_TOKEN=${HF_TOKEN:-} \
STOP_WHEN_DONE=${STOP_WHEN_DONE:-1} bash /opt/work/repo/infra/jobs/baselines.sh 2>&1 | tail -40"
echo "Running baselines on $ID (progress: aws s3 cp s3://$BUCKET/$NAME/job.log -)"
"$(dirname "$0")/../aws/run.sh" "$ID" "$CMD" "$REGION"

mkdir -p "runs/ec2/$NAME"
aws s3 sync "s3://$BUCKET/$NAME/" "runs/ec2/$NAME/" --only-show-errors
echo "Report: runs/ec2/$NAME/report/index.html"
