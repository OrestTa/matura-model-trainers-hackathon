# AWS training infrastructure

Scripts for running training on AWS GPUs, paid for by AWS Activate credits only.

Credentials come from `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_DEFAULT_REGION`
(environment settings, never committed), or from 1Password: set `OP_SERVICE_ACCOUNT_TOKEN` and
`AWS_OP_ITEM` (for example `op://Hackathon/AWS root key`) and install the `op` CLI. Needs the AWS CLI (`pip install awscli`).

| Script | What it does |
| --- | --- |
| `setup.sh` | One time: requests GPU quotas in us-east-1/us-east-2/us-west-2, creates the S3 bucket, an SSM instance role, an egress-only security group, and two budgets (gross spend cap, and cost after credits). Set `BUDGET_EMAIL` for alarm emails. |
| `launch.sh <type> [name] [region]` | Starts a Deep Learning AMI instance that terminates itself at `DEADLINE_UTC` (Sun 27 Sep 10:30 CEST). Refuses if anything is being billed past the credits, or if projected spend would pass `BUDGET_USD` ($95k). `/opt/work/out` syncs to S3 every 10 minutes. |
| `run.sh <id> <command>` | Runs a command on an instance through SSM, no SSH needed. |
| `status.sh` | Running instances, burn rate, projected spend, and cost before and after credits. |
| `teardown.sh [--all]` | Terminates every project instance; `--all` also deletes the bucket. |

All resources carry the tag `Project=matura-hackathon`.
