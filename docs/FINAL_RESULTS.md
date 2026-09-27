# Final results: deck vs base vs optimised (26 Sep 2026)

Model: Gemma 4 12B QAT q4_0 GGUF + mmproj, **7.16 GB** as shipped (the deck ran bf16, 23.92 GB).
Setting for every run below: thinking on at 2k (`gemma4-12b-think`), raw exam prompt, pictures sent
to the model (fine-tune evals also with `THINK_FALLBACK=1`). Primary grade: Claude against the CKE klucz. Second opinion: Sol.
Held-out papers only (May 2023–2026), never used in training.

## May 2023, the deck's five categories

| Category | Deck (bf16 24 GB) | Deck's answers, our judge | Base (ours, 7.16 GB) | Shipped: stage path (27.09) |
|---|---|---|---|---|
| Closed /11 | 10 | 10 (+0) | 8 (-2) | 7 (-3) |
| Open /34 | 24 | 24 (+0) | 23 (-1) | 23 (-1) |
| Essay /15 | 12 | 11 (-1) | 10 (-2) | 8 (-4) |
| Text-only /28 | 24 | 23 (-1) | 22 (-2) | 19 (-5) |
| Text + table /30 | 26 | 25 (-1) | 24 (-2) | 21 (-5) |
| **Total /60** | **46** | **45 (-1)** | **41 (-5)** | **38 (-8)** |

Grading (7e6fe48): pictures viewed by the judge, full CKE essay criteria. On the deck's own answers our judge gives 45/60
vs the deck's 46, so the judges agree; the base gap to the deck is the model (4-bit QAT, 2k thinking), mostly closed + essay.

May 2023 is one paper: over all four held-out papers the stage path equals the base (163 vs 163, next table); per-paper
differences of ±3 are run-to-run noise (the same raw setting scored 163 and 159.5 on two runs).

## Four held-out papers

| Run | 2023 | 2024 | 2025 | 2026 | Total /240 | Picture /101 | Text /79 | Essay /60 | Sol |
|---|---|---|---|---|---|---|---|---|---|
| Base (g4vr) | 41 | 42 | 39 | 41 | **163** | 67 | 66 | 30 | Sol 101 vs Claude 96 of 139 (text + essays) |
| Shipped = base (no fine-tune beat it) | 41 | 42 | 39 | 41 | **163** | 67 | 66 | 30 | |
| **Shipped from 27.09 03:10: stage path (essay plan + best of 3), measured** | 38 | 44 | 39 | 42 | **163** | 66 | 68 | 29 | full stage run, graded paper by paper (results/judged/matura-judge-claude-stage-heldout); the blind side-by-side essay batch gave 71 vs 56/120, the paper-by-paper grade shows no gain |
| Harness `--mode subtype` (no LoRA) | 38 | 45 | 40 | pending | 123 on 3 papers (base 122) | | | 23/45 (3 papers) | |
| A1 LoRA (1 epoch) | 24 | – | – | – | – | | | 0/15 (2023) | |
| B4m2 LoRA | 23 | – | – | – | – | | | 0/15 (2023) | |
| Hm2 LoRA | 28 | 30 | – | – | – | | | 0/15 (2023) | |
| Gm3 LoRA (essay-weighted) | 20 | 36 | – | – | – | | | 0/15 (2023) | |
| S4m2 LoRA | 25 | 31 | – | – | – | | | 2/15 (2023) | |
| SD1 LoRA (self-distilled, real past papers only) | 36 | 45 | 33 | 41 | **155** (base 163); probny 36 vs 37 | 66 | 65 | 24 (2025 essay 298 words = 0) | dd87719, 232bda2, eb610f2, 89c8ac6 |
| A01 LoRA (0.1 epoch) | 28 | 34 | 34 | 35 | **131** (base 163) | | | 7/60 | |

Ship bar: a fine-tune ships only at base + 3 (166/240; 86/120 on May 2023+2024) or better at the same setting.
Source: `results/judged/TABLE.md`, `scripts/deck_compare.py`.

**Outcome:** every LoRA fine-tuned on our synthetic + past-paper data scored below the base, mainly
because it broke the essay (too short, looping or factually wrong) and never gained on short items.
We ship the base model (7.16 GB) with thinking and the blank-answer fallback, plus (from 27.09 03:10) the essay
setup "plan first, then best of 3 drafts", which beat the base essay on practice essays (+9 to +13/150 in 4 blind
batches) and then on the 4 held-out essays (71 vs 56 of 120 over 2 runs); see
docs/EXAM_DAY_BEST_SCORE.md for the frozen on-stage commands.

**Harness: no clear gain.** The per-subtype harness (configs/subtypes.yaml, picks made on dev papers) is level
with raw on the held-out papers: 123 vs 122 on full papers May 2023–2025 (c4a87e5), and 77/138 vs 79.5/134 on
the half-answered held-out sweep (results/subtype/heldout-hog/REPORT.md, dab51bc). The dev pick for open
picture questions (OCR notes next to the image) scored −6.5 pts per 100 vs base on 26 paired held-out items,
so it is out. The essay length guard exists only in subtype mode and is not shipped. We ship raw + fallback.

## Essays: plan + best of 3 (shipped, Orest 27.09 07:43 "Keep the essay")

| Check | Base essays | Plan + best of 3 | Source |
|---|---|---|---|
| 12 practice essays, 5 blind batches /150 | 63, 68, 61, 58, 63 | 77 (bo3plan batch 2), 69, 70, 69 | results/judged/essay-grid |
| 4 held-out essays × 2 runs, blind side-by-side /120 | 56 | 71 | results/judged/heldout-essay |
| Full stage run, essays blind side-by-side /60 | 35 | 40 (ahead on all 4 papers) | 70e8f2f |
| Full stage run, essays graded paper by paper /60 | 30 | 29 | results/judged/matura-judge-claude-stage-heldout |
| Practice paper probny-2026-01 (full stage run) /60 total | 37 | 43 (essay 11 vs 6–8) | 7e23140 |

Side by side the new essays win every time; graded one paper at a time the difference disappears, so the honest
claim is "same total as base on held-out (163/240), essays about +5/60 better side by side". It also prevents the
300-word zero: three plain-model essays tonight came out at 276, 297 and 298 words.

## Other levers tested overnight (none shipped)

| Lever | Result |
|---|---|
| Best of 3 for open answers (OPEN_BEST_OF=3) | 49 practice non-essay items: 43 vs raw 42 (noise) |
| Describe the picture before answering (PICTURE_DESCRIBE=1) | 43 vs 42 (noise); with best-of-3: 44 |
| Essay retrieval from era fact sheets + Wikipedia (ragplan) | dev 70–74/150; held-out 66/120 vs bo3plan 71 |
| Retrieval + best of 3 (ragbo3plan) | dev 72 vs bo3plan 69, 5 wins / 5 losses |
| Essay best of 5 instead of 3 (bo5plan) | dev 71 vs bo3plan 69/150 (3 wins, 2 losses, 7 ties), noise |
| Thinking 4k vs 2k | 49 vs 50 on 51 practice items |
| SD1 self-distilled LoRA (real past papers only) | 155/240 vs base 163 |
