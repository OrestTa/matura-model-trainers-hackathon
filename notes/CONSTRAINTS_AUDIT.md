# Constraints audit (PDF FAQ + rules)

## Offline (exam / Sunday)
- Building: download anything, closed APIs OK for synthetic data.
- Exam: no external APIs or web search; answers without human help.
- Local RAG and tools allowed. Base model must stay <=8.0 GB on disk before fine-tuning, and the shipped post-FT package should stay <=8.8 GB. RAG KB is excluded.
- Cloud GPU OK if model answers locally (no calling ChatGPT etc.).
- Exam script may send answers to organizers; the model/harness must not fetch knowledge online during the test.

## Tracks
1. Best final exam score (harness+model OK)
2. Best progress = improvement over untouched bare model(s)
3. Smallest model >=35%

## Issues found in our runs
1. Practice `kind=base` was NOT bare model. Label said "untouched" but answers came from deterministic `geo_solver` (same as tuned). Score 14/15 is harness-inflated base, so practice "progress" is meaningless (14->14).
2. Local history "baseline" 15/30 or 48/90 is offline HF generate with gold dropped - method OK - but items are easy hand-authored factoids, not CKE matura. High % is dataset ease, not proof of matura readiness. Letter skew (B/A heavy) also inflates vs balanced exams.
3. 10:35 GEO-025=`C` uses public practice-answer consensus baked before submit (build-time OK); tuned harness is allowed. Still does not fix the dishonest base filing.

## Fixes going forward
- Sunday: `base` = model only (no geo formulas, no RAG unless organizers count that as harness-only for tuned). `tuned` = full harness+LoRA+RAG.
- Local metrics: report train-set MCQ scores as dev/practice only, never as official baseline.
- Keep answering path offline (local weights + local chunks); network only for organizer submit RPC if required by their client.
