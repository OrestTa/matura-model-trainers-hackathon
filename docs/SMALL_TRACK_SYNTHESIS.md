# Smallest-model synthesis and supervised fine-tuning

Work is isolated in the `small-model-track` managed worktree. This document records
implementation and measured results. The corpus now contains 100 newly generated,
synthetic-QA-accepted 60-point papers and 3,843 tasks; exact file hashes are in
`data/small_track_synthetic/final_manifest.json`. This is not exhaustive historical
fact certification or an official CKE grade.

## Inputs and separation

- Ten official history papers and keys, 2017–2026, are development/source material.
- 2015 and 2016 are excluded from all teacher prompts and all SFT. A local hashed
  seven-token overlap check rejects near copies against those evaluation papers
  as well as source papers and already accepted synthetic tasks. Prior exposure
  by earlier project work is unknown; these are reserved evaluations, not a
  proven uncontaminated external benchmark.
- Current-format point and task allocation comes from the extracted 2023–2026
  papers, each 60 points with a 15-point essay. Legacy source papers have 50
  points and are not silently relabeled as current-format exams.
- Categories: closed without images, closed with images, open without images,
  open with images, essay. Category inference from source text is approximate;
  all teacher output must match its explicit generated plan.

## Generation and quality controls

`scripts/small_track_synth.py` uses Forgehand's team-scoped text API at build time.
Credentials are read into memory only; the file is never uploaded. GPT-6 Sol
writes new questions, original educational source passages, solutions and point
rubrics. A separate GPT-6 Sol call independently critiques factual correctness, ambiguity and
key/rubric agreement. Failed reviews allow one targeted repair and re-review;
failed papers remain quarantined. A short essay gets one bounded expansion.
Local validation checks exact task IDs/categories/points, 60-point denominator,
minimum essay length, source overlap and original diagram schema.

Image tasks contain original SVG tables/diagrams, clearly described as such.
They are not claimed to be photographs, maps or historical reproductions. Full
factual transcriptions are stored separately. This is narrower than the visual
variety of an official exam and must not be treated as full vision training.

Accepted papers alone receive `exam.json`, `candidate.jsonl`, `judge.jsonl` and
`sft.jsonl`. A combined SFT file includes only papers bearing that acceptance
marker. Raw output, reviews, repair usage and failures remain auditable. Each
teacher request has explicit output limits, no unbounded retry policy, and a
persistent initial credit ledger; the worker stops within the combined incremental $35
budget (synthesis and independent judging) using a conservative outstanding-request envelope. GPU spending is a
separate allocation controlled by the orchestrator.

## Training

`scripts/small_track_train.py` trains an offline causal model with LoRA on a cloud
GPU. It refuses non-synthetic rows, splits validation by synthetic exam, masks
all prompt tokens with -100, verifies exact chat-template prefix alignment and
rejects overlength rows rather than chopping assistant answers. It requires at
least five accepted exams. Image transcription rows are excluded unless the
explicit inclusion flag is supplied; this should match an inference harness
that can obtain equivalent transcriptions offline. Official 2015/16 never enter
training or synthetic validation.

Defaults: 180 optimizer steps, rank 16, learning rate 1e-4, 2048 tokens, batch 1
with eight accumulation steps. Optional NF4 uses bitsandbytes. Checkpoints are
saved every 20 steps; the caller must select a persistent cloud-volume output.
The final manifest records resolved model revision, dataset hash, parameters,
rejected overlength IDs, validation exam IDs, metrics and adapter byte size.
A successful run is not evidence of a 35% pass; paired official-paper inference
and point-complete independent grading remain necessary.

## Live run

Generation has started with sixteen continuous parallel workers and a 100-accepted-exam target.
The initial pilot was correctly quarantined for a 290-word essay; bounded repair
was added before the large batch. The initial Luna reviewer repeatedly rejected
permissible historical shorthand and raised new minor issues after repair; it was
replaced with a separate Sol review focused on concrete material errors. Existing
original drafts are reused rather than discarded. Inspect ignored
`data/small_track_synthetic/progress.json` and `generation.log` for verified counts.
No completed fine-tuning run is claimed here.

## Public GGUF training source

The trainer accepts `--gguf-file` for a public artifact when native weights are
gated. Transformers imports supported GGUF architectures as dense weights; the
converted source and its quantized inference counterpart are distinct baseline
configurations. NF4 and GGUF import cannot be combined in this harness. Optional
`--save-merged` writes a dense merged model for downstream GGUF conversion, while
retaining the LoRA adapter. This follows the [Transformers GGUF documentation](https://huggingface.co/docs/transformers/main/quantization/gguf).

Synthetic `judge.jsonl` uses the compatibility field `official_solution`, but
its `synthetic: true` flag identifies teacher-authored references, never CKE
solutions or official grades. Codex Astra grades real exam submissions against
actual CKE rubrics outside this synthetic quality-control process.

## Astra spot check and first training launch

Astra manually checked 30 tasks across five categories in exams000/004/007.
No identified key mismatch in the sampled text-only tasks. One image task
(exam000-z4) contained unsupported Frankish area statistics. It was replaced
with a qualitative dynasty table approved by Astra; all per-exam exports and
its provenance were regenerated. This spot check is not exhaustive factual
certification of every task. Numerical diagrams attached to real historical
entities need further source verification before vision or transcription SFT;
first training excludes all image rows. Clearly hypothetical educational data
are separately described as such and should not be presented as actual records.

Compute launched a frozen 25-exam,359-text-row,80-step Bielik1.5B pilot from the
public f16 GGUF. Dense import succeeded; the first run failed at step0 because
frozen embeddings lacked input gradients under checkpointing. The trainer now
explicitly enables input gradients and compute relaunched. The relaunched80-step job completed in131.6seconds according to the compute
worker. Paired examination performance remains unverified in this document.

The same training script offers `--pair-only` to evaluate the imported dense
base and the merged adapter on identical candidate-only text, prompts, greedy
decoding,500 short-answer tokens and1600 essay tokens. Real pages are not passed
to either model in this paired text experiment. Results carry IDs, hashes,
token counts and configuration manifests for Codex/CKE grading.

## Portable pilot recipe

Run on a CUDA cloud worker with torch, transformers, peft, datasets, accelerate,
gguf and safetensors installed. Use an immutable accepted-exam snapshot and the
exact resolved model revision recorded by the worker. Example pilot command:

```sh
python scripts/small_track_train.py \
  --model second-state/Bielik-1.5B-v3.0-Instruct-GGUF \
  --gguf-file Bielik-1.5B-v3.0-Instruct-f16.gguf \
  --data /persistent/snapshots/synthetic-text.jsonl \
  --output /persistent/runs/bielik15-pilot \
  --steps 80 --save-merged
```

For a specialist adapter, add `--category closed_without_images` (or another
route). Image-route rows remain excluded unless
`--include-image-transcriptions` is explicitly supplied; that trains textual
transcriptions, not a vision encoder. Use the same immutable snapshot and
exam-separated synthetic validation. Only start additional SFT after paired
results justify it. Current artifacts retain adapter and merged weights; the
manifest separately counts only `adapter_model*.safetensors` for LoRA size.

For a same-Q4-base deployment, the official llama.cpp converter accepts
`python convert_lora_to_gguf.py --base MERGED_HF_DIR --outfile ADAPTER.gguf
--outtype f16 ADAPTER_DIR`; `--base` supplies architecture configuration, not
merged weights. Load the original Q4 file with `llama-server --lora ADAPTER.gguf`
and unchanged baseline arguments. Measure and grade this configuration before
claiming the adapter helps. [Converter source](https://github.com/ggml-org/llama.cpp/blob/master/convert_lora_to_gguf.py).

The continuous synthesis scheduler publishes on each individual completion and
checks credit state at most15seconds apart. It enforces both the authorized
combined incremental spending ceiling and at least$10 remaining available
credits, counting all concurrent team spending and reservations conservatively.

## Completed corpus and invalidated pilot

Generation completed with 100 accepted papers and 3,843 SFT rows. Original SVG
tables/diagrams remain a limited visual task distribution. Astra spot-checked 30
tasks; one unsupported numerical diagram was replaced with its approved
qualitative dynasty comparison. Image rows were excluded from the pilot SFT.

The bounded 80-step pilot completed on 25 papers / 359 text rows, but is **not a
usable improvement**: its Transformers-imported GGUF base already generated
garbled Polish and the adapter produced blank answers. Native llama.cpp inference
on the same f16 GGUF was coherent. The import/tokenizer path must pass a native-ID
smoke check before any retraining or adapter use; losses alone do not validate it.

## Native-weight SFT feasibility check, 2026-09-26

Official native safetensors were checked directly on Hugging Face. Both
`speakleash/Bielik-1.5B-v3.0-Instruct` (revision
`1907cec498b762e8223b7cffc2b8f279c417a44d`) and
`speakleash/Bielik-4.5B-v3.0-Instruct` (revision
`4b1220a9d745bdd874c44347075ef25484ef322b`) are gated and returned HTTP 401.
No Hugging Face credential was available in the supplied credential document,
relevant environment variables, standard local token files, or Modal's secret
inventory. This blocks a valid native-weight training run. No paid job was
launched for this feasibility check, and broken GGUF import was not reused.

A ready strict snapshot excludes papers whose teacher examples came from 2023
or 2024, and also excludes their point/category blueprint structures. It contains
40 synthetic exams / 564 text-only rows (320 open, 204 closed, 40 essays):
`data/small_track_synthetic/sft-no2023-no2024-strict-text.jsonl`, SHA-256
`c85f7e08effc403e3fa31f7fbe6f864c06395223bce2bcbce608335f51d2bcad`.
Excluding question/key origins alone would retain 81 exams / 1,128 text rows,
but would retain some 2023/2024 structural blueprints. No image transcription rows
are included. This source separation does not establish unknown pretraining or
prior-project contamination status.

If native access becomes available, first preload the pinned model and tokenizer
and verify native inference with three candidate-only prompts. Only after that
smoke passes, the proposed bounded pilot is 80 steps, rank 8, learning rate 5e-5,
3072-token maximum and gradient accumulation 8, using the existing assistant-only
loss and paper-separated synthetic validation. An estimated 5–15 minutes on one
H100 includes loading and training; a 20-minute cap is appropriate, not a measured
runtime promise. Paired native baseline and adapter inference with Sol-only
full-paper grading must precede any improvement claim.

## Accessible native alternative: Qwen3-4B-Instruct-2507

Official `Qwen/Qwen3-4B-Instruct-2507`, revision
`cdbee75f17c01a7cc42f958dc650907174af0554`, is ungated; an unauthenticated HEAD of
its native safetensor shard returned HTTP 200. Three native shards total
8,044,982,000 bytes. Its Qwen3 architecture is supported by the prepared native
Transformers training environment; no GGUF import is needed for future SFT.

A complete unchanged-input, text-only baseline was executed with the pinned
Unsloth Q4_K_M conversion: revision
`a06e946bb6b655725eafa393f4a9745d460374c9`, weight SHA-256
`3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`,
2,497,281,120 bytes. This is 381,605,792 bytes smaller than Bielik 4.5B Q4.
All 37 answers completed without request errors or blanks and the outputs were
coherent; the 331-word essay and occasional English answers remain for Sol to
grade. No score or SFT improvement is claimed here.

Results: `results/small_track/20260926-192723-qwen3-4b-2507-q4-canonical-b0/`.
The exact tested runner snapshot is preserved beside the answers. CPU preload
verified weight bytes/hash; inference used one L4 with provider-level
`block_network=True`, and an actual outbound connection probe failed before
inference began. The app stopped at 19:28:48 UTC with zero tasks. The pinned GGUF
and complete run remain in Modal volume `matura-qwen-independent`; the native
training shards have not been downloaded and native SFT has not been launched.
