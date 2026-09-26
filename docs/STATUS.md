# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| train-bielik-l40s | train.sh, TRAIN_MODELS=bielik-11b | Labqoat/Forgehand L40S VM 34.224.61.209, tmux train, log work/train.log | running since ~10:55 UTC (started from Orest's Mac); not verifiable from cloud: SSH blocked, needs FORGEHAND_TOKEN | 2026-09-26 10:58 | 2026-09-26 11:01 | ~/matura-model-trainers-hackathon/work/out | GPU VM thread |
| labqoat-baselines | baselines, all models, no judge (1 GPU) | Forgehand session 01a0dd4b | queued on the GPU: waits for the Grok 7B LoRA to free the card | 2026-09-26 10:58 | 2026-09-26 11:04 | /workspace/work/out/labqoat-baselines | Modal compute setup thread |
