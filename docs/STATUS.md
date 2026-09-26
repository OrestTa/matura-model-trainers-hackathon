# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| --help |  |  |  | 2026-09-26 11:00 | 2026-09-26 11:00 |  |  |
| train-bielik-l40s | train.sh, TRAIN_MODELS=bielik-11b | Labqoat/Forgehand L40S VM 34.224.61.209, tmux train, log work/train.log | running since ~10:55 UTC (started from Orest's Mac); not verifiable from cloud: SSH blocked, needs FORGEHAND_TOKEN | 2026-09-26 10:58 | 2026-09-26 11:01 | ~/matura-model-trainers-hackathon/work/out | GPU VM thread |
| labqoat-baselines | baselines, all models in configs/models.yaml | Labqoat Forgehand workspace 01a0dd4b | waiting: Forgehand sign-in from Orest | 2026-09-26 10:58 | 2026-09-26 10:58 | /workspace/work/out/<name> | Modal compute setup thread |
