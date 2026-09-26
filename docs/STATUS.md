# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| router-ablation | bielik-11b MODES=raw,routed,rag on headline eval (needs data/kb from build_kb.py); measures template+voting+RAG gains | next free GPU | queued: wants a GPU after labqoat-baselines | 2026-09-26 11:13 | 2026-09-26 11:13 | work/out/router-ablation | Question router thread |
| grok-lora-7b-fh-v2 | Grok bot: harness/forgehand_lora_train.py --model-size 7b, 80 rows | Forgehand session 01a0dd4b, tmux train | running (step 940/2000 at 11:06) | 2026-09-26 11:06 | 2026-09-26 11:06 | /workspace/hackathon/runs/lora/forgehand-lora-7b-fh-v2 | Grok bot |
| train-bielik-l40s | train.sh TRAIN_MODELS=bielik-11b, current main | Forgehand session 01a0dd4b | queued: starts when labqoat-baselines finishes | 2026-09-26 10:58 | 2026-09-26 11:08 | /workspace/work/out/train-bielik-l40s | Modal compute setup thread |
| labqoat-baselines | baselines on all 16 papers (matura_all.jsonl, 573 items), no judge | Forgehand session 01a0dd4b | queued on the GPU behind the Grok LoRA | 2026-09-26 10:58 | 2026-09-26 11:10 | /workspace/work/out/labqoat-baselines | Modal compute setup thread |
