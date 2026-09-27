# Final entry for all three categories (27.09 10:30 CEST)

**Decision (Orest, 10:26 CEST, "Best of both"):** one project, Gemma 4 12B QAT (7.15 GB, no fine-tune), enters
**Best exam score**, **Smallest model passing 35%** and **Biggest improvement**. Every Bielik candidate is dropped.
The models we tried below were all graded blind by Claude on the January 2026 mock (probny-2026-01, 60 points,
official CKE key, pictures viewed, essay under 300 words = 0).

| Category | Entry | Size | Evidence |
|---|---|---|---|
| Best exam score | Gemma 4 12B QAT, our stage harness (`--mode subtype`, essay plan + best of 3) | 7.15 GB | 163/240 held-out, 38–43/60 mock |
| Smallest model ≥35% | same project | 7.15 GB | no smaller model reached 21/60 (table below) |
| Biggest improvement | same project; base = same file, plain exam prompt, thinking on | 7.15 GB | mock 32/60 → 38–43/60 = **+10 to +18 pp** |

Base run for the improvement category: `python scripts/run_exam.py final/ --model gemma4-12b-exam --mode raw
--concurrency 16 -o answers-base.json` (same server as the best-score run; 322 s on the mock, 0 blank).
Details and form fields: [SUBMISSION.md](SUBMISSION.md).

## Biggest improvement: Gemma 4 12B, plain vs our harness (mock, five categories)

| Category | Plain Gemma, thinking on (base) | Ours: rehearsal | Δ | Ours: final e2e | Δ |
|---|---|---|---|---|---|
| Closed /7 | 2 | 3 | +1 | 3 | +1 |
| Open /38 | 23 | 29 | +6 | 29 | +6 |
| Essay /15 | 7 | 11 | +4 | 6 | −1 |
| Text only /18 | 11 | 13 | +2 | 13 | +2 |
| With pictures /27 | 14 | 19 | +5 | 19 | +5 |
| **Total /60** | **32 (53.3%)** | **43 (71.7%)** | **+18.3 pp** | **38 (63.3%)** | **+10.0 pp** |

Sources: results/judged/b15-probny/gemma-raw (base, cc1beca), results/judged/matura-judge-claude-stage-rehearsal-probny,
results/judged/matura-judge-claude-final-e2e-probny. The two harness runs are the same setup; the gap is the essay
(run-to-run noise). Why thinking on is the base: it is the model's default and the fairer comparison (Orest). With
thinking off the base is lower (held-out 123/240 vs 163), so the gain would look bigger than it is.
On the four held-out papers the harness equals the thinking-on base (163 vs 163); the mock gain comes from open
questions and pictures, which held-out does not confirm. State this honestly if asked.

## Dropped candidates (mock, five categories)

| Model / setup | Size | Closed /7 | Open /38 | Essay /15 | Text only /18 | Pictures /27 | Total /60 | Why dropped |
|---|---|---|---|---|---|---|---|---|
| Bielik-1.5B Q8_0 bare | 1.70 GB | 2 | 7 | 0 | 5 | 4 | 9 | below 35% |
| Bielik-1.5B + our harness + OCR | 1.71 GB | 1 | 8 | 0 | 6 | 3 | 9 | no gain over bare |
| Bielik-1.5B + our harness, no OCR | 1.70 GB | 1 | 7 | 0 | 5 | 3 | 8 | worse than bare |
| Bielik-1.5B + our harness, per-type (subtype) | 1.71 GB | 1 | 5 | 0 | 2 | 4 | 6 | worse than bare |
| Bielik-1.5B + OCR/router, no adapters | 1.71 GB | 2 | 6 | 0 | 5 | 3 | 8 | worse than bare |
| Bielik-1.5B + our b15-v1 adapters | 1.79 GB | 2 | 6 | 0 | 5 | 3 | 8 | training gives no gain |
| Bielik-1.5B + Codex clean-v3 adapters | 1.79 GB | | | 0 | | | 6 | training gives no gain |
| Bielik-1.5B + Codex all-papers adapters (trained on this mock) | 1.79 GB | | | 0 | | | 5 | trained on the test; still worse |
| Bielik-4.5B Q8_0 + OCR, simple prompt | 5.06 GB | 2 | 11 | 0 | 9 | 4 | 13 | below 35% (21/60) |
| Bielik-4.5B + OCR, our harness | 5.06 GB | 1 | 9 | 1 | 8 | 2 | 11 | below 35% |
| Bielik-4.5B + OCR, our harness, subtype | 5.06 GB | 2 | 10 | 0 | 8 | 4 | 12 | below 35% |
| Gemma 4 E4B (Q4 5.21 GB, Q2 4.21 GB) | 4.2–5.2 GB | | | | | | not run | dropped at 09:40 CEST to keep the GPU for the final runs |

Empty cells: the per-category split was not computed for those arms; totals are from their claude_score.json.
Sources: results/judged/b15-probny/README.md and `<arm>/claude_score.json` (9bc74e5); answers in results/b15/.

**Why Bielik-1.5B fails:** the model lacks the history knowledge. Its essay on the Vasa dynasty names Stanisław August
Poniatowski as a Vasa king and dates the end of serfdom to 1724, and it writes bullet lists instead of prose. The
essay scored 0/15 in every version: length guard (468 and 716 words, but printed twice or looping), anti-repetition
sampling (243 words), writing it in parts (995 words, two topics mixed, >5 serious errors). No harness, OCR, voting
or adapter setup beat the bare 9/60, so its best improvement is 0.

**Why Bielik-4.5B fails:** best 13/60 = 21.7%, below the 35% bar (21/60) in every setup. An earlier 40% on
May 2023 (FP8, OCR text) was not reproduced on the mock with the same grading.

**Codex's result** (screenshot, 08:35 CEST): Bielik-1.5B + OCR/router 11/60 → + clean-v3 adapters 13/60. Under our
grading the same arms scored 8 and 6.
