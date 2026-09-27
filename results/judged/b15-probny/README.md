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
