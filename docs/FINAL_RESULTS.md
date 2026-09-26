# Final results: deck vs base vs optimised (26 Sep 2026)

Model: Gemma 4 12B QAT q4_0 GGUF + mmproj, **7.16 GB** as shipped (the deck ran bf16, 23.92 GB).
Setting for every run below: thinking on at 2k (`gemma4-12b-think`), raw exam prompt, pictures sent
to the model, `THINK_FALLBACK=1`. Primary grade: Claude against the CKE klucz. Second opinion: Sol.
Held-out papers only (May 2023–2026), never used in training.

## May 2023, the deck's five categories

| Category | Deck (bf16 24 GB) | Deck's answers, our judge | Base (ours, 7.16 GB) | Optimised |
|---|---|---|---|---|
| Closed /11 | 10 | 10 (+0) | 8 (-2) | _pending_ |
| Open /34 | 24 | 24 (+0) | 23 (-1) | _pending_ |
| Essay /15 | 12 | 11 (-1) | 10 (-2) | _pending_ |
| Text-only /28 | 24 | 23 (-1) | 22 (-2) | _pending_ |
| Text + table /30 | 26 | 25 (-1) | 24 (-2) | _pending_ |
| **Total /60** | **46** | **45 (-1)** | **41 (-5)** | _pending_ |

Grading (7e6fe48): pictures viewed by the judge, full CKE essay criteria. On the deck's own answers our judge gives 45/60
vs the deck's 46, so the judges agree; the base gap to the deck is the model (4-bit QAT, 2k thinking), mostly closed + essay.

## Four held-out papers

| Run | 2023 | 2024 | 2025 | 2026 | Total /240 | Picture /101 | Text /79 | Essay /60 | Sol |
|---|---|---|---|---|---|---|---|---|---|
| Base (g4vr) | 41 | 42 | 39 | 41 | **163** | 67 | 66 | 30 | Sol 101 vs Claude 96 of 139 (text + essays) |
| Optimised | _pending_ | | | | | | | | |

Ship bar: a fine-tune ships only at base + 3 (166/240; 86/120 on May 2023+2024) or better at the same setting.
Source: `results/judged/TABLE.md`, `scripts/deck_compare.py`.
