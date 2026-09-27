# Per-subtype harness: what was built, tested and shipped

Orest's ask (26.09): a harness that answers each of 5 subtypes with its own setup: closed without images,
closed with images, open without images, open with images, essay. All scores are graded by Claude Opus
with the pictures viewed and the full CKE essay criteria. Items are selected on the practice papers
(pokaz-2022-03, probny-2026-01, older May papers); the held-out papers (May 2023 to 2026) were used only to confirm.

## Shipped (configs/subtypes.yaml, frozen at 964c246)

| subtype | setup | why |
|---|---|---|
| closed text / image | 5 answers, 3-of-5 vote (Orest 22:33) | same score as one answer on held-out (10/13, 15/25) |
| open text / image | `raw: true`: the exact `--mode raw` request | every variant was within ±2 of raw |
| essay | plan prompt, 16k thinking, 2600 tokens + env `ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550` | best on practice essays in 4 blind batches; raw essays can fall under 300 words and score 0 |

Stage command (docs/EXAM_DAY_BEST_SCORE.md):

    ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1 \
      python scripts/run_exam.py <package> --model gemma4-12b-exam --mode subtype --concurrency 8 -o answers.json

Blank answers are asked again with thinking off (THINK_FALLBACK=1). A run with more than 10% blank answers fails loudly.
Size: base 6.98 GB plus mmproj, 7.15 GB in total, under the 8.8 GB limit (serve_exam.sh sums every file it loads).

## Measured results

| run | score | where |
|---|---|---|
| Frozen base, raw 2k | 163/240 (41/42/39/41) | docs/FINAL_RESULTS.md |
| Stage path on held-out, graded paper by paper | 163/240 (38/44/39/42) | results/rehearsal/stage-heldout, results/judged/matura-judge-claude-stage-heldout |
| Held-out essays, blind, 2 runs each | plan + best of 3: 71/120; base: 56; RAG plan: 66; no word target: 63 | results/judged/heldout-essay |
| Held-out essays, blind side by side | stage 40/60, base 35 | 70e8f2f |
| Stage rehearsal, probny-2026-01 | 43/60; the 4 other runs on this paper each scored 37 | results/rehearsal/stage-probny |

On the full held-out run the essay gain did not show (29/60 vs 30 graded paper by paper). Grading noise is about ±3 per paper.
The essay setup ships because it scored higher in every blind essay batch, and because its 350-word minimum
removes the zero-score risk (raw essays came in at 276 and 297 words in practice runs).

May 2023 in the deck's categories (stage run vs Ania's deck, Gemma 4 12B bf16):

| category | deck | stage |
|---|---|---|
| closed /11 | 10 | 7 |
| open /34 | 24 | 23 |
| essay /15 | 12 | 8 |
| text-only /28 | 24 | 19 |
| text + table /30 | 26 | 21 |
| total /60 | 46 | 38 |

## What was tried and dropped

| technique | result |
|---|---|
| OCR notes next to the images (tesseract) | +5.6 on 14 practice items, then −6.5 on 26 held-out items; dropped (Orest 22:33: no OCR for a vision model) |
| thinking off | loses on every subtype |
| thinking above 2k (4k, 8k, 16k, 24k) | no gain; long budgets run out and leave blanks |
| essay length guard (continue under 350 words, no plan) | −7 and −2 of 150 on practice essays |
| RAG (offline Wikipedia 25,216 passages + 121 era fact sheets) for essays | +10 on held-out essays, less than plan + best of 3; together with best of 3, +3 over best of 3 (noise) |
| open questions, best of 3 | within ±2 of raw on 49 paired practice items |
| open questions, describe the picture first | within ±2 of raw |
| routed prompts on open picture items | +6 on a partial held-out sweep, not repeated on the full run; dropped for raw |

## Code

- `matura_router/subtypes.py`: subtype classification and the `Profile` per subtype (`raw`, `votes`, `think_tokens`, `prompt_suffix`, `min_words`, `rag`, `ocr`).
- `matura_router/router.py`: votes, essay best of N and length control (`ESSAY_*`), open best of N, picture describe, blank retry.
- `scripts/run_exam.py --mode subtype`: organiser-format package in, answers.json out.
- `scripts/subtype_sweep.py`, `configs/subtype_grid.yaml`: the ablation grid per subtype. `scripts/subtype_select.py` picks on practice papers; `scripts/subtype_report.py` reports held-out.
- `scripts/build_factsheet_kb.py`: fact sheets into `data/kb/factsheets.jsonl`; `RAG_PATH` merges knowledge bases.
- `infra/jobs/subtype_sweep.sh` (supervised server, SMOKE mode), `infra/jobs/rehearsal.sh` (the exact stage path).

## Lessons for the servers

- The prebuilt llama.cpp CUDA image aborts on H100 ("illegal instruction"). Build llama.cpp from source for sm90, and set GGML_CUDA_DISABLE_GRAPHS=1 and f16 KV.
- llama-server's host prompt cache defaults to 8 GiB per server and OOM-killed a 30 GB box. Use `--cache-ram 0`.
- Nebius job logs return about 100 lines per call. `scripts/subtype_collect.py` pages through time windows.
- Run a small smoke first (`SMOKE=N`), and never commit a run with more than 10% blank answers.
