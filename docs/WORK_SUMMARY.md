# Work summary: best matura score (26–27 Sep 2026)

Owner: thread "Win best matura score". Times CEST. All numbers are Claude-graded against the CKE key, with
pictures viewed and the full essay criteria, on the held-out papers May 2023–2026 (4 × 60 = 240 points)
unless marked "practice".

## Result

| | Score | Size |
|---|---|---|
| Deck (Ania's slides, Gemma 4 12B bf16, May 2023 only) | 46/60 | 23.92 GB |
| Our base (Gemma 4 12B QAT, raw, 2k thinking) | 163/240 (41/42/39/41) | 7.16 GB |
| **Shipped: stage path (base + essay "plan, best of 3")** | **163/240 (38/44/39/42), measured** | **7.15 GB** |
| Goal set at 22:20 (+10 points) | 187/240 | ≤ 8.8 GB |

We did not reach the +10 goal. The shipped setup equals the base on the total and writes better essays when
graded side by side (40 vs 35 of 60 on the held-out papers). It also stops the essay from falling under 300 words,
which scores 0.

## What ships

- Model: `google/gemma-4-12B-it-qat-q4_0-gguf` + mmproj, no LoRA, no OCR. Size check: 7.15 GB of 8.8 GB.
- Run: `run_exam.py --model gemma4-12b-exam --mode subtype --concurrency 8` with
  `ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1`.
  - Open questions: the plain exam prompt, 2k thinking.
  - Closed questions: 5 samples, 3-of-5 vote (Orest 22:33).
  - Essay: plan first, 16k thinking, 3 drafts, keep the best one of 300+ words.
- Dress rehearsal of this exact path: 0 blank answers on all 5 papers, 9–11 min per paper on an L40S.
- Fallback if stage time is short: `ESSAY_BEST_OF=1`, or `--mode raw --model gemma4-12b-think` (~4 min per paper).
- Full commands: `docs/EXAM_DAY_BEST_SCORE.md`.

## What we tried

| Idea | Outcome |
|---|---|
| 6 LoRA fine-tunes on synthetic + past-paper data (A1, B4m2, Hm2, S4m2, Gm3, A01) | All below base (A01 131/240); they broke the essay |
| SD1: LoRA self-distilled from the base on real past papers only | 155/240 vs 163 |
| Picture LoRA V1 (135 past-paper picture items) | Trained and backed up, never graded; not used |
| OCR notes for pictures | −6.5 points per 100 on held-out picture items |
| Per-question-type prompts and settings (harness) | 162 vs 159.5 on held-out, within noise |
| Best of 3 for open answers; describe the picture first | Within ±2 on 49 practice items |
| Essay length guard alone | −7/150 on practice essays |
| Essay plan prompt | +5/150 on practice essays |
| **Essay plan + best of 3** | **+9 to +13/150 practice; 71 vs 56/120 held-out side by side; shipped** |
| Essay retrieval from fact sheets + Wikipedia | Level with best of 3; not shipped |
| Essay best of 5 instead of 3 | 71 vs 69/150 on practice essays, noise |
| Thinking 4k or 8k instead of 2k | No gain; 8k leaves blank answers |

## Infrastructure built

- `scripts/run_exam.py` fails a run with more than 10% blank answers; `infra/jobs/rehearsal.sh` retries a paper
  on a fresh server.
- `scripts/serve_exam.sh` sums every model file against 8.8 GB and refuses to serve above it; turns off
  llama.cpp's 8 GB prompt cache (it killed servers on a 30 GB box).
- Router: routed LoRAs per question type, essay best-of-N, open best-of-N, picture description step.
- `docs/ARTIFACTS.md`: where every model, adapter and data dump lives, with rebuild commands; adapters backed up
  to private Hugging Face repos.

## Rules kept

- Past answer keys were used only as training data, never in prompts.
- The held-out May 2023–2026 papers were never used for training or for choosing settings.
- Sizes are the quantized file sizes, all model files summed.

Full tables: `docs/FINAL_RESULTS.md`. Job log: `docs/STATUS.md`.
