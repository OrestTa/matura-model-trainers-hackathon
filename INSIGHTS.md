# Tarasiuk Lab - live insights (trunk sync)

Updated: 2026-09-26 ~14:56 Europe/Warsaw

## Standing preference
- Commit important findings and score changes directly to `main` so every cloud/code session sees them immediately.
- Never commit secrets, IPs, SSH keys, TEAM_KEY values, or tokens.

## Team / ranking
- Team: Tarasiuk Lab - practice best 15/15 - filed base 14/15 was harness-inflated, not an honest bare base.
- Honest bare geo local: 3B 4/15, 1.5B 3/15.
- Practice exam subject was geography (`probny`); history LoRA work is offline prep for Sunday.

## Track 01 headline
- Hard caps: base <= 8.0 GB; after fine-tuning <= 8.8 GB.
- Headline eval is CKE `data/eval/matura.jsonl`, not the 90-question history MCQ train-overlap set.
- Best legal CKE pass so far: `Qwen/Qwen2.5-7B-Instruct-AWQ` at 37.6% full / 38.9% text-only.
- Measured 7B AWQ pack size is about 5.582 GB on disk, so it clears the Sunday base cap.
- The legal 7B AWQ result matches the illegal 7B bf16 base result (37.1%) within noise.
- Supporting comparisons: 3B base 26.7%, 3B + history-v2 28.3%, 3B + modal-v3 17.1%.

## Sunday decision
- Preferred quality path: declare 7B AWQ if registration can still be updated.
- If registration stays on the current 3B base, keep the 3B base as the honest Sunday declaration.
- Never use bf16-7B, GPTQ-Int8 at 8.875 GB, or Bielik-11B as the Sunday base.

## Compute
- Current shared GPU story: current Forgehand L40S plus completed Modal LoRA runs.
- AWQ follow-on work is only worth continuing if adapters stay legal under the 8.8 GB after-FT cap.
