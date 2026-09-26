# Job status

One row per job, updated on every state change with `scripts/job_status.py`.
Newest update first. Pull before reading; results and learnings go in
[FINDINGS.md](FINDINGS.md).

| Job | State | Where | Owner | Updated (UTC) | Notes |
|---|---|---|---|---|---|
| train-bielik-l40s | running | Labqoat L40S VM (tmux train) | GPU VM thread | 2026-09-26 10:58 | TRAIN_MODELS=bielik-11b infra/jobs/train.sh; state as logged in FINDINGS 13:00 CEST, owner to confirm |
