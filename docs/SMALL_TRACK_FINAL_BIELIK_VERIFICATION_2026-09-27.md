# Final fresh Bielik verification — 2026-09-27

**The selected Bielik1.5 recipe did not reach35%.** Fresh own-Codex GPT-6-Luna judgments give a provisional10/60 (16.67%), with settled lower9/60 and unresolved upper14/60 (15.00–23.33%). Even full credit for every unresolved item cannot reach21/60. No further judge calls were made to chase a score.

Model:Bielik-1.5B-v3.0-Instruct Q8_0, zero adapters, frozen eligible real-only router and image-route OCR. Total deployed weights:1,708,932,059bytes (1.709GB). All37 fresh answers are nonempty and transport-error-free.

| Category | Fresh primary | Settled lower | Unresolved upper |
|---|---:|---:|---:|
| closed_without_images | 1/4 (25.00%) | 1 | 1 |
| closed_with_images | 2/7 (28.57%) | 2 | 4 |
| open_without_images | 3/11 (27.27%) | 3 | 3 |
| open_with_images | 4/23 (17.39%) | 3 | 6 |
| essay | 0/15 (0.00%) | 0 | 0 |

All20 own-Luna calls finished:17 passed validation,3 had item-metadata failures. IDs14.1,14.2,17,19 remain unresolved; their raw responses are retained. The essay checks were0/0/0; the first mark is primary. The exact total remains unresolved, but the threshold failure is definitive within these conservative bounds. No assistant assigned or changed any examination mark.

## Comparison limits

Fresh answer inference on a frozen previously computed OCR/router candidate; OCR and routing were not re-executed.

The strongest earlier eligible Q8 base result was provisional16/60, bounds16–19, with categories2/4,4/7,5/11,5/23,0/15. This verification reconstructed the same37 request hashes, but the answering-server binary changed fromf805c57a2 to81bc6b8. Only5/37 answer strings match the old run. It is fresh current-runtime verification, not bit-for-bit reproduction; no new optimization arm or controlled improvement delta was measured.

Ania Bielik1.5 reference15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs and55point subset differ; five-way reference unavailable; no comparable numeric delta.

The2023 paper is a development case, not an untouched holdout. The router provenance audit excluded2023/2024 evaluation and2015/2016 reserved papers. Fresh evaluation inputs contain no official keys; keys and original images enter only the post-inference judge packets.

## Reproducibility evidence

Inference run:`results/small_track/20260927-bielik15-q8-final-verification/evaluation/`.

Compact machine-readable record:`results/small_track/bielik15-q8-final-verification-compact.json`. Local full report:`results/small_track/bielik15-q8-final-fresh-luna.{json,md}`; original responses, prompts hashes and per-item grades are retained under the run’s`luna_fresh_v4/` directory.

The committed scripts are`prepare_bielik_final_luna.py`,`local_luna_fresh_grade.py`, and`report_bielik_final_luna.py` in`scripts/small_track/`. They require full coverage and immutable input/request hashes, default to dry-run, use no prior verdict cache, cap execution at4 workers/180seconds per call, preserve valid siblings, and do not retry failures. Five focused transport/schema validation tests pass.

Own Codex plan; monetary cost unknown. No Forgehand judging API.
