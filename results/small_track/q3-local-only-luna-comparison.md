# Q3 paired evaluation using own Codex Luna only

Both frozen submissions were graded entirely by the user’s own Codex GPT-6-Luna plan, using official CKE keys and original images. The new protocol is `local-luna-official-v2`:20 prior local image judgments were reused only with exact packet hashes; remaining visual tasks used original PNGs; short text tasks were batched; every essay received three independent identical checks. No Forgehand marks enter these totals.

| Category | Plain Q3 | Q3 + OCR | Point delta |
|---|---:|---:|---:|
| closed_without_images | 3/4 (75.00%) | 3/4 (75.00%) | +0 |
| closed_with_images | 4/7 (57.14%) | 4/7 (57.14%) | +0 |
| open_without_images | 6/11 (54.55%) | 6/11 (54.55%) | +0 |
| open_with_images | 12/23 (52.17%) | 10/23 (43.48%) | -2 |
| essay | 0/15 (0.00%) | 0/15 (0.00%) | +0 |
| **Full paper** | **25/60 (41.67%)** | **23/60 (38.33%)** | **-2** |

All37 tasks are resolved in each run; both essay triples were0/0/0. Plain Q3 package:2,965,812,064bytes. OCR package:2,974,690,670bytes. Aggregate weights are the size objective; the extra8,878,606bytes produced no measured gain.

Both used the same original questions, source material and images, with offline OCR appended only to candidate context. The official judging context was identical. This is one observed pair; inference serving/batching and judge-sampling variation were not quantified.2023 is development evidence, not an untouched holdout.

Ania: matching Qwen3.5-4B reference remains unverified; older input representations differ, so no numerical Ania delta is claimed. Earlier hybrid24/60 and23/60 reports remain historical; changing the judge protocol is not a model improvement.

Identity evidence: every call explicitly requested `--model gpt-6-luna`, with no fallback configured. CLI response events do not echo resolved model identity. Each call’s command, raw events, output, packet hash and provenance are preserved. Monetary cost of own-plan usage is unknown; no new Forgehand calls were used.
