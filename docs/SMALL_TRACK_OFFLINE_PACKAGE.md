# Bielik six-model offline package

This package is below the35% full-paper target. It is a reproducible experiment,
not a passing submission. It contains one learned classifier and five genuinely
trained LoRA specialists sharing one Bielik1.5B base. Two OCR language weights are
additional auxiliaries. The specialist types are closed text, closed image with
OCR, open text, open image with OCR, and essay. OCR does not understand pictures.
All caption auxiliaries were rejected; no judge participates in inference.

Exact unique deployed weight totals:

| Configuration | Bytes | DecimalGB |
|---|---:|---:|
| Bielik1.5B Q4 +five clean-v3 adapters +aligned classifier +OCR |1062667538|1.062667538|
| Same system with Q8 base |1789438226|1.789438226|

Build from the repository root (no downloads or inference):

```sh
python3 scripts/small_track/build_offline_package.py --quant q4 --output artifacts/small_track/offline-bielik-clean-v3-q4
```

The existing local package already contains the five adapters, classifier and
Polish/English OCR weights. `weights-manifest.json` records every path, exact byte
count, SHA256 and pinned recovery source. The Q4 base is public and can be restored
without private authentication. Missing private components require the authorized
HF account login; never embed a token in code or shell history.

CPU-only restoration, kept separate from exam inference:

```sh
python3 artifacts/small_track/offline-bielik-clean-v3-q4/restore.py
```

This requires `huggingface_hub` in the interpreter. Existing files are verified and
not downloaded again. Public base revision is
`second-state/Bielik-1.5B-v3.0-Instruct-GGUF@6c316d2be07dee472901150c3f3e9d4f725a4706`.
Private adapters/classifier/OCR use recovery repo `orestta/matura-small-track-recovery`
at commit `7c015a205cf7b45f0d8dc507430133ea447b3d44`. No exam keys belong in this package.
Preserve upstream Apache2.0/license attribution for Bielik and Tesseract language
assets when redistributing, using the separately backed-up license notices.

One-command offline structural smoke and official-format export:

```sh
python3 artifacts/small_track/offline-bielik-clean-v3-q4/run.py --exam data/small_track/official_mock_v1/exam.json --output artifacts/small_track/offline-bielik-clean-v3-q4-complete-dryrun
```

This runs the learned classifier, verifies original image hashes and all available
weight hashes, checks all37IDs/60points, writes an OCR/adapter route plan, and exports
`answers.DRY_RUN.EMPTY.json`. That file deliberately contains empty answers: it is
schema verification only and must never be represented as model output. Missing
weights are reported explicitly. Actual Tesseract execution is not part of this
structural dry run; offline OCR was previously separately verified on19images.

Explicit inference is separate and has not been tested through this new launcher.
It requires Linux, Python3.11+, local Tesseract5 binary with Polish/English traineddata,
libseccomp, a CUDA-capable GPU, and the previously tested llama.cpp server binary
version0.5.0-dev81bc6b8 with SHA256
`efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf`.
The package uses the supplied localOCR weights rather than downloading them.
For an independently approved run with sufficient shared capacity:

```sh
timeout --signal=TERM --kill-after=15s 900s python3 PACKAGE/run.py --exam ORGANIZER/exam.json --output NEW_OUTPUT --run --server /ABSOLUTE/PATH/llama-server
```

The launcher requires6GiB freeGPU and6GiB available hostRAM, classifies first,
OCRs only classified image routes, preserves original images/questions, verifies
all five server LoRA IDs/paths, sets global adapters to zero, then selects one per
request. It uses port18935 on loopback, seed42, greedy decoding,500short/1600essay
caps and no voting. Outbound server connections/UDP are denied by seccomp and
probed. Client proxies and redirects are disabled. Only the owned server child is
terminated on exit. `answers.jsonl` persists per-item outputs, errors and token
usage; `answers.json` uses exact organizer IDs. A nonzero error count must not be
reported as a successful complete exam run.

The source corpus is the frozen138real rows with exact-source allowance for one
2023teaching-guide essay; evaluation papers and reserved holdouts remain excluded.
Training manifest SHA256:
`da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab`.
No synthetic historical targets or caption-generated evidence are included.

## Verified complete local Q4 restoration

The public pinned Q4 base has now been downloaded into the local package. All nine
weight files (one shared base, five adapters, one classifier, two OCR language
files) pass exact SHA256 and byte verification; no weights are missing.
Weights manifest SHA256:
`034420954f1c29cafa063829b0205eef2b77f7f3c71f538524172f284b00dae5`.
The completed structural dry run is saved at
`artifacts/small_track/offline-bielik-clean-v3-q4-complete-dryrun/`:37unique taskIDs,
60points, original image hashes, learned routing and strict empty-answer export
verified. No GPU inference ran during restoration. This completes local learned
weight recovery, not installation of a platform-specific llama/Tesseract runtime
or demonstration of35% accuracy.
