# Essay grid: Claude judge (blind)

12 dev essays (f15-2015..2024, pokaz-2022-03, probny-2026-01) × 4 arms from results/subtype/essay-grid/essay/{base,plan,guard,plan_guard}.
Graded by Claude Opus against the full official CKE essay criteria of each paper (f15 = max 12, formula 2023 = max 15).
Arms were shuffled and labelled A–D per topic, so graders did not know which arm wrote which essay; one grader saw all four arms of a topic.

| Arm | Total /150 | Formula 2023 only /30 |
|---|---|---|
| base | 63 | 16 |
| plan | 68 | 17 |
| guard | 56 | 13 |
| plan_guard | 67 | 14 |

Files: claude_scores.json (label key, grades, totals), breakdown.json (per-criterion notes).

## Batch 2: grid arms regraded blind together with essay-bo3 (6 arms × 12 essays, 6 graders)

bo3raw = results/subtype/essay-bo3/raw/raw, bo3plan = results/subtype/essay-bo3/essay/plan (16k, ESSAY_BEST_OF=3, min 350, target 550 words).

| Arm | Batch 1 /150 | Batch 2 /150 | Formula 2023 only /30 (batch 2) |
|---|---|---|---|
| base | 63 | 68 | 16 |
| plan | 68 | 73 | 19 |
| guard | 56 | 66 | 16 |
| plan_guard | 67 | 75 | 19 |
| bo3raw | - | 75 | 16 |
| bo3plan | - | 77 | 19 |

The same essays scored 5–10 higher in batch 2, so compare arms only within a batch. Base is lowest in both batches.
