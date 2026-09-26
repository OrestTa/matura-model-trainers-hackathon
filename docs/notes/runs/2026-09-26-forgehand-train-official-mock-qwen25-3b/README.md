# 2026-09-26 Forgehand train + official mock (Qwen2.5-3B)

Sanitized notes and artifacts copied into the repo so later agents can reuse the
same context without relying on ephemeral uploads.

## Standing eval rule

- Only the organiser-format official mock, `history-2023-mock-v1`, gauges
  submission-quality model behaviour.
- CKE `data/eval/matura.jsonl`, the 90-question history MCQ set, and other
  local/proxy evals are still useful for development, but they are **not** the
  official quality signal.
- `37/37 nonempty` in `answers.summary.json` means every answer slot was filled.
  It is **not** an official grade.

## Key takeaways

- The mock package is `history-2023-mock-v1` (37 items / 60 points) and uses
  the organiser JSON format plus 19 PNGs.
- The bundled `run_official_mock.py` run used local
  `Qwen/Qwen2.5-3B-Instruct` through Hugging Face Transformers with OCR text for
  image tasks; no pixels were fed to the model.
- The run produced `37/37` nonempty answers and regenerated the essay to 301
  words, which satisfies the format constraint but does **not** reveal the
  organiser's later LLM-graded score.
- Hard caps during this period remained base <= 8.0 GB on disk and base +
  adapters <= 8.8 GB after fine-tuning.

## Files

- `INSIGHTS_2026-09-26.md` - condensed Forgehand train insights, sanitized
- `OFFICIAL_EVAL.md` - organiser-format mock notes
- `SIZE_CAP_8GB.md` - hard-cap note for legal Sunday packs
- `JOBS.md` - job-board snapshot around the same window
- `FORGEHAND.md` - Forgehand operational notes, sanitized
- `run_official_mock.py` - the HF runner used for this mock attempt
- `answers.json` - organiser-format answers payload from that run
- `answers.summary.json` - run summary (`37/37` nonempty, OCR-only images)
- `answers.runlog.jsonl` - per-item trace from the run
