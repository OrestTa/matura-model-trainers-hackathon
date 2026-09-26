# Tarasiuk Lab - live insights (trunk sync)

Updated: 2026-09-26 ~15:35 Europe/Warsaw

## Request to the Grok bot: register GPU jobs (2026-09-26 13:50 CEST)

The L40S in Forgehand session 01a0dd4b is shared by several bots. Your tmux sessions `gpu_par` and `dl7b` (`hf_eval_matura.py`, ~22 GB) have no rows in `docs/STATUS.md`, so other jobs can't plan around them and may OOM.
- Before taking GPU memory: `python3 infra/jobs/gpu_admit.py <job-id> <need-gb>` (waits until the card has room).
- On start, state change and finish: `python infra/jobs/status.py <job-id> state=running where="Forgehand 01a0dd4b, tmux <name>" what="..." out=<dir> owner="Grok bot"`, then pull and push.
- Please add rows for `gpu_par` and `dl7b` now.

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
- Hard cap update: declared base **<=8.0 GB** on disk; after FT **<=8.8 GB**.
- Do **not** pursue Bielik-11B bf16 / full-11B DAPT for the Sunday declared base.
- Preferred paths now: Qwen2.5-3B-Instruct or Qwen2.5-7B-Instruct-AWQ (~5.582 GB). GPTQ-Int8 7B is demoted because 8.875 GB exceeds the base cap.

## Official history mock
- Qwen2.5-3B bare mock for `history-2023-mock-v1` is committed under `results/official_mock_3b/`.
- Final payload: `results/official_mock_3b/answers.json` (**37/37 nonempty**).
- Category split from `answers.summary.json`: text_open 10, text_closed 3, image_open 19, image_closed 4, essay 1.
- Harness is committed as `harness/run_official_mock.py`.

## Forgehand
- Sanitized access tip for the live session packet: `root@54.91.88.11` (key label `Orest-Noninteractive`).
- Longer sanitized notes are in `docs/forgehand/`.

## Compute
- Modal workspace `orestta`: idle except completed LoRA apps; billed $0 this month so far.
- AWS Activate a16z ~$98k left; GPU On-Demand quotas still 0 (small G/VT 32 ask in flight).

## Sunday
- Final unlocks ~11:00 Warsaw. File true bare base then harness+LoRA+local RAG.
