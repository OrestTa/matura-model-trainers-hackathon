# Final results: deck vs base vs optimised (26 Sep 2026)

Model: Gemma 4 12B QAT q4_0 GGUF + mmproj, **7.16 GB** as shipped (the deck ran bf16, 23.92 GB).
Setting for every run below: thinking on at 2k (`gemma4-12b-think`), raw exam prompt, pictures sent
to the model, `THINK_FALLBACK=1`. Primary grade: Claude against the CKE klucz. Second opinion: Sol.
Held-out papers only (May 2023–2026), never used in training.

## May 2023, the deck's five categories

| Category | Deck (bf16 24 GB) | Deck's answers, our judge | Base (ours, 7.16 GB) | Optimised |
|---|---|---|---|---|
| Closed /11 | 10 | 10 (+0) | 8 (-2) | _pending_ |
| Open /34 | 24 | 24 (+0) | 24 (+0) | _pending_ |
| Essay /15 | 12 | 8 (-4) | 9 (-3) | _pending_ |
| Text-only /28 | 24 | 20 (-4) | 21 (-3) | _pending_ |
| Text + table /30 | 26 | 22 (-4) | 23 (-3) | _pending_ |
| **Total /60** | **46** | **42 (-4)** | **41 (-5)** | _pending_ |

Our judge is 4 points stricter than the deck's on the deck's own answers, all on the essay (Sol: 45).

## Four held-out papers

| Run | 2023 | 2024 | 2025 | 2026 | Total /240 | Picture /101 | Text /79 | Essay /60 | Sol |
|---|---|---|---|---|---|---|---|---|---|
| Base (g4vr) | 41 | 43 | 41 | 44 | **169** | 72 | 66 | 31 | 171 |
| Optimised | _pending_ | | | | | | | | |

Ship bar: a fine-tune ships only at base + 3 (172/240) or better at the same setting.
Source: `results/judged/TABLE.md`, `scripts/deck_compare.py`.
