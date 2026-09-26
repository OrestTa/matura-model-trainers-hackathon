# Shared settings for the AWS scripts. Source this file; don't run it.
set -euo pipefail

# Optional: read the AWS key from 1Password with a service account. Set OP_SERVICE_ACCOUNT_TOKEN
# and AWS_OP_ITEM (e.g. "op://Hackathon/AWS root key") in the environment; the item needs
# fields named "access key id" and "secret access key".
if [ -n "${OP_SERVICE_ACCOUNT_TOKEN:-}" ] && [ -n "${AWS_OP_ITEM:-}" ]; then
  AWS_ACCESS_KEY_ID="$(op read "${AWS_OP_ITEM}/access key id")"
  AWS_SECRET_ACCESS_KEY="$(op read "${AWS_OP_ITEM}/secret access key")"
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
fi

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PROJECT_TAG="matura-hackathon"
REGIONS=(us-east-1 us-east-2 us-west-2)

# Every instance powers off (and terminates) by this time: Sun 27 Sep 2026 10:30 CEST,
# 30 minutes before the exam cutoff.
DEADLINE_UTC="${DEADLINE_UTC:-2026-09-27T08:30:00Z}"

# Hard spending cap approved by Orest, in USD. launch.sh refuses to start an instance
# if the projected on-demand cost of everything running until DEADLINE_UTC would exceed it.
BUDGET_USD="${BUDGET_USD:-95000}"

# Card-charge guard: Orest wants only startup credits used, never the card on file.
# If month-to-date cost AFTER credits exceeds this (USD), launches are refused. Normal
# credited usage nets to ~0, so anything above a few dollars means credits aren't covering it.
MAX_NET_USD="${MAX_NET_USD:-5}"

ROLE_NAME="${PROJECT_TAG}-instance"
SG_NAME="${PROJECT_TAG}-sg"

account_id() { aws sts get-caller-identity --query Account --output text; }
bucket_name() { echo "${PROJECT_TAG}-$(account_id)"; }

# Approximate us-east-1 on-demand prices (USD/hour). Used only for the budget guard,
# so they err on the high side.
hourly_price() {
  case "$1" in
    p5en.48xlarge) echo 70 ;;
    p5e.48xlarge)  echo 65 ;;
    p5.48xlarge)   echo 60 ;;
    p5.4xlarge)    echo 8 ;;
    p4de.24xlarge) echo 45 ;;
    p4d.24xlarge)  echo 35 ;;
    g6e.48xlarge)  echo 32 ;;
    g6e.24xlarge)  echo 16 ;;
    g6e.12xlarge)  echo 11 ;;
    g6e.xlarge)    echo 2.5 ;;
    g6.xlarge)     echo 1 ;;
    *)             echo 100 ;;  # unknown type: assume expensive
  esac
}

hours_until_deadline() {
  python3 -c "
import datetime as d
end = d.datetime.fromisoformat('${DEADLINE_UTC}'.replace('Z', '+00:00'))
print(max(0.0, (end - d.datetime.now(d.timezone.utc)).total_seconds() / 3600))"
}

# Lists running or pending project instances in every region as: region id type launch-time
list_instances() {
  for r in "${REGIONS[@]}"; do
    aws ec2 describe-instances --region "$r" \
      --filters "Name=tag:Project,Values=${PROJECT_TAG}" "Name=instance-state-name,Values=pending,running" \
      --query 'Reservations[].Instances[].[InstanceId,InstanceType,LaunchTime,Tags[?Key==`Name`]|[0].Value]' \
      --output text | sed "s/^/$r\t/"
  done
}

# Month-to-date cost after credits and refunds, i.e. what would hit the card.
# Cost Explorer lags a few hours, so this catches trouble late but reliably.
net_cost_mtd() {
  aws ce get-cost-and-usage --region us-east-1 \
    --time-period Start="$(date -u +%Y-%m-01)",End="$(date -u -d tomorrow +%Y-%m-%d)" \
    --granularity MONTHLY --metrics UnblendedCost \
    --query 'ResultsByTime[0].Total.UnblendedCost.Amount' --output text
}

# Month-to-date cost before credits, i.e. how much credit has been used this month.
gross_cost_mtd() {
  aws ce get-cost-and-usage --region us-east-1 \
    --time-period Start="$(date -u +%Y-%m-01)",End="$(date -u -d tomorrow +%Y-%m-%d)" \
    --granularity MONTHLY --metrics UnblendedCost \
    --filter '{"Not":{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit","Refund"]}}}' \
    --query 'ResultsByTime[0].Total.UnblendedCost.Amount' --output text
}
