# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| grok-lora-7b-fh-v2 | Grok bot: harness/forgehand_lora_train.py --model-size 7b, 80 rows | Forgehand session 01a0dd4b, tmux train | running (step 940/2000 at 11:06) | 2026-09-26 11:06 | 2026-09-26 11:06 | /workspace/hackathon/runs/lora/forgehand-lora-7b-fh-v2 | Grok bot |
| train-bielik-l40s | train.sh TRAIN_MODELS=bielik-11b, current main | Forgehand session 01a0dd4b | queued: starts when labqoat-baselines finishes | 2026-09-26 10:58 | 2026-09-26 11:08 | /workspace/work/out/train-bielik-l40s | Modal compute setup thread |
| labqoat-baselines | baselines, all models, no judge (1 GPU) | Forgehand session 01a0dd4b | queued on the GPU: waits for the Grok 7B LoRA to free the card | 2026-09-26 10:58 | 2026-09-26 11:04 | /workspace/work/out/labqoat-baselines | Modal compute setup thread |
