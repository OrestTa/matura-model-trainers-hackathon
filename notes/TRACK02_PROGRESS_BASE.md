# Track 02 - progress base

Updated: 2026-09-26 Europe/Warsaw

## First VALID `progress-base-raw` note

- Model: `speakleash/Bielik-11B-v2` NF4 ship pack, about 6.66 GB on disk and within the 8.0 GB base cap; not the v3 Instruct-AWQ pack.
- Job: `progress-base-raw` baselines on the `matura.jsonl` holdout.
- Raw result: **25.5%** (**26.0/102 pts**), with **91/154** items scored, **0** errors, wall about **426 s**.
- Diagnostics: `pct_text_only` **39.2**; `decision_acc` **42.3**.
- Operator path on the VM: `/workspace/work/out/progress-base-raw/baselines/bielik-11b-base/raw/summary.json`.
- `routed` is still running.
- Ignore prior contaminated Bielik-11B-v3 scores for Track 02.
- Official mock gauge remains `history-2023-mock-v1` only; earlier E2E `Qwen2.5-3B` judge result was **15/60**.
