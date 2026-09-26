# Small-model effort wrap-up — 2026-09-26

Historical interruption snapshot, superseded by the user's clarification:
wrap-up meant achieve the smallest model above 35%, not stop jobs. Work is
reauthorized with Forgehand gpt-6-sol as the sole judge and bounded credit use.
Resource states below describe the interruption, not current live status.

## What is saved

- Official history corpus: 2017–2026, ten papers, 369 tasks, 540 points, official
  keys stored separately from candidate inputs. Two additional 2015–2016 papers
  were excluded from this synthesis; prior project/model exposure is unknown.
- Organizer mock: `data/small_track/official_mock_v1/`, 37 items, 60 points,
  19 checksum-verified PNGs and exact input contract.
- Synthetic corpus: `data/small_track_synthetic/final_manifest.json`, 100 accepted
  synthetic exams, 3843 tasks / 6000 points. Acceptance is synthetic QA, not an
  official CKE grade. Exact dataset hashes and train/validation metadata retained.
- Inference and evaluation artifacts: `results/small_track/`. Twenty route trials
  completed with 148 generated target answers; other routes explicitly reuse
  frozen baseline answers, so these are composed development results.
- All twenty route trials have independent Sol results. Ten Bielik 1.5B trials
  have finalized Codex adjudication; ten 4.5B trials remain unfinalized by Codex.
- Nebius 2024 development outputs: two model submissions, 40 answers each, under
  `data/small_track_cloud/nebius-20260926/`. Ungraded at user stop.
- Candidate-only five-route harness, deterministic classifier, per-route model /
  adapter / prompt settings, measured artifact accounting and strict submission
  exporter. The default route file remains an unmeasured endpoint template, not a
  proven combined deployment. Twenty-four focused tests passed before wrap-up.

## Selection and limitations

Bielik 1.5B Q4 is the smallest functioning candidate evaluated here, at
972797408 serialized bytes. Prefer its verified bare configuration to the
regressing generic prompt and caption variants. Concise closed-text routing is
a development candidate only; no frozen combined harness has passed held-out
validation. No qualifying full-modality result is established.

The first SFT artifact is unusable. Native GGUF inference was coherent but its
Transformers conversion was garbled before training; the trained output then
collapsed. Preserve these artifacts as diagnostics and do not deploy the adapter.

Earlier PDF-derived text inputs, the organizer JSON mock and Ania's benchmark are
different input representations. Do not rank their raw percentages as matched
comparisons. See per-run adjudicated summaries for five-category scores, paired
changes, official rubric evidence and Ania reference caveats.

## Resources and costs

All owned Modal apps were verified stopped at wrap-up; other agents' apps were
left untouched. The owned Nebius VM was verified STOPPED through the live API;
evidence is in `data/small_track_cloud/nebius-20260926/stopped_instance.json`.
Preserve its managed disk and outputs; storage can still
incur charges while a VM is stopped. No deletion or shared-workload changes.

Persisted estimated Forgehand judging spend: $2.8374525 of its $5 allocation.
Provider balances are shared and billing can lag; this is not an account-wide
final invoice. No top-ups, Git fetches or pushes during this isolated execution.

## If work is resumed

First repair and smoke-test the model conversion, or use a verified native HF
base. Finish the unfinalized evaluations only if the user reauthorizes judging.
Freeze route choices, run the actual combined pipeline on excluded papers,
measure every shipped weight and adapter, and validate the final answer JSON.
Do not infer a working small model from a development-only composed score.
