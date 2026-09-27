# Bielik answers on the January 2026 mock (probny-2026-01, 38 items), L40S, 27.09 09:00–09:10 CEST

Prompt as Codex's infer.py: its system prompt, temperature 0, seed 42, 500 tokens (1600 essay), thinking off.
Picture items get tesseract `pol` OCR text first (except `bare`). One LoRA per route (closed/open x with/without pictures, essay), picked per item (routes.json).

| arm | model | adapters | blank | wall | essay words |
|---|---|---|---|---|---|
| bare | Bielik 1.5B Q8_0 | none, no OCR | 0 | 49 s | 287 |
| base | Bielik 1.5B Q8_0 | none, OCR | 0 | 11 s | 176 |
| ours | Bielik 1.5B Q8_0 | b15-v1 (ours, 149 real rows, 1 epoch; mock + May 2023–2026 left out) | 0 | 20 s | 274 |
| cleanv3 | Bielik 1.5B Q8_0 | Codex clean-v3-full-epoch | 0 | – | 243 |
| allpapers | Bielik 1.5B Q8_0 | Codex all-papers-full-epoch (trained incl. the mock) | 0 | 90 s | 681 |
| b45 | Bielik 4.5B Q8_0 | none, OCR | 0 | 58 s | 250 |

Essays under 300 words score 0 under the CKE rule. Not graded yet. Training data is not committed.
scripts/: train_b15.py = Codex's train_bielik_real_native.py with only the reserved-year guard (now our 5 held-out papers) and the GPU cap changed.

## Essay length guard (answers-guard.json, 09:09 CEST)
Only the essay item (27) re-run: 2400 tokens, then up to 3 "continue" turns until ≥350 words (scripts/b15guard.py). All other answers unchanged. check_submission OK for all three.

| arm | essay words by round |
|---|---|
| base | 237 → 466 |
| ours | 1078 (one turn) |
| allpapers | 206 → 473 |
