# Five specialist adapters and sixth classifier: prepared data

**Historical Qwen synthetic experiment, superseded.** The active candidate is
Bielik trained on real exam data and official exemplars; see
`SMALL_TRACK_REAL_CORPUS.md`. Do not use this document's synthetic splits or
classifier as the active Bielik training recipe.

This is a training plan and validated dataset export, not a claim that five
adapters have already been trained. One vision-capable Qwen3.5-4B base and its
projector are shared; each route gets a distinct measured LoRA delta. The sixth
model is the separately trained task-type classifier. Every unique deployed
weight file, including adapters, OCR and router, counts toward 8,800,000,000 bytes.

## Strict source separation

The selected 40 synthetic papers exclude 2023/2024 question/key teacher examples
and those years' point/category blueprints. Sources and hashes come from the
frozen selector `data/small_track_synthetic/sft-no2023-no2024-strict-text.jsonl`.
All routes share the same 32 training papers and 8 held-out synthetic papers;
no paper crosses the split. Unknown pretraining/prior-project exposure remains
unknown, so this is source-disjoint, not proven uncontaminated.

| Specialist | Train | Validation |
|---|---:|---:|
| Closed, no image | 162 | 42 |
| Closed, image + actual OCR | 160 | 40 |
| Open, no image | 256 | 64 |
| Open, image + actual OCR | 621 | 153 |
| Essay | 32 | 8 |

Files: `data/small_track_specialists/<route>/{train,validation}.jsonl` plus
candidate-only counterparts and a root `manifest.json` with SHA-256 checksums.
Targets appear only as final assistant messages. Mask all system/user/image/OCR
tokens with -100 in training; the runtime must verify this masking rather than
relying on the export's declarative policy field.

## Image requirements and completed preprocessing

974 original synthetic SVG tables/diagrams were rasterized into real PNGs
(approximately 25 MB), with original SVG and PNG hashes. These are narrow
educational diagrams: **zero natural photographs or historical maps**. A sample
was visually inspected and its Polish text was legible. Image branch messages
contain actual image references and the source context/question; they cannot be
fed to the old text-only tokenizer trainer and called vision training.

`reference_transcription` is a synthetic diagram's known text, retained separately
for provenance. It is **not OCR**, and it is excluded from the prompt. Image rows
now have `ocr_pending=false`: the bounded CPU preprocessing stage ran the local
OCR model on each PNG, preserved the original images, attached measured OCR
text/provenance, and updated dataset hashes. All 974 images produced nonempty
actual OCR, totaling 137,946 characters; the network-denial probe passed. Empty actual OCR is a valid observed result, not grounds to
substitute a reference transcription silently.

Validation commands:

```sh
python scripts/small_track/validate_specialists.py data/small_track_specialists
python scripts/small_track/validate_specialists.py data/small_track_specialists --require-ocr
```

The first passes all 1,538 rows, disjoint paper membership, candidate/key
separation, and image/file hashes. The second also passes after actual OCR preprocessing completed. It was tested
to fail before that stage, preventing unprepared image training from being
reported ready. The frozen final manifest SHA-256 is
`a786dba487cd197f84c6506685799ee230a6dcd58592c69d299545a7206565f6`.
Only 32 training essays are available: enough for a small pilot, not evidence of
broad essay competence. All labels/solutions remain synthetic QA products.

## Classifier and measured size

The prior frozen strict40 classifier remains unchanged at 841,666 bytes. Its
reported 99.674% metric is agreement with synthetic teacher route labels on the
held-out papers, not human or official classification accuracy. It uses only
question words/bigrams, supplied image presence, and point allocation.

Optional `artifacts/small_track/router-strict40-six-decimal.json` rounds log
weights to six decimals and uses compact JSON: 650,747 bytes. All 1,538 eligible
synthetic tasks retain exactly the same route prediction. This is a serialization
size reduction, not evidence of improved accuracy or universal equivalence.

`infra/small_track/configs/five-specialists-plan.json` records pinned Q3 base,
projector, OCR and selected frozen 841,666-byte router: 2,975,532,336 measured
shared bytes before adapters, leaving 5,824,467,664 bytes under the limit. The
smaller serialization remains optional and is not substituted into this pilot. Adapter byte counts
are intentionally null until real trained exports are measured. Export/runtime
compatibility and paired full-paper grading remain mandatory before deployment.
New grading follows the latest user instruction: Codex GPT-6-Luna with original
images where relevant; historical Sol results keep their original provenance.
