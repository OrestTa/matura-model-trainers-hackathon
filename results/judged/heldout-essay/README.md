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
