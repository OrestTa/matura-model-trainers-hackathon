# Final results: deck vs base vs optimised (26 Sep 2026)

Model: Gemma 4 12B QAT q4_0 GGUF + mmproj, **7.16 GB** as shipped (the deck ran bf16, 23.92 GB).
Setting for every run below: thinking on at 2k (`gemma4-12b-think`), raw exam prompt, pictures sent
to the model (fine-tune evals also with `THINK_FALLBACK=1`). Primary grade: Claude against the CKE klucz. Second opinion: Sol.
Held-out papers only (May 2023–2026), never used in training.

## May 2023, the deck's five categories

| Category | Deck (bf16 24 GB) | Deck's answers, our judge | Base (ours, 7.16 GB) | Shipped (frozen 22:30) |
|---|---|---|---|---|
| Closed /11 | 10 | 10 (+0) | 8 (-2) | = base |
| Open /34 | 24 | 24 (+0) | 23 (-1) | = base |
| Essay /15 | 12 | 11 (-1) | 10 (-2) | = base |
| Text-only /28 | 24 | 23 (-1) | 22 (-2) | = base |
| Text + table /30 | 26 | 25 (-1) | 24 (-2) | = base |
| **Total /60** | **46** | **45 (-1)** | **41 (-5)** | **= base** |

Grading (7e6fe48): pictures viewed by the judge, full CKE essay criteria. On the deck's own answers our judge gives 45/60
vs the deck's 46, so the judges agree; the base gap to the deck is the model (4-bit QAT, 2k thinking), mostly closed + essay.

## Four held-out papers

| Run | 2023 | 2024 | 2025 | 2026 | Total /240 | Picture /101 | Text /79 | Essay /60 | Sol |
|---|---|---|---|---|---|---|---|---|---|
| Base (g4vr) | 41 | 42 | 39 | 41 | **163** | 67 | 66 | 30 | Sol 101 vs Claude 96 of 139 (text + essays) |
| Shipped = base (no fine-tune beat it) | 41 | 42 | 39 | 41 | **163** | 67 | 66 | 30 | |
| **Shipped from 27.09 03:10: raw + essay "plan, best of 3"** | | | | | **~170 projected** | 67 | 66 | 30 + ~7.5 | held-out essays 71/120 vs base 56 over 2 runs (results/judged/heldout-essay) |
| Harness `--mode subtype` (no LoRA) | 38 | 45 | 40 | pending | 123 on 3 papers (base 122) | | | 23/45 (3 papers) | |
| A1 LoRA (1 epoch) | 24 | – | – | – | – | | | 0/15 (2023) | |
| B4m2 LoRA | 23 | – | – | – | – | | | 0/15 (2023) | |
| Hm2 LoRA | 28 | 30 | – | – | – | | | 0/15 (2023) | |
| Gm3 LoRA (essay-weighted) | 20 | 36 | – | – | – | | | 0/15 (2023) | |
| S4m2 LoRA | 25 | 31 | – | – | – | | | 2/15 (2023) | |
| SD1 LoRA (self-distilled, real past papers only; probny-2026-01 practice) | – | – | – | – | 36/60 on probny (base 37, stage 43) | | | 7/15 | dd87719 |
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
