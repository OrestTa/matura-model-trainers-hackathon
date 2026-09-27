# Final exam submission: every field, ready to paste (27.09.2026)

Form: https://warsawmodeltrainers.dev/submissions.html?exam=final (read 07:55 CEST, incl. its
`submissions.mjs` and `submission-validation.mjs`). **Nothing has been submitted.**

## How the form works

1. **Get final exam questions.** Team code + repository link + a checkbox that the whole team has
   stopped work on every project. The server records the time. After this, the rules forbid any
   training, editing or improving of any project; only running the finished harness is allowed.
2. The server returns a **download link, valid 5 minutes** (the button renews it). The package is
   a zip: `exam.json` (items with `question`, `source_text`, `images`, `answer_format`),
   `images/*.png`, `answers-template.json`. Same layout as the mock `history-2023-mock-v1.zip`.
3. **Register your project** (up to 3 per team, each category once per team): project name,
   models used, categories, `answers.json`, and base-model answers if "Biggest improvement" is chosen.
4. Upload. The site checks the format at once; organisers grade later.

## Fields

| Field | Value |
|---|---|
| Team code | `TEAM_KEY` (Orest types it; never in chat or repo) |
| Project repository link | `https://github.com/OrestTa/matura-model-trainers-hackathon` (must be public or shared with the jury first; it is **private** as of 07:55 CEST) |
| Readiness checkbox | Tick only when every agent (incl. the Grok bot) has stopped pushing and main is final |
| Project name (max 120) | `Gemma 4 12B QAT + matura exam harness (plan-first essays, 3-of-5 closed vote)` |
| Model 1: name or link | `google/gemma-4-12B-it-qat-q4_0-gguf` |
| Model 1: quantization | `Q4_0 QAT GGUF + mmproj vision projector, 7.15 GB on disk` |
| Categories | Best exam score; Smallest model passing 35% (our only model is 7.15 GB); Biggest improvement only if the base run below is also done |
| Answers JSON | `answers.json` from the stage command below |
| Most capable base model (improvement only) | Model 1 |
| Base model answers JSON (improvement only) | `answers-base.json` from the base command below |

No other model is used: no LoRA, no OCR model, no retrieval model. The size check in
`serve_exam.sh` sums the files it serves and refuses anything over 8.8 GB.

## Commands on the GPU box (after the package is on the box)

```bash
git pull origin main   # before ticking the readiness box; nothing is committed after it
export LD_LIBRARY_PATH=$PWD/work/llama.cpp/build/bin:${CUDA_LIB:-/workspace/work/cuda/lib}
export THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1
export ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b-exam &
unzip final.zip -d final/
python scripts/run_exam.py final/ --model gemma4-12b-exam --mode subtype --concurrency 8 -o answers.json
python scripts/check_submission.py answers.json final/      # same rules as the upload form
```

About 10 minutes on the L40S (essay ~8 min). If time is short: `ESSAY_BEST_OF=1`, or the previous
freeze `--mode raw --model gemma4-12b-think --concurrency 16` (~4 min, same 163/240 on held-out).

Base answers, only for "Biggest improvement" (the untouched model, exam prompt as given, 2k thinking):

```bash
# restart the server as gemma4-12b-think, then
python scripts/run_exam.py final/ --model gemma4-12b-think --mode raw --concurrency 16 -o answers-base.json
python scripts/check_submission.py answers-base.json final/
```

## What we can honestly claim

Held-out May 2023–2026, Claude-graded against the CKE key with pictures viewed: base 163/240 and the
stage path 163/240 (docs/FINAL_RESULTS.md). The stage path scored 43/60 vs 37 on the Jan 2026 practice
paper and won the blind side-by-side essay comparison (71 vs 56/120). Every fine-tune scored below the
base (best: SD1 155/240), so none is shipped. So the expected improvement over the base is about 0.

## Checked

- `scripts/run_exam.py` reads the official package layout and writes `{"exam_id", "answers":[{"id","answer"}]}`
  in the template's order. Its output on the real mock package passes the site's own
  `validateAnswers` (run with node on 27.09) and `scripts/check_submission.py`, which ports it.
- `SOURCE.md` holds the required line exactly.
