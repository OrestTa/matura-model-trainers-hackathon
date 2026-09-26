#!/usr/bin/env bash
# Terminates every project instance in every region. Pass --all to also delete the S3 bucket.
source "$(dirname "$0")/common.sh"
for r in "${REGIONS[@]}"; do
  ids=$(aws ec2 describe-instances --region "$r" \
    --filters "Name=tag:Project,Values=${PROJECT_TAG}" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].InstanceId' --output text)
  if [ -n "$ids" ]; then
    echo "$r: terminating $ids"
    aws ec2 terminate-instances --region "$r" --instance-ids $ids --output text >/dev/null
  fi
done
if [ "${1:-}" = "--all" ]; then
  aws s3 rb "s3://$(bucket_name)" --force
fi
echo "Done."
