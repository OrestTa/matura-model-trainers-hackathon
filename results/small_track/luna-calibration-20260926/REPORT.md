# Blinded Luna calibration — 2026-09-26

Forgehand GPT-6-Luna was compared with existing GPT-6-Sol judgments on five fixed official CKE2023 tasks, one per category, repeated three times. Sol remains the primary judge. No Sol marks or rationales were sent to Luna.

| Category | Task | Sol | Luna repeats | Point agreement |
|---|---|---:|---|---:|
| closed_without_images | 2.2 | 0/1 | 0, 0, 0 | 3/3 |
| closed_with_images | 3 | 1/2 | 1, 1, 1 | 3/3 |
| open_without_images | 2.1 | 0/1 | 0, 0, 0 | 3/3 |
| open_with_images | 1 | 1/1 | 1, 1, 1 | 3/3 |
| essay | 26 | 0/15 | 3, 4, 0 | 1/3 |

Point agreement: **13/15 (86.7%)**. Uncertainty agreement: **15/15**, but every selected task had a false Sol uncertainty flag, so this does not test difficult uncertainty detection. Short-task points were stable. Essay points varied from0 to4, population variance2.889.

Estimated pilot cost: **$0.1035925**, using conservative Sol token rates; the exact Luna invoice price was not verified. Budget cap$0.15. All15 calls completed.

This is a small non-random pilot, not a full exam, not an accuracy study and not evidence that Luna should replace Sol. No averaging or changes to primary Sol grades. Original requests are bound by hashes in manifest.json; every response is preserved.
