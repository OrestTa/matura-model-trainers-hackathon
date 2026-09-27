# Smallest model and Biggest improvement: state before the freeze (27.09 08:45 CEST)

Owner: Claude thread "Take over Codex tracks" (Orest 08:33 CEST: Codex is out of usage, Claude runs all three
tracks; Codex and the Grok bot do nothing further). Codex's own work: none found in this repo (no Codex commits);
GPU box inventory requested, results/codex-inventory/ when it lands.

Codex's result (screenshot from Orest, 08:35 CEST; files not in repo, project files or HF): Bielik-1.5B Q8_0
+ OCR/router 11/60 (1.709 GB) -> + five clean-v3 adapters 13/60 = 21.7% (1.789 GB). Below 35%, and the +2 is
within grading noise ("0-3 points" by Codex's own note). Not used for either track.

**Decision (08:50 CEST, Orest: take over, don't wait):** smallest = Bielik-4.5B FP8; improvement = Gemma 4 12B
bare vs our harness.

## Biggest improvement (proposed: same Gemma 4 12B, bare vs our exam harness)

| | Base (untouched) | Ours | Delta |
|---|---|---|---|
| Model file | `google/gemma-4-12B-it-qat-q4_0-gguf` + mmproj, 7.16 GB | same file, no LoRA | size 0 |
| Setup | plain request, thinking off (`--mode raw --model gemma4-12b`) | `--mode subtype --model gemma4-12b-exam`, essay plan + best of 3 | |
| Held-out May 2023-26, Claude-graded, pictures viewed | **123/240** (33/29/33/28), g4r0 | **163/240** (38/44/39/42), stage-heldout | **+40 = +16.7 pp** |

Source: results/judged/TABLE.md rows g4r0 and stage-heldout (same grader, same grading rules).
Caveat to state honestly: the gain comes from the harness (turning on 2k-token thinking, per-type prompts, essay
plan + best of 3), not from training. The rules allow "fine-tune, harness, or both".
HF: no new weights; the model is the same file as the best-score entry (orestta/matura-gemma4-12b-best-score).

Stage (after the best-score run, same server restarted with the base key):
```bash
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b &
python scripts/run_exam.py final/ --model gemma4-12b --mode raw --concurrency 16 -o answers-base.json
python scripts/check_submission.py answers-base.json final/
```
The trained answers are the best-score track's answers.json (same run, no second pass).

Missing before the freeze: one smoke of the base command on the mock package (check_submission OK).

## Smallest model passing 35% (current entry: Bielik-4.5B FP8)

| Item | State |
|---|---|
| Model | `speakleash/Bielik-4.5B-v3.0-Instruct-FP8-Dynamic` (public HF, unchanged), key `bielik-4.5b-fp8` |
| Size on disk | 4.90 GB (to re-measure on the box) |
| Score | 24/60 = 40.0% on May 2023 (Claude-graded, pictures as Tesseract OCR text); Sol 48.3%, Grok 46.7% |
| Harness | `serve_exam.sh bielik-4.5b-fp8` + `run_exam.py --model bielik-4.5b-fp8` (OCR on) |
| Tested end to end | **no**: the exact command has never run on the box |
| Needs on the box before offline | vLLM that loads FP8, `tesseract-ocr tesseract-ocr-pol`, the weights downloaded |
| Smaller candidates | Bielik-1.5B FP8 18.3% (Sol), Qwen3-4B Q3_K_M 22% / 19.4% with OCR: all below 35% |

Missing before the freeze: download + size check, one smoke on the mock package, check_submission OK.
