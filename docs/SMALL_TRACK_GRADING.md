# Smallest-model history grading protocol

## Current policy — user clarification, 2026-09-26

Forgehand `gpt-6-sol` is the sole judge for all future evaluations against the
official CKE key and task-specific rubric. No Astra judging or assistant
adjudication. Work continues toward the smallest model at or above 35%; the
temporary stop was a misunderstanding, superseded by the user.

Use `scripts/small_track_second_opinion.py` (legacy filename) with protocol
`sol-official-primary-text-v3`. Its output role is `sole_primary_judge`. New
protocol runs require new output directories; historical results keep their
original identities. Uncertainty prevents a final full-paper score. The tested
Forgehand gateway accepts text only; necessary visual inspection remains
unresolved unless supported source input can be supplied to this same judge.
Never substitute Astra or silently label a text-only judgment as visual.

All five category scores, paired base/optimized results and the Ania comparison
caveat remain mandatory. Comparisons across judge protocols are not paired
improvement measurements. Historical evaluation procedures below document
past artifacts only and must not be used to launch Astra evaluation.

Protocol established 2026-09-26. The requested selection target is **at least
35% of the full official paper maximum**, ordinarily 21/60. This is the project
selection target, not a claim that extended-level history has an official pass
threshold. Score the exact serialized model and frozen harness that produced
the answers. A smaller package is promoted only on comparable completed grades.

## Data and split

Use official CKE history main-session papers and marking keys for completed
years 2017–2026. Record year, formula, exam session, original source URL,
SHA256 and local path for both PDFs. Keep formulas separate; do not merge items
from distinct formula versions into one exam. The corpus manifest's paper
maximum is authoritative after checking the printed PDF maximum. Every extracted
task and essay must appear exactly once and task maxima must sum to that maximum.
Equal sums alone do not prove complete extraction: audit task numbering, shared
sources, images and task-specific rubric alignment before inference.

* 2017–2026: development and source material for the requested 100 synthetic
  exams. These papers are already project-exposed and none is an untouched holdout.
* Additional 2015–2016 official papers: excluded from this synthesis and its SFT.
  Their prior project exposure is unknown, so describe them as held out from
  this synthesis only, not as proven uncontaminated. Freeze candidate settings
  before evaluation and track subsequent reuse for selection.

`data/small_track/{paper_id}/candidate.jsonl` contains candidate-safe questions,
context, task points, and original task-page images. `judge.jsonl` contains
matching IDs plus official solutions and rubrics; it is evaluator-only. Do not
mount keys, grader prompts, graded responses or reference answers in candidate
inference/retrieval. For text-only candidates, record image omission explicitly;
image-dependent task points remain in the denominator. A generated description
of an image is additional harness input and needs its own provenance.

## Frozen inputs

Each rubric row has `id`, `paper_id`, `task_id`, `year`, `formula`, `max_points`
(and optionally equivalent `points`), `rubric`, `official_solution`, and
`rubric_pdf`. Retain the original question and source pages alongside it. Each
answer JSONL row has the same `id` and a string `answer`; write an empty string
for generation failures. Preserve all response text and its generation status.
An absent row is missing evidence, never an implicitly correct answer.

The separate run manifest records `run_id`, model repository and immutable
revision, exact quantization, serialized required model files with byte counts
and hashes, adapters, harness version/hash, prompt/decoding settings, modality,
input-manifest hash, split, and generation errors. Runtime GPU memory estimates
do not establish serialized size. Original source hashes and this manifest
must travel with any selection claim.

## Historical Astra evaluation — superseded

Astra evaluates each answer using the original task, source text/images and
its specific official rubric. The grader must actually inspect relevant page
images when meaning depends on maps, art, charts or unreadable extracted text.
Use permitted answer variants and rubric partial credit; do not require exact
wording where the key permits equivalents. Apply conjunctions and conditions
literally: a verdict alone does not earn a justification point. Match labels
to answers for matching tasks; unordered keyword overlap cannot establish the
correct pairing. Score essays against every official criterion and any stated
minimum-length/capping rule. Explain point allocation in the rationale.

External grading remains distinct from aggregation. The Python utility does
not call Astra and does not invent grades. Only a real Astra evaluation may
use `{"kind":"astra","identity":"gpt-6-astra"}`. Human evaluations use
`{"kind":"human","identity":"reviewer identifier"}`. Rule-based checks are
not Astra marks. A rubric ambiguity, unreadable source or uncertain acceptable
variant is marked `uncertain: true` and resolved before final promotion. Keep
original and adjudicated grades as separate artifacts when they differ.

Generate an immutable-answer-bound template:

```sh
python3 scripts/small_track_judge.py template \
  --items data/small_track/PAPER/judge.jsonl \
  --answers runs/RUN/PAPER/answers.jsonl --run-id RUN \
  --output runs/RUN/PAPER/grades.astra.jsonl
```

For every template row, a real evaluator fills integer `earned_points`, sets
`status: "graded"`, provides `rationale`, `rubric_reference` (official PDF page
and task/criterion), `evaluator`, and an honest boolean `uncertain`. Preserve
all binding fields. `max_points` and `earned_points` must be JSON integers;
fractional, negative, over-maximum and boolean marks are rejected. A missing or
blank answer earns zero after evaluator review, with an explicit rationale.

```sh
python3 scripts/small_track_judge.py summarize \
  --items data/small_track/PAPER/judge.jsonl \
  --answers runs/RUN/PAPER/answers.jsonl --run-id RUN \
  --grades runs/RUN/PAPER/grades.astra.jsonl \
  --output runs/RUN/PAPER/summary.astra.json
```

The default official maximum is 60; override only from the verified paper.
An incomplete/overlapping extraction fails before any score is produced. All
marks bind to the complete rubric-file hash and exact UTF-8 answer hash.
Changed answers or keys require a new grading record. Duplicate or unknown IDs
fail closed. Retain the grade file and summary hashes for the audit trail.

## Reporting and promotion

Report earned/maximum, percentage, task count, grading coverage, uncertainty,
missing responses, evaluator and split for each year/formula separately. A
complete score is emitted only when every rubric item has a settled grade.
For partial grading, `score_percent` and `target_35_percent_met` are null;
only confirmed point bounds and explicitly provisional points are reported.
No ratio over scored rows, extrapolation, or essay omission counts as a pass.
Do not average judges into improvement or silently choose the highest judge.

Keep paired model/harness comparisons on identical input packs. Rank eligible
fully evaluated candidates by measured serialized bytes while retaining a
passing fallback. State all completed validation papers and failures, rather
than presenting the easiest paper as proof of generalization. The additional 2015–2016 results
are checks held out from this synthesis, with unknown prior contamination. Synthetic exams and SFT-set accuracy
must be labelled separately and never replace held-out official-paper grades.

## Mandatory comparison contract (2026-09-26 clarification)

Every newly evaluated real-paper score is judged by **Forgehand gpt-6-sol using
the official CKE answer key and task-specific rubric**. A paired base/optimized comparison
requires identical item IDs, question/context content, source-image representation,
full-paper maximum and grading protocol. Official keys remain outside candidate
inference. A change in source representation is a distinct experiment and must
not silently count as a same-input optimization delta.

Every score report includes all five task categories with earned/maximum and
percent: closed without images, closed with images, open without images, open
with images, essay. These labels classify the original tasks; a text-only model
may still omit the images, which must be disclosed. Zero-point categories have
undefined percentages. Uncertain categories show proposed marks explicitly.

Include the matching Ania model reference, but mark it **not comparable** until
the exact adapted inputs and 55-point subset are recovered. User-supplied
references: Bielik 4.5B 23/55 (41.8%), closed 6/11, open 15/29, essay 2/15;
Bielik 1.5B 15/55 (27.3%), closed 5/11, open 9/29, essay 1/15. Five-category
reference breakdowns are unavailable. Do not compute an improvement delta
against these unmatched references. Base-versus-optimized deltas are also
reported as **not measured** until paired artifacts have actually been graded.

## Historical independent Forgehand Sol second opinion — superseded

Every post-inference submission also receives an independent `gpt-6-sol` second
opinion through the user-specified Forgehand team endpoint. Codex Astra remains
the primary judge and adjudicates disagreements against the official CKE rubric;
never average marks. Keep the original primary grades, Sol grades and any
adjudicated grades as separate artifacts.

`scripts/small_track_second_opinion.py` reads only the frozen candidate tasks,
submitted answers and official rubric. It does not read Astra grades. It binds
each result to exact task/answer/rubric/image hashes, writes per-item state before
request dispatch, validates integer marks and persists response IDs/token usage.
Requests initially used two workers; the user subsequently authorized up to
eight workers for faster bounded batches, with190-second timeouts, with a $5 maximum
configured budget and conservative token-cost accounting. An ambiguous failed
request is never automatically retried; changed inputs require a new output
folder. Local tests cover invalid marks and malformed/incomplete responses.

The Forgehand Responses gateway was directly tested on2026-09-26: text and
structured `input_text` succeed, while `input_image` is rejected with HTTP400
schema validation. Therefore protocol `sol-official-blind-text-v2` sends exact
answers and official key/rubric text but does **not** claim visual access. It
flags source-image-dependent alternatives for Codex Astra to adjudicate using
the original pages. A missing rubric extraction falls back to the text of the
original official rubric PDF; it fails closed if that text is unavailable.
Public CKE2023 paper/key file hashes were verified against the source manifest.
