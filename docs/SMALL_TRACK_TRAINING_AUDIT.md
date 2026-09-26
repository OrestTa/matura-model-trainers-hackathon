# Bielik real-data training audit — 2026-09-26

This audit reads training data, candidate inputs, tokenizer metadata, adapter files and runtime logs. It does not grade answers or inspect evaluation keys. Findings are mechanisms and distribution differences, not proof that any one caused the observed regression. No training or inference was launched.

## Confirmed alignment and remaining numerical checks

Native pinned `cpral/Bielik-1.5B-v3.0-Instruct-ungated` revision `a3a660b10fdba3a7b03c3349567e54d8875f9ac9` and deployed GGUF have exactly equal ChatML template strings. Both begin with the BOS token and finish the generation prefix with `<|im_start|>assistant\n`. Native BOS is1, EOS `<|im_end|>` is4, pad is2; native model EOS accepts[4,2]. GGUF BOS1/EOS4/add_bos=true agrees. Training uses `add_special_tokens=False` after applying the template and appends `<|im_end|>` to the assistant target. There is no evidence of the old broken GGUF-to-Transformers tokenizer conversion here.

Full-epoch adapters have rank8 and GGUF `adapter.lora.alpha=16`, matching the PEFT configuration. Runtime request scale1 is consistent with that configuration. Adapter registry ID/path/hash assertions and zero-scale initialization pass. This checks metadata and selection, not numerical equivalence: a useful preflight would compare native PEFT versus exported GGUF next-token distributions on fixed non-evaluation prompts. Do not claim export scaling is numerically proven from metadata alone.

Full-epoch training reports286/286 rows, zero3072-token exclusions, and a fresh native base per route. Runtime has8192 tokens per slot; all74 paired sequences report `truncated=0`. Generation caps still matter:24sequences hit500 generated tokens and one hit1600. The old pilot similarly had21at500 and one at1600. These combined counts do not identify which member of each pair hit the cap; recorded responses omit finish_reason/usage in the Nebius runner. Preserve those fields in a future run before attributing failures to EOS or budget.

## Prompt and target distribution differences

- Training system prompts are shorter than runtime prompts; runtime additionally requests justification, full essay argumentation and no thinking narration.
- Image training orders context, question, then full-page OCR. Runtime places OCR with context and leaves the question last. The latter is preferable to match when repairing training data; original inference input remains untouched.
-111of181 image-training rows have OCR containing multiple distinct task headers. Training uses complete paper pages; actual organizer inference uses image crops. Median training OCR text length is1302characters, versus559for the examined inference OCR records. Full-page OCR may repeat the question or add neighboring tasks. OCR remains text recognition, not image semantics.
-151of282 short training targets match broad example/alternative markers. These are official valid answer variants, not151incorrect answers. Many contain slash aliases or several acceptable arguments, whereas a candidate should provide a single sufficient response. Automatic removal can destroy required multipart answers; the conservative repair below changes zero factual targets.
- Four official essay exemplars contain826,1348,721and670words and each has a single topic. Runtime asks the candidate to choose one of three topics. This is a substantial format and sample-size difference. A longer generation cap alone does not fix topic selection or factual content.

## Router label mismatch and frozen correction

The earlier router was trained against `classifier.py`'s narrow weak-label rules, while specialists used the corpus extractor's broader closed/open categories. On282 non-essay specialist rows,37route predictions disagree with their expert split:14/25closed-text and21/43closed-image rows route to open experts, with two reverse mismatches. This is label-contract inconsistency, not evidence that either weak label is universally correct.

New `router-real-specialist-aligned-v1.json` trains on248candidate-only rows using exactly the specialist category field, holding the entire2026paper out. It uses no answer/rubric/grade features. On the same38held-out2026rows, old router agreement is33/38 and new34/38(89.47%). There are no essay validation rows: the four guide essays all remain training, so essay generalization is unmeasured. Labels are heuristic, not human gold.

The new artifact is313604bytes, SHA256 `7b3c6c17031d7374f9597581b43d5b3f2e5344a2f176b72e3717738d97e9f0cf`. Old router untouched. Separate Q4/Q8 full-epoch aligned-router configs total1,062,667,698and1,789,438,386bytes. After freezing, candidate-only route inspection on2023 yields19open-image,11open-text,4closed-image,2closed-text,1essay. No settings were adjusted from this inspection or from evaluation marks. This small routing change cannot be assumed to solve the entire accuracy deficit.

## Data-only repair prepared, not trained

`data/small_track_real_training_runtime_v2/` preserves286real rows and all286assistant targets byte-for-byte. Every system prompt now matches runtime, and image prompts use context→actualOCR→originalquestion. Original page hashes are verified against OCR records. No crop was introduced because reliable task-specific crop alignment has not been verified. Source manifest remains `022b107ec04dfa7df392ab13869b2cce4eaf82b4b2a852687507e48f22b65bef`; repaired manifest is `c5e702ab09dd586094eefcf4b58c526d603e4463f303f94c53cf1d23976e5f08`.

The normalizer only chooses an official alternative when an explicit single-example question and an unambiguous bullet-list answer occur together. No current row met that conservative condition, so none was changed. Five focused tests passed; dataset checks confirm unique preservation of286real targets and unchanged source manifest.

An OPTIONAL `optional-real-essay-choice-format.jsonl` recomposes existing real guide prompts into three-topic choices and prefixes each unchanged real essay with its chosen topic number. It is not selected in any `train.jsonl` and requires review. It contains no generated historical prose, but it is a new prompt-format construction and must be described as such. Current examples consistently select topic1; diversify choice position if this optional variant is approved. No new synthetic essay was generated.

## Predeclared next ablations

1. Complete the already-running Q4/Q8 paired evaluations before selecting precision; higher precision is not assumed to help.
2. Run an adapter numerical preflight on fixed non-evaluation prompts: native PEFT versus GGUF, same exact serialized prompt, including BOS/EOS and alpha. No new training needed.
3. Test the frozen aligned router with the same base/adapters/input/decoding; label this router-only.
4. Compare original-data versus runtime-format-data training with identical fresh-base seed, updates and hyperparameters. This isolates formatting; targets and OCR image scope remain unchanged.
5. Only after manually verifying task-image boundaries, test cropped OCR independently. Preserve source PDFs/images and crop coordinates/hashes; do not guess page-to-task crops.
6. Review official answer alternatives and actual official essay exemplars before broader target changes. A bounded predeclared adapter-scale ablation can test over-strong deltas without inventing new targets, but is not an accuracy claim.

Boundary QA packets now prepared in `data/small_track_real_training_ocr_audit_v1/candidate-only-packets.jsonl`:39exact-OCR-header candidates (7closed-image,32open-image), preserving originalPNG hashes and nativePDFpage headers, no answer/rubric fields. The remaining142rows are quarantined. All39still require visual boundary review; zero are declared accepted merely from matching headers. Script: `scripts/small_track/audit_real_ocr_boundaries.py`.

## Candidate-only Luna boundary review

`scripts/small_track/luna_ocr_boundary_qa.py` defaults to a dry run that validates
all39 image hashes and packet fields. Parent may launch with `--execute --workers 4`.
The runner attaches original page images to own Codex `gpt-6-luna`; it includes no
answer keys or assistant targets. It reviews boundaries only, never history answers.
Acceptance requires no neighboring task content, a complete required source, and
unambiguous task/page association. Unknown evidence is uncertain; contradictory
acceptance fields fail validation. All started/failed calls remain recorded and are
never automatically retried. Outputs live under the audit directory's
`luna-boundaries/`. No accepted subset exists until review completes.

The packet file SHA256 is
`18c5ae462159139b9fd1e34ad59947c1fde9db827af3e7698b37be1ed265f944`.
Nine focused repair/boundary tests pass. Source scripts compile. These checks do not
establish OCR correctness or model improvement.

An optional fifth official essay is staged separately at
`data/small_track_essay_research/cke-20230111/official-five-essay-candidate.jsonl`
(SHA256 `f08d79003cd926a5af5f5801c7f1e6e3fa1cbed741a981b1b9e3080bd84dab0c`).
The original four remain unchanged. The added worked example is from a January2023
CKE supplemental guide, not the2023 examination; retain its actual publication year
and permit it only through an explicit source allowlist. It shares historical subject
matter with evaluated material, but is not an exact evaluated prompt/answer copy.
This optional file is not silently included in the frozen286-row training set.

## Completed boundary-clean dataset

All39 Luna boundary reviews reached terminal states:32 accepted,4 rejected,
3 failed without retry. The earlier142 image rows remain quarantined.
`data/small_track_real_training_boundary_clean_v3/` now contains138 rows:
25closed text,76open text,7closed image,25open image,5official essays.
Manifest SHA256:
`da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab`.
The builder `prepare_boundary_clean_training.py` refuses unfinished reviews and
existing destination folders. Its exception for the January2023 guide requires
exact row ID, PDF hash, paper ID and essay category; examination years2015/16/23/24
remain excluded. All138 assistant targets match the source bytes. No training has
been launched from this dataset. Accepted OCR still uses original complete pages;
it is not a claim that text OCR provides visual understanding. Fifteen focused
repair, boundary and exclusion tests pass.
