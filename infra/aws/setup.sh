#!/usr/bin/env bash
# One-time account setup: GPU quota requests, S3 bucket, instance role for SSM, security
# group, and a monthly budget alarm. Safe to re-run.
source "$(dirname "$0")/common.sh"

echo "== Identity"; aws sts get-caller-identity

BUCKET="$(bucket_name)"
ACCOUNT="$(account_id)"

echo "== GPU quotas (vCPUs)"
# L-417A185B: Running On-Demand P instances; L-DB2E81BA: Running On-Demand G and VT instances
WANT_P="${WANT_P:-384}"   # two p5.48xlarge
WANT_G="${WANT_G:-384}"
for r in "${REGIONS[@]}"; do
  for pair in "L-417A185B:$WANT_P" "L-DB2E81BA:$WANT_G"; do
    code="${pair%%:*}"; want="${pair##*:}"
    have=$(aws service-quotas get-service-quota --region "$r" --service-code ec2 --quota-code "$code" \
      --query 'Quota.Value' --output text 2>/dev/null || echo 0)
    echo "$r $code current=$have wanted=$want"
    if python3 -c "import sys; sys.exit(0 if float('$have') < float('$want') else 1)"; then
      aws service-quotas request-service-quota-increase --region "$r" --service-code ec2 \
        --quota-code "$code" --desired-value "$want" --query 'RequestedQuota.Status' --output text \
        || echo "  (request failed or one is already pending)"
    fi
  done
done

echo "== S3 bucket $BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [ "$AWS_DEFAULT_REGION" = us-east-1 ]; then
    aws s3api create-bucket --bucket "$BUCKET"
  else
    aws s3api create-bucket --bucket "$BUCKET" \
      --create-bucket-configuration LocationConstraint="$AWS_DEFAULT_REGION"
  fi
fi

echo "== Instance role $ROLE_NAME (SSM access + project bucket)"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam create-instance-profile --instance-profile-name "$ROLE_NAME" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$ROLE_NAME" --role-name "$ROLE_NAME"
fi
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name bucket --policy-document "{
  \"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"s3:*\",
  \"Resource\":[\"arn:aws:s3:::$BUCKET\",\"arn:aws:s3:::$BUCKET/*\"]}]}"

echo "== Security group $SG_NAME (no inbound; access is via SSM)"
for r in "${REGIONS[@]}"; do
  aws ec2 describe-security-groups --region "$r" --filters "Name=group-name,Values=$SG_NAME" \
    --query 'SecurityGroups[0].GroupId' --output text | grep -q '^sg-' \
    || aws ec2 create-security-group --region "$r" --group-name "$SG_NAME" \
         --description "matura hackathon, egress only" --query GroupId --output text
done

echo "== Budget alarm at \$$BUDGET_USD"
notif=()
if ! aws budgets describe-budget --account-id "$ACCOUNT" --budget-name "$PROJECT_TAG" >/dev/null 2>&1; then
  if [ -n "${BUDGET_EMAIL:-}" ]; then
    notif=(--notifications-with-subscribers "[
      {\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":50,\"ThresholdType\":\"PERCENTAGE\"},\"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"$BUDGET_EMAIL\"}]},
      {\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":90,\"ThresholdType\":\"PERCENTAGE\"},\"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"$BUDGET_EMAIL\"}]}]")
  fi
  aws budgets create-budget --account-id "$ACCOUNT" --budget "{
    \"BudgetName\":\"$PROJECT_TAG\",\"BudgetType\":\"COST\",\"TimeUnit\":\"MONTHLY\",
    \"BudgetLimit\":{\"Amount\":\"$BUDGET_USD\",\"Unit\":\"USD\"},
    \"CostTypes\":{\"IncludeCredit\":false,\"IncludeRefund\":false}}" "${notif[@]}"
fi
echo "== Card-charge alarm: cost after credits above \$$MAX_NET_USD"
if ! aws budgets describe-budget --account-id "$ACCOUNT" --budget-name "${PROJECT_TAG}-net" >/dev/null 2>&1; then
  aws budgets create-budget --account-id "$ACCOUNT" --budget "{
    \"BudgetName\":\"${PROJECT_TAG}-net\",\"BudgetType\":\"COST\",\"TimeUnit\":\"MONTHLY\",
    \"BudgetLimit\":{\"Amount\":\"$MAX_NET_USD\",\"Unit\":\"USD\"},
    \"CostTypes\":{\"IncludeCredit\":true,\"IncludeRefund\":true}}" "${notif[@]}"
fi
echo "Done."
