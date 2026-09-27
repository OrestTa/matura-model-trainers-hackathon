# Bielik runs on the Jan 2026 mock (probny-2026-01), Claude-graded blind (27.09 09:15 CEST)

One Opus grader per answer set, blind to the model, official CKE key, essay < 300 words = 0.
Answers: results/b15/<arm>/answers.json (GPU box, infer.py prompt, temp 0, 500/1600 tokens).

| Arm | Size | Score | Essay |
|---|---|---|---|
| Bielik-1.5B Q8_0 bare (no OCR, no router) | 1.70 GB | 9/60 = 15.0% | 0 (289 words) |
| Bielik-1.5B + OCR/router, no adapters | 1.71 GB | 8/60 = 13.3% | 0 (176 words) |
| Bielik-1.5B + our b15-v1 adapters (149 real rows, mock unseen) | 1.79 GB | 8/60 = 13.3% | 0 (274 words) |
| Bielik-1.5B + Codex clean-v3 adapters | 1.79 GB | 6/60 = 10.0% | 0 (243 words) |
| Bielik-1.5B + Codex all-papers adapters (**trained on this mock**) | 1.79 GB | 5/60 = 8.3% | 0 (681 words, bullet list, many errors) |
| Bielik-4.5B Q8_0 + OCR, no adapters | 5.06 GB | 13/60 = 21.7% | 0 (250 words) |

Conclusion: no Bielik-1.5B setup is near 35% (21/60) and training gives no gain over the bare model. Dropped.
Bielik-4.5B with this simple prompt is also below 35% here; rerun with our harness + essay guard pending.

## Essay length guard (results/b15/{base,ours}/answers-guard.json), graded blind 09:30 CEST
Both 0/15: base-guard 468 words but the essay is printed twice (~234 unique words, bullet list, factual errors);
ours-guard 716 words, a loop of the same block (~150 unique words). Continuing a 1.5B essay does not make it pass.

## Five categories (python results/judged/b15-probny/breakdown.py bare base ours)
| arm | closed | open | essay | text only | with pictures | total |
|---|---|---|---|---|---|---|
| bare | 2/7 | 7/38 | 0/15 | 5/18 | 4/27 | 9/60 |
| base | 2/7 | 6/38 | 0/15 | 5/18 | 3/27 | 8/60 |
| ours | 2/7 | 6/38 | 0/15 | 5/18 | 3/27 | 8/60 |

## 09:35 CEST: Bielik-4.5B through our harness, and plain Gemma (thinking on), graded blind
| arm | closed | open | essay | text only | with pictures | total |
|---|---|---|---|---|---|---|
| Bielik-1.5B bare (baseline) | 2/7 | 7/38 | 0/15 | 5/18 | 4/27 | 9/60 |
| Bielik-4.5B + OCR, simple prompt | 2/7 | 11/38 | 0/15 | 9/18 | 4/27 | 13/60 |
| Bielik-4.5B + OCR, our harness | 1/7 | 9/38 | 1/15 | 8/18 | 2/27 | 11/60 |
| Bielik-4.5B + OCR, our harness, subtype | 2/7 | 10/38 | 0/15 | 8/18 | 4/27 | 12/60 |
| Gemma 4 12B QAT plain (--mode raw, thinking on) | 2/7 | 23/38 | 7/15 | 11/18 | 14/27 | 32/60 |

Our stage harness on the same paper: 43/60 (rehearsal, results/rehearsal/stage-probny) and 38/60 (final e2e).
So Gemma plain 32 -> ours 38-43 (+10 to +18 pp) with thinking ON in the base. Bielik-4.5B stays below 35% (21/60)
in every setup, so it cannot enter "smallest model"; the Gemma project does (7.15 GB) unless E4B passes.
