# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| --help |  |  |  | 2026-09-26 11:00 | 2026-09-26 11:00 |  |  |
| train-bielik-l40s | train.sh, TRAIN_MODELS=bielik-11b | Labqoat L40S VM, tmux train | running (per FINDINGS 13:00 CEST, owner to confirm) | 2026-09-26 10:58 | 2026-09-26 10:58 | ~/matura-model-trainers-hackathon/work/out | GPU VM thread |
| labqoat-baselines | baselines, all models in configs/models.yaml | Labqoat Forgehand workspace 01a0dd4b | waiting: Forgehand sign-in from Orest | 2026-09-26 10:58 | 2026-09-26 10:58 | /workspace/work/out/<name> | Modal compute setup thread |
