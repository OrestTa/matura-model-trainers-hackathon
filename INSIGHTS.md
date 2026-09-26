# Tarasiuk Lab - live insights (trunk sync)

Updated: 2026-09-26 ~12:35 Europe/Warsaw

## Standing preference
- Commit important findings/results directly to `main` (no feature branches / no waiting on PRs) so the cloud Code project sees them immediately.
- Never commit secrets (TEAM_KEY, AWS keys, Modal tokens, supabase).

## Team / ranking
- Team: Tarasiuk Lab - practice best 15/15 - filed base 14/15 (harness-inflated, not honest bare).
- Honest bare geo local: 3B 4/15, 1.5B 3/15.
- Practice exam subject was geography (`probny`); history LoRA is offline prep.

## Models
- Declared base: Qwen2.5-3B-Instruct (~5.8-6.2 GB).
- Modal LoRA done: 3B v3 + 1.5B v1 on L4 (adapters under `runs/lora/modal-*`).
- Next: push toward <=8 GB cap with Qwen2.5-7B (GPTQ-Int8 ~8.88 GB if organizers allow ~8.9; else AWQ ~5.58 GB). Full 7B bf16 ~15 GB illegal for exam disk.

## Compute
- Modal workspace `orestta`: idle except completed LoRA apps; billed $0 this month so far.
- AWS Activate a16z ~$98k left; GPU On-Demand quotas still 0 (small G/VT 32 ask in flight).

## Sunday
- Final unlocks ~11:00 Warsaw. File true bare base then harness+LoRA+local RAG.
