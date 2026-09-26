# Findings

Shared log for every bot and person on this repo. Newest first, dated, one short entry per finding.
Pull before you add, commit straight to main.

## 2026-09-26 · Eval set from real CKE papers (eval-set thread)

- `python scripts/fetch_matura.py` builds `data/eval/matura.jsonl` from the May 2023–2026 historia
  (rozszerzony) papers and official keys: 154 items, 4 × 60 = 240 points. Every paper parses to exactly
  60 points, and every official key scores full marks against `matura_router/scoring.py`.
- **85 of 154 items need a picture** (map, photo, poster, plan, stamp) that a text model only sees as
  `[ilustracja – niedostępna w wersji tekstowej]`. Flag: `needs_image`; `--text-only` drops them.
  A text-only model has a hard ceiling well below 100% on the full paper.
- **The exam is mostly source analysis.** Gold types: source_analysis 109, short_open 13, true_false 12,
  closed_choice 12, matching 4, essay 4 (15 pts each, 25% of the paper), **chronology 0**. Formuła 2023
  papers have no ordering tasks, so a chronology adapter buys nothing on this exam.
- **52 items are "Rozstrzygnij … uzasadnij"** (verdict + justification, 1 pt only if both are right).
  This is the single most common task shape and may deserve its own prompt/adapter. The bare expected
  verdict is in the `decision` field.
- Rule classifier vs gold types: all closed/essay types routed correctly; 13 of 109 source_analysis
  items go elsewhere (5 general, 5 short_open, 2 closed_choice, 1 chronology).
- ~60 items are auto-scorable (closed keys + `gold_keywords`); the rest need the judge.
- Scorer gap: `scoring._pairs` only reads "1 – B". Letter-keyed matching keys ("Fragment A – Karol IX",
  "A – 3") are therefore emitted as `gold_keywords` instead of `gold`.
- Older formuła 2015 papers (2015–2022) are not included; they have more closed/chronology items and
  could serve as extra training data, not as a faithful eval.
