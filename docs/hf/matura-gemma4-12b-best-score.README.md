---
license: apache-2.0
base_model: google/gemma-4-12B-it-qat-q4_0-gguf
language: [pl]
tags: [gguf, matura, history, polish, llama.cpp]
---

# Tarasiuk Lab: best-score candidate for the Warsaw Model Trainers history matura

**This is Tarasiuk Lab's best-performance candidate** for the "Best exam score" category.

It is an unmodified copy of `google/gemma-4-12B-it-qat-q4_0-gguf` (revision
`29d097773436b69ff9feafd636ab4cf873786537`), stored here so the exact files we run on stage stay
available. **No fine-tune.** Every LoRA we trained scored below this base model, the best being SD1 at 155/240 vs 163.

| File | Bytes | sha256 |
|---|---|---|
| `gemma-4-12b-it-qat-q4_0.gguf` | 6,975,879,296 | `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` |
| `mmproj-gemma-4-12b-it-qat-q4_0.gguf` | 175,115,616 | `cb018338a7538a9814d994bfe54644c71eb7ed54e31eae2f721e45fd3c260da7` |
| **Total** | **7,150,994,912 (7.15 GB)** | limit 8.0 GB base / 8.8 GB all models summed |

## Harness (github.com/OrestTa/matura-model-trainers-hackathon, commit `c87a484`)

llama.cpp `llama-server` with thinking on. `scripts/run_exam.py --model gemma4-12b-exam --mode subtype`:
- open questions: the exam prompt as given, 2k thinking tokens;
- closed questions: 5 samples, 3-of-5 vote;
- essay: plan first, then 3 drafts with 16k thinking, keeping the best of the drafts that reach 300 words (target 350–550 words);
- a blank answer is asked once more with thinking off (`THINK_FALLBACK=1`).

## Scores (Claude graded against the CKE key, pictures viewed)

| Paper | Score |
|---|---|
| Held-out May 2023 / 2024 / 2025 / 2026 | 38 / 44 / 39 / 42 = **163/240 (67.9%)**, same as the plain base model |
| Practice paper Jan 2026 (probny) | **43/60** (plain base model: 37) |

## Run

```bash
export THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b-exam &
python scripts/run_exam.py <exam package dir> --model gemma4-12b-exam --mode subtype --concurrency 8 -o answers.json
python scripts/check_submission.py answers.json <exam package dir>
```

Made during the Warsaw Model Trainers hackathon, Kolektyw3, 25–27.09.2026.
