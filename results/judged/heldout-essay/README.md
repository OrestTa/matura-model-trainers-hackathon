# Held-out essays: Claude judge (one blind batch)

Source: results/subtype/heldout-essay (a3c32a6). 4 held-out essays (May 2023, 2024, 2025, 2026; max 15 each) × 4 setups × 2 runs = 32 essays.
Graded by Claude Opus with the full official CKE essay criteria. Runs were shuffled and labelled A–H per paper, so graders did not know the setup; one grader saw all 8 runs of a paper.

| Setup | Run 1 /60 | Run 2 /60 | Both runs /120 | vs base |
|---|---|---|---|---|
| base (raw) | 26 | 30 | 56 | - |
| bo3plan (plan + best of 3, min 350, target 550 words) | 35 | 36 | 71 | +15 |
| ragplan (fact sheets + offline Wikipedia + plan) | 36 | 30 | 66 | +10 |
| bo3plan without length guard | 33 | 30 | 63 | +7 |

Per paper (run 1, run 2):

| Paper | base | bo3plan | ragplan | no guard |
|---|---|---|---|---|
| 2023 | 6, 9 | 11, 12 | 13, 9 | 9, 9 |
| 2024 | 9, 9 | 7, 9 | 9, 9 | 9, 9 |
| 2025 | 4, 4 | 5, 8 | 5, 4 | 8, 3 |
| 2026 | 7, 8 | 12, 7 | 9, 8 | 7, 9 |

bo3plan was chosen on practice essays first (essay-grid batches 2–4), so this held-out batch confirms it; it was not tuned here.

## Stage essays vs base essays, blind side by side (one grader, 4 essays per paper)

Stage = results/rehearsal/stage-heldout (964c246, essay bo3plan); frozen = results/gemma4/gemma4-vision/raw (the 163 base); base-r1 and bo3plan-r1 from above.

| Paper | Stage | Frozen base | base-r1 | bo3plan-r1 |
|---|---|---|---|---|
| 2023 | 11 | 10 | 7 | 10 |
| 2024 | 13 | 12 | 11 | 7 |
| 2025 | 7 | 5 | 7 | 7 |
| 2026 | 9 | 8 | 7 | 11 |
| Total /60 | 40 | 35 | 32 | 35 |

Graded side by side, the stage essays beat the frozen base essays on all 4 papers (+5/60). Graded one paper at a time inside full-paper grading they scored 29 vs 30. Absolute essay grades move by several points between grading passes; compare essays only within one side-by-side batch.
