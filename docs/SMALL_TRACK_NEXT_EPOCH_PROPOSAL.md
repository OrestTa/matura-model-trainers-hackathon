# Predeclared Bielik extra-epoch experiment — not launched

## Rationale and limits

One epoch currently means25closed-text,76open-text,7closed-image,25open-image and
5essay updates. Additional text training is a testable hypothesis: there are only
101text updates and the targets are official answers. It is not established that
undertraining caused weak full-paper scores. The training log's first/last-quarter
mean losses decrease for the text routes (closed3.26→1.08, open2.15→1.26), but these
are different examples, so that trend cannot prove learning or justify more epochs.
The essay route's five examples and image-route OCR limitations argue against
indiscriminately repeating all five datasets. Earlier adapter regressions also make
“more epochs must help” an unsupported assumption.

No evaluation keys, per-question evaluation failures or new historical targets were
used to design this proposal. Caption augmentation is stopped after all three
caption paths failed independent fidelity checks.

## Frozen data and routes

Training remains the clean-v3 manifest
`da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab`.
Only closed_without_images(25rows) and open_without_images(76rows) are eligible for
this experiment. Closed-image, open-image and essay adapters remain exactly at their
current one-epoch hashes. The learned classifier, OCR, source serialization and
inference prompts remain frozen. This creates a two-route training ablation within
the same six-model system, without increasing deployed weight size.

Reserve the12new primary-key-verified2012/2014text examples as validation, not more
training:2closed/10open. Their file is
`data/small_track_legacy_audit_20260927/optional-text-training.jsonl`, SHA256
`39787692d5d6b8990d6f8f6a5bfa8b94dc0fc7bf377cc649f1eef6ad69db2122`.
Candidate-input character5-gram comparison against138training rows found maximum
Jaccard0.0782 and no near-copy at0.8. This is a split check, not a claim these public
exams were absent from base-model pretraining.2015/16reserved and2023/24evaluation
papers remain excluded. There is no new image/essay validation coverage, which is
why those three routes are not further trained in this proposal.

## Fixed plan and stopping rule

1. Use the same native public mirror revision
   `a3a660b10fdba3a7b03c3349567e54d8875f9ac9`, exact BF16 hash and isolated runtime
   from clean-v3. Before training, calculate assistant-only per-example mean token
   negative log-likelihood on the12validation rows for the native base. This is a
   likelihood diagnostic, not an exam grade.
2. For each of the two text routes, start from a fresh native base and reproduce
   epoch1:seed7291, rank8, alpha16, MLPgate/up/down targets, dropout0, AdamW5e-5,
   batch1, gradient clipping1, assistant-only labels,3072-token hard exclusion.
   Keep EOS/chat template unchanged. Save checkpoint and optimizer state after the
   first complete pass. No truncation or silent skipped rows is allowed.
3. Score epoch1 on the untouched12validation examples using their recorded task
   categories, not an adjusted router. Require mean per-example NLL below native
   base overall. Otherwise stop without epoch2; the data does not support a simple
   undertraining explanation. Save every diagnostic regardless of outcome.
4. If that gate passes, resume each same optimizer/checkpoint for exactly one more
   complete pass. Use a predeclared second shuffle seed7292. At most202training
   updates total across two routes; no learning-rate search, third epoch or manual
   example reweighting. Save epoch2 separately; do not overwrite epoch1.
5. Keep epoch2 as a candidate only if validation mean per-example NLL falls by at
   least2% versus epoch1 and neither route's mean NLL worsens. The closed route has
   only two validation examples, so this guard has low statistical power. Record
   per-example deltas and truncation/error counts. A likelihood improvement alone
   does not establish35% official accuracy.
6. Only after that decision is frozen, convert the two chosen adapters and check
   exact GGUF identities/rank/scaling. Run one fixed complete-paper comparison with
   the unchanged classifier/OCR/prompts/decoding and own Codex Luna evaluation.
   Keep both passing and failed experiments in the record. Do not pick captions or
   adapter routes using per-question evaluator feedback.

Proposed resource ceiling for a future separately approved job: one shared GPU,
PyTorch allocator fraction0.20, free-memory gate(cap+1GiB), hostRAM≥6GiB,900seconds
plus15seconds termination grace. Reuse staged native weights and isolated packages;
no top-ups, new model downloads, shared-environment edits or other-agent process
changes. Estimated training work is202small-model updates; runtime/billing must be
verified before launch. No job or paid API call was launched for this proposal.
