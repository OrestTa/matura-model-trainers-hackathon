# Job ID + parallel infer/judge pipeline

Orest directive recorded 2026-09-26 16:39 CEST.

## Required job_id format

Every job must use a unique id:

`matura-<stage>-<model_slug>-<exam>-<YYYYMMDD-HHMM>-<rand4>`

- `stage` identifies the pipeline step, for example `infer`, `judge-grok`, `judge-claude`, or `judge-sol`.
- `model_slug` identifies the model used for that step.
- `exam` identifies the paper or evaluation target.
- `YYYYMMDD-HHMM` is the launch timestamp.
- `rand4` is a four-character family suffix shared across related jobs.

## Output paths

- Infer writes to `runs/<job_id>/answers.json`.
- Judge jobs must keep the same family suffix `<rand4>` as the related infer job.

## Parallel judging rule

For each completed `answers.json`:

- Claude and Grok grade in parallel.
- Sol grading is optional, but if used it should also run in parallel.
- Do not wait for judging to finish before starting the next infer job if VRAM is free.

## BOT_CHANNEL rules

- Always lead BOT_CHANNEL lines with `job_id=`.
- Claude still does not admit VM or GPU jobs.
