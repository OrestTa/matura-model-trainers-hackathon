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

**Repetition check (sentences / unique sentences):** base 28/18, ours 106/16 (the essay loops on the same sentences), allpapers 30/19. The word counts clear 300, but a grader will likely mark the repeated text down; the "ours" essay is mostly one loop.

## Our harness (scripts/run_exam.py at cf84ec6, 09:10–09:23 CEST)
Bielik 4.5B Q8_0 (key `bielik-4.5b-q8`, OCR on), llama-server on :8093, ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550, concurrency 3 each (both ran at once).

| arm | mode | blank | wall | essay words |
|---|---|---|---|---|
| b45-harness-adapters | adapters (default, no adapters loaded) | 0 | 512 s | 490 |
| b45-harness-subtype | subtype (ESSAY_BEST_OF=3 from subtypes.yaml) | 0 | 742 s | 1711 |

gemma-raw: Gemma 4 12B QAT, `--mode raw`, key gemma4-12b-exam, on the warm exam server (007fb17 checkout), 0 blank, 322 s, essay 339 words.

## Bielik 1.5B through our harness (improvement track, 09:30–09:33 CEST)
Harness = main cf84ec6 + keys from 795bf2f (bielik-1.5b-q8, bielik-1.5b-q8-noocr), no adapters. One llama-server, three arms at once (concurrency 3 each).

| arm | key | mode | blank | wall | essay words (sentences / unique) |
|---|---|---|---|---|---|
| h-routed-ocr (A) | bielik-1.5b-q8 | routed | 0 | 178 s | 254 (16/16), under 300 |
| h-routed-noocr (B) | bielik-1.5b-q8-noocr | routed | 0 | 100 s | 314 (21/21) |
| h-subtype-ocr (C) | bielik-1.5b-q8 | subtype | 0 | 153 s | 605 (52/43) |

D (b15-v1 adapters through the router) skipped. ESSAY_MIN_WORDS only acts in subtype mode, so A's essay stayed at 254 words.

Essay-only experiments (scripts/essay_parts.py; bare arm's answers with item 27 replaced), temperature 0.3, repeat_penalty 1.15, DRY 0.8/1.75/2:
| arm | essay words (sentences / unique) |
|---|---|
| essay-dry (E1, one call, 2400 tokens) | 243 (14/14), under 300 |
| essay-parts (E2, intro + 4 aspect paragraphs + conclusion) | 995 (57/47) |

On-stage commands for A (run from the repo root, offline):
```bash
export LD_LIBRARY_PATH=$PWD/work/llama.cpp/build/bin
work/llama.cpp/build/bin/llama-server -m <Bielik-1.5B-v3.0-Instruct-Q8_0.gguf> --host 127.0.0.1 --port 8000 \
  -ngl 999 -c 32768 --parallel 8 --jinja --cache-ram 0 &      # configs/routes.yaml backend.base_url = http://localhost:8000/v1
ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 python scripts/run_exam.py <package> --model bielik-1.5b-q8 --mode routed -o answers.json
python scripts/check_submission.py answers.json <package>
```
(On the L40S the server ran on :8091 with routes.yaml pointed there, because :8000 holds the best-score exam server.)
