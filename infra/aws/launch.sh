#!/usr/bin/env bash
# Launches one GPU instance that terminates itself at DEADLINE_UTC.
# Usage: launch.sh <instance-type> [name] [region]
# Example: launch.sh p5.48xlarge train-bielik us-east-1
source "$(dirname "$0")/common.sh"

TYPE="${1:?instance type required}"
NAME="${2:-$TYPE}"
REGION="${3:-$AWS_DEFAULT_REGION}"
DISK_GB="${DISK_GB:-1000}"
BUCKET="$(bucket_name)"

# Card guard: refuse if anything is already being billed beyond the credits.
net=$(net_cost_mtd)
echo "Month-to-date cost after credits: \$$net (limit \$$MAX_NET_USD)"
if python3 -c "import sys; sys.exit(0 if float('$net') > float('$MAX_NET_USD') else 1)"; then
  echo "Refusing: usage is being charged beyond the credits. Check Billing > Credits." >&2; exit 1
fi

# Budget guard: projected cost of everything running (plus this one) until the deadline.
hours=$(hours_until_deadline)
projected=$(hourly_price "$TYPE")
while read -r _ _ t _ _; do
  [ -n "${t:-}" ] && projected=$(python3 -c "print($projected + $(hourly_price "$t"))")
done < <(list_instances)
projected=$(python3 -c "print(round($projected * $hours))")
echo "Projected on-demand cost of all instances until $DEADLINE_UTC: \$$projected (cap \$$BUDGET_USD)"
if [ "$projected" -gt "$BUDGET_USD" ]; then
  echo "Refusing: would exceed the budget cap." >&2; exit 1
fi

# Latest AWS Deep Learning AMI (PyTorch, Ubuntu 22.04, NVIDIA driver preinstalled).
AMI=$(aws ssm get-parameters-by-path --region "$REGION" \
  --path /aws/service/deeplearning/ami/x86_64/ --recursive \
  --query 'Parameters[?contains(Name, `oss-nvidia-driver-gpu-pytorch`) && contains(Name, `ubuntu-22.04`) && ends_with(Name, `latest/ami-id`)].[Name,Value]' \
  --output text | sort | tail -1 | cut -f2)
[ -n "$AMI" ] || { echo "Could not resolve a Deep Learning AMI in $REGION" >&2; exit 1; }

SG=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=$SG_NAME" \
  --query 'SecurityGroups[0].GroupId' --output text)

MINUTES=$(python3 -c "print(max(1, int($hours * 60)))")
USER_DATA=$(cat <<UD
#!/bin/bash
# Hard stop at the deadline; shutdown behavior is terminate, so this ends billing.
shutdown -h +$MINUTES
mkdir -p /opt/work && chown ubuntu:ubuntu /opt/work
# Push /opt/work/out to S3 every 10 minutes so nothing is lost at shutdown.
echo "*/10 * * * * ubuntu aws s3 sync /opt/work/out s3://$BUCKET/$NAME/ --only-show-errors" > /etc/cron.d/s3sync
UD
)

aws ec2 run-instances --region "$REGION" \
  --image-id "$AMI" --instance-type "$TYPE" \
  --iam-instance-profile Name="$ROLE_NAME" \
  --security-group-ids "$SG" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$DISK_GB,\"VolumeType\":\"gp3\",\"Throughput\":1000,\"Iops\":16000,\"DeleteOnTermination\":true}}]" \
  --metadata-options HttpTokens=required \
  --user-data "$USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Project,Value=$PROJECT_TAG},{Key=Name,Value=$NAME}]" \
                       "ResourceType=volume,Tags=[{Key=Project,Value=$PROJECT_TAG}]" \
  --query 'Instances[0].[InstanceId,InstanceType,Placement.AvailabilityZone]' --output text
echo "Self-terminates in $MINUTES minutes. Outputs in /opt/work/out sync to s3://$BUCKET/$NAME/"
