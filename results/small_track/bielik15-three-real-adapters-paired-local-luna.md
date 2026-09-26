> **INVALID_SPECIALIST_ROUTING — diagnostic outputs only.** The server warned that repeated `--lora` flags load only the last value (server.log lines3–4). Declared adapter IDs were not verified. The scores below are preserved, but their differences do not establish any trained-specialist improvement and this experiment is nonqualifying for threshold certification. See `bielik15-harness-diagnosis-20260926.json`.

# Bielik1.5 Q4_K_M: three real-data adapters versus matched base

The classifier, route-specific OCR, original paper, model revision, prompt settings and token limits are held constant. All37tasks/60points are covered in both submissions. The filename says five specialists, but this pilot has three trained adapters: closed text, open text and essay. Image routes use the base model.

Matched-base aggregate package:982,161,371bytes (0.982GB). Three-adapter package:1,030,569,275bytes (1.031GB).

| Category | Matched base, primary points | Three adapters, primary points | Observed delta |
|---|---:|---:|---:|
| closed_without_images | 1/4 (25.00%) | 1/4 (25.00%) | +0 |
| closed_with_images | 3/7 (42.86%) | 4/7 (57.14%) | +1 |
| open_without_images | 2/11 (18.18%) | 4/11 (36.36%) | +2 |
| open_with_images | 2/23 (8.70%) — uncertain | 1/23 (4.35%) — uncertain | -1 |
| essay | 0/15 (0.00%) | 1/15 (6.67%) — uncertain | +1 |

**Full paper:** primary/provisional8/60 (13.33%) versus11/60 (18.33%), a provisional+3points. Settled lower bounds are8/60 and10/60. Exact full-paper delta remains unresolved. Base essay repeats0/0/0; trained essay repeats1/2/1, with the first mark retained and disagreement flagged. Neither submission establishes the35%target.

The settled paired short-task gain is+2points across45possible points. Task13.1 has identical answer bytes and identical0marks, but both returned empty image-inspection metadata; its common uncertainty cancels in that short-task difference. Raw outputs remain preserved, with conservative uncertainty added. The whitespace-only baseline answer14.1 was not repaired.

Only the open-text predicted route improved by2settled points; closed text was unchanged. Image routes have no adapters and moved+1/−1, net0, indicating repeated-generation variation. All17identical-answer pairs received matching points. Per-route contributions are observational breakdowns, not new independent ablation runs.

Ania Bielik1.5 reference:15/55 (27.27%), closed5/11, open9/29, essay1/15. Its adapted-input subset is noncomparable; five-category reference unavailable, so no numerical Ania delta is claimed.

All new judging used own Codex GPT-6-Luna, official keys and original images. No Forgehand or assistant/Astra grading. Own-plan monetary cost is unknown. Compute reports an official essay-training topic overlap with2024; no2024holdout claim is made. This evaluation uses2023.
