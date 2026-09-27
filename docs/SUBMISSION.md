# Final exam submission: every field, ready to paste (27.09.2026)

Form: https://warsawmodeltrainers.dev/submissions.html?exam=final (read 07:55 CEST, incl. its
`submissions.mjs` and `submission-validation.mjs`). **Nothing has been submitted.**

The model and harness entered: **[docs/BEST_SCORE_CANDIDATE.md](BEST_SCORE_CANDIDATE.md)** (harness: main at `007fb17` or later).

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
| Readiness checkbox | Covers the whole team and every project, Codex's too. Tick only when every agent (incl. the Grok bot and Codex) has stopped pushing and all projects are final |
| Project name (max 120) | `Gemma 4 12B QAT + matura exam harness (plan-first essays, 3-of-5 closed vote)` |
| Model 1: name or link | `google/gemma-4-12B-it-qat-q4_0-gguf` (our identical copy: https://huggingface.co/orestta/matura-gemma4-12b-best-score, private) |
| Model 1: quantization | `Q4_0 QAT GGUF + mmproj vision projector, 7.15 GB on disk` |
| Categories | **Best exam score only** (Orest 08:00 CEST). Codex registers the other two categories as its own projects under the same team code |
| Answers JSON | `answers.json` from the stage command below |

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

## One freeze, three tracks (plan from 27.09 08:35 CEST; Claude coordinates all submissions; details of tracks 2–3: docs/TRACKS_SMALL_AND_IMPROVEMENT.md)

Codex ran out of usage, so Claude now runs all three categories. Grok bot and Codex do nothing further.
The site's readiness confirmation is **one per team**: after it, no project may change. So everything
for all three tracks must be committed first, then one confirmation, one exam package, three runs.

| Track | Project | Model(s) | Answers | Status |
|---|---|---|---|---|
| Best exam score | Gemma 4 12B QAT + matura exam harness | `google/gemma-4-12B-it-qat-q4_0-gguf`, 7.15 GB | `answers.json` from the stage command above | ready (main 007fb17+, smoke b371e40 OK) |
| Smallest model passing 35% | Bielik-4.5B FP8 + OCR | `speakleash/Bielik-4.5B-v3.0-Instruct-FP8-Dynamic`, 4.90 GB (+ tesseract pol) | `run_exam.py --model bielik-4.5b-fp8` | 40.0% on May 2023 only; **never run end to end**; smoke on mock pending |
| Biggest improvement | same Gemma 4 12B, bare vs our harness | same file as best score, 7.15 GB | best-score `answers.json` + `answers-base.json` (`--mode raw --model gemma4-12b`, thinking off) | held-out 123 → 163/240 = +16.7 pp; base command smoke on mock pending |

**Pending (08:45 CEST):** Orest asked for a Bielik-1.5B fine-tune (past papers only, scored on the Jan 2026 practice
paper). If the trained 1.5B scores ≥ 21/60 (35%), one project "Bielik-1.5B" takes Smallest + Biggest improvement (base =
bare Bielik-1.5B answers) and the Gemma improvement pair is not used. Otherwise Bielik-4.5B = smallest, Gemma = improvement.
If the 1.5B is not scored by 10:00 CEST it is dropped. The freeze waits for this.

Before the freeze, each track needs: everything on main (harness, configs, commands, results); every shipped model or
adapter on a private HF repo under `orestta/` with a model card (best score: orestta/matura-gemma4-12b-best-score, card
re-uploaded from a78ac0a); its model files on the GPU box and their size measured; one command that
turns the exam package into a valid answers.json (checked with `check_submission.py` on the mock package);
its results for base and trained in the repo; and its section in this file.

After the freeze (in this order, on the L40S, one model at a time):
1. Confirm readiness with the team code and repo link; fetch the package straight onto the box from the 5-minute link.
2. Run Best exam score (~10 min), check, upload as its own project (category Best exam score).
3. Run the smallest-model track, check, upload (category Smallest model passing 35%).
4. **Required for Biggest improvement: the base-model answers from the same exam.** Restart the server bare and run:
   `ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b &` then
   `python scripts/run_exam.py final/ --model gemma4-12b --mode raw --concurrency 16 -o answers-base.json` and
   `python scripts/check_submission.py answers-base.json final/`. Upload `answers-base.json` as "Base model answers"
   (most capable base model = Gemma 4 12B, the same model row) in the project that has the Biggest improvement category.
   Expected base score from held-out: 123/240 = 51.3% (thinking off) vs our 163/240 = 67.9%.
Every upload is a separate project with its own receipt. Receipts go to results/final-exam/.

## Orest's steps, in order (08:40 CEST)

1. ~~Make the repo public~~ done (08:19). ~~Update team on the site~~ done by Claude (08:27, Gemma 4 12B, 7.15 GB).
2. Pick the Biggest improvement baseline (thinking off = +16.7 pp harness gain, thinking on = ~0, or skip).
3. Cancel all Nebius jobs in the Nebius console (no agent has a working token).
4. Say "go". Then Claude confirms readiness with the team code, the GPU box fetches the package from the
   5-minute link and runs: best score, then the improvement base run, then smallest (Bielik-4.5B, only if it
   produces a valid answers.json). Each answers file is checked with check_submission.py and uploaded as its own project.
5. After the freeze: push the tag on that main commit, `git tag best-score-candidate && git push origin best-score-candidate`
   (tag pushes are blocked from the cloud container).
