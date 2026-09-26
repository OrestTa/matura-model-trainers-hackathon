#!/usr/bin/env bash
# Runs a shell command on an instance through SSM (no SSH needed) and prints its output.
# Usage: run.sh <instance-id> <command> [region]
source "$(dirname "$0")/common.sh"
ID="${1:?instance id}"; CMD="${2:?command}"; REGION="${3:-$AWS_DEFAULT_REGION}"
params=$(python3 -c "import json,sys; print(json.dumps({'commands':[sys.argv[1]],'executionTimeout':['172800']}))" "$CMD")
cid=$(aws ssm send-command --region "$REGION" --instance-ids "$ID" \
  --document-name AWS-RunShellScript --parameters "$params" --query Command.CommandId --output text)
while :; do
  st=$(aws ssm get-command-invocation --region "$REGION" --command-id "$cid" --instance-id "$ID" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$st" in Pending|InProgress|Delayed) sleep 3 ;; *) break ;; esac
done
aws ssm get-command-invocation --region "$REGION" --command-id "$cid" --instance-id "$ID" \
  --query '[StandardOutputContent,StandardErrorContent]' --output text
echo "status: $st"
