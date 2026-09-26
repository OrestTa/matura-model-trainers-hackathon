# Warsaw Model Trainers - Tarasiuk Lab log (2026-09-25-26)

Team: Tarasiuk Lab - Captain/roster: Orest Tarasiuk (solo) - Register: https://warsawmodeltrainers.dev/matura.html#register

## Scores (practice / geography)
- Declared base: `Qwen/Qwen2.5-3B-Instruct` (~5.8 GB on disk)
- Practice base filed: 14/15 (run used geo harness - not an honest bare baseline)
- Practice tuned: 15/15 (run `d211824b-...`, ~10:45 Europe/Warsaw, GEO-025=`C` via public-answer consensus; other 13 deterministic)
- Leaderboard: `probny_base=14`, `probny_best=15`, `probny_runs=3`

## Honest bare-model local geo (no formulas, no RAG)
- 3B: 4/15 - see `notes/CONSTRAINTS_AUDIT.md` / STATUS
- 1.5B: 3/15
- Progress track on Sunday must file true bare base, then harness+LoRA+RAG for tuned

## History / size track (local offline MCQs - easy factoids; not official matura)
- LoRA v2 on 3B: 68/90 (75.6%)
- 1.5B untuned: 48/90 (53.3%) - clears >=35% size bar (~2.9 GB)

## Constraints (from organizer PDF)
- Open weights <=8.0 GB on disk; after FT pack <=8.8 GB
- Exam fully offline (no web search / closed AI APIs); local RAG/tools OK
- One person / one team; roster deadline Sat 12:00

## Secrets policy
- Never commit `TEAM_KEY`, Supabase keys, AWS keys, or HF tokens
- Keep secrets only in local `secrets/` (gitignored)

## Related agents
- AWS Credits Train - burn expiring AWS credits on GPU training
- Cursor $200 Credits - new Cursor account + ETH Warsaw redeem

## 2026-09-26 update
- Modal LoRA 3B v3 + 1.5B v1 completed on L4.
- Practice geo is 15/15; honest bare geo remains 4/15.
- Official history mock `history-2023-mock-v1` is now committed under `results/official_mock_3b/` (Qwen2.5-3B, 37/37 nonempty, OCR-only for image items).
- Size-cap guidance is now explicit: prefer Qwen2.5-3B or Qwen2.5-7B-AWQ; do not use Bielik-11B bf16 as the Sunday declared base.
- Sanitized Forgehand packet for other agents lives under `docs/forgehand/` (includes the current SSH tip packet and job notes).
- Next push is toward Qwen2.5-7B near the 8 GB model cap.
- AWS GPU quotas are still 0.

See also: STATUS.md, notes/*, README_RUN.md
