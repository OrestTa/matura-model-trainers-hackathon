# ★ Best-performance candidate (Tarasiuk Lab, "Best exam score")

**This is our best-performance candidate for the final exam** (Orest, 27.09.2026 08:07 CEST).
If the SDALL run beats it later, Orest decides whether to swap; until then this is the candidate.

| | |
|---|---|
| Model | Gemma 4 12B QAT q4_0 GGUF + mmproj, **no fine-tune** |
| Upstream | `google/gemma-4-12B-it-qat-q4_0-gguf` @ `29d097773436b69ff9feafd636ab4cf873786537` (Apache-2.0) |
| Our copy | https://huggingface.co/orestta/matura-gemma4-12b-best-score (private; uploaded 27.09 08:11 CEST, sha256 on HF match the table below) |
| Size | 7,150,994,912 bytes = **7.15 GB** (limit 8.0 GB base / 8.8 GB all models summed) |
| Harness | this repo at commit `007fb17` or later main (adds, after c87a484: the essay's printed plan is stripped from the answer, and the essay settings are defaults in configs/subtypes.yaml; tag `best-score-candidate` to be pushed by Orest on the final commit); `run_exam.py --model gemma4-12b-exam --mode subtype` |
| Held-out May 2023–2026 | **163/240 (67.9%)**: 38 / 44 / 39 / 42 |
| Practice paper Jan 2026 | **43/60** dress rehearsal (964c246), **38/60** final end-to-end run on fresh main 38725cd (5b9f270); plain base 37. The 5-point gap between the two runs of the same setup is run-to-run noise (essay 11 vs 9) |

| File | sha256 |
|---|---|
| `gemma-4-12b-it-qat-q4_0.gguf` (6,975,879,296 B) | `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` |
| `mmproj-gemma-4-12b-it-qat-q4_0.gguf` (175,115,616 B) | `cb018338a7538a9814d994bfe54644c71eb7ed54e31eae2f721e45fd3c260da7` |

Check the files on the GPU box: `sha256sum gemma-4-12b-it-qat-q4_0.gguf mmproj-gemma-4-12b-it-qat-q4_0.gguf`.

## Settings

- Open questions: the exam prompt as given, thinking on, 2k thinking tokens.
- Closed questions: 5 samples, 3-of-5 vote.
- Essay: plan first, then 3 drafts with 16k thinking; the best draft of 300+ words is kept (target 350–550 words).
- A blank answer is asked once more with thinking off (`THINK_FALLBACK=1`).
- No LoRA, no OCR, no retrieval (`ADAPTERS=/nonexistent`).

## Stage command

```bash
export THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b-exam &
python scripts/run_exam.py <exam package dir> --model gemma4-12b-exam --mode subtype --concurrency 8 -o answers.json
python scripts/check_submission.py answers.json <exam package dir>
```

Full detail: docs/EXAM_DAY_BEST_SCORE.md (on-stage runbook), docs/FINAL_RESULTS.md (all scores,
incl. every rejected fine-tune), docs/SUBMISSION.md (form fields). Model card for the HF copy:
docs/hf/matura-gemma4-12b-best-score.README.md.
