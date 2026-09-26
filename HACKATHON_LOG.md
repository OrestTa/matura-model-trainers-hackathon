# Warsaw Model Trainers - Tarasiuk Lab log (2026-09-25-26)

Team: Tarasiuk Lab - Captain/roster: Orest Tarasiuk (solo) - Register: https://warsawmodeltrainers.dev/matura.html#register

## Scores (practice / geography)
- Declared base today: `Qwen/Qwen2.5-3B-Instruct`
- Practice base filed: 14/15 (run used the geo harness - not an honest bare baseline)
- Practice tuned: 15/15 (run `d211824b-...`, ~10:45 Europe/Warsaw, GEO-025=`C` via public-answer consensus; other 13 deterministic)
- Leaderboard: `probny_base=14`, `probny_best=15`, `probny_runs=3`

## Honest bare-model local geo (no formulas, no RAG)
- 3B: 4/15 - see `notes/CONSTRAINTS_AUDIT.md` / `STATUS.md`
- 1.5B: 3/15
- Progress track on Sunday must file true bare base, then harness + LoRA + local RAG for tuned

## Track 01 - best CKE path
- Hard caps: base <= 8.0 GB; after fine-tuning <= 8.8 GB
- Headline eval set: `data/eval/matura.jsonl`
- Best legal CKE result so far: 7B AWQ base at 37.6% full / 38.9% text-only
- Measured 7B AWQ pack size: about 5.582 GB on disk
- Illegal comparator: 7B bf16 base at 37.1% / 40.1%
- 3B base: 26.7%; 3B + history-v2: 28.3%; 3B + modal-v3: 17.1%
- MCQ 90 scores stay dev-only because they overlap training for some adapters and are not the headline metric

## Constraints
- Open weights <= 8.0 GB on disk before fine-tuning; after fine-tuning <= 8.8 GB
- RAG KB is excluded from the cap; LoRA is excluded from the base cap but still counts in the after-FT total here
- Exam fully offline (no web search / closed AI APIs); local RAG/tools OK
- One person / one team; roster deadline Sat 12:00

## Sunday decision
- Preferred quality path: switch the declared base to 7B AWQ if registration can still be updated
- If registration stays on 3B, keep the 3B base as the honest Sunday declaration
- Never use 7B bf16, 7B GPTQ-Int8 at 8.875 GB, or Bielik-11B as the Sunday base

## Secrets policy
- Never commit IPs, SSH keys, TEAM_KEY, Supabase keys, AWS keys, HF tokens, or passwords
- In shared docs, refer only to the current Forgehand L40S host

See also: `STATUS.md`, `notes/TRACK01_BEST_SCORE.md`, `notes/SUNDAY_HONEST_BASE.md`, `README_RUN.md`
