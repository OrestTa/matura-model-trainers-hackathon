# Offline OCR stage

`ocr.py` reads only candidate exam JSONL and organizer image files. It runs a
local Tesseract LSTM recognizer with Polish and English traineddata. Install
`tesseract-ocr`, `tesseract-ocr-pol`, `tesseract-ocr-eng`, and `libseccomp2` while
building the execution image; Python 3.11 or newer is required. The inference
stage never downloads weights and never calls an OCR API.

```sh
python scripts/small_track/ocr.py \
  --input candidate.jsonl --output derived/ocr-candidate.jsonl \
  --image-root /path/to/exam --artifact-dir derived/ocr-assets
```

Organizer `images[].path` is resolved beneath the exam root and checked against
its supplied SHA-256. Duplicate image bytes are recognized once. Original input
files, question, source_text, image metadata and answer_format remain unchanged.
Only the derived output's context gains clearly labeled OCR text and `ocr_refs`.
Answer-key fields are rejected before any OCR work.

`ocr-assets/manifest.json` records the original and derived file hashes, engine
version and executable hash, exact copied traineddata bytes/hashes, script hash,
per-image text hashes and extraction counts. The copied `weights/` directory is
the offline OCR model bundle. Include these bytes in total deployed-model size.
Per-image JSON files keep literal recognized text separately from original data.
The OCR bundle does not include exam answer keys.

Every Tesseract subprocess runs with OS-enforced network denial: Linux seccomp
blocks socket/connect/send syscalls; macOS uses sandbox-exec's network deny rule.
Unsupported platforms or missing isolation fail closed. This policy covers OCR;
the downstream language-model worker must independently prohibit outbound
network after preloading its dependencies and weights. Loopback model-server
traffic is a separate permitted local inference channel.

OCR recognizes visible text. It does not interpret maps, symbols, historical
photographs, chronology, or other visual semantics. Empty or incorrect text is
possible; retaining image uncertainty is required. No accuracy or score gain is
claimed until paired full-paper inference is graded by Forgehand GPT-6 Sol.

Tests: `python3 -m unittest discover -s tests/small_track -p test_ocr.py -v`.
The cloud smoke must additionally verify that a socket-creation subprocess fails
with PermissionError while actual Tesseract execution succeeds.

## Verified organizer smoke, 2026-09-26

The Modal CPU run processed all 37 candidate rows and 19 unique organizer images;
all 19 produced nonempty OCR, totaling 6,584 characters. Tesseract 5.3.0 used
8,878,606 bytes of traineddata: Polish 4,765,518 and English 4,113,088. The actual
socket-creation probe was denied while OCR completed successfully.

Saved artifact: `data/small_track/official_mock_v1/ocr-offline-v1/`. Independent
local audit verified every original candidate field other than derived context,
all 19 organizer image hashes, both copied model hashes/sizes, and output/script
hashes. The original candidate SHA-256 is
`3ecfcc62c05cc28ba668ff751fa6ce33a81e54a5cd8e958cf1ae0d2e5c6b031a`;
the derived candidate SHA-256 is
`abe9791630317612ece247d452a960549ad7dabc9c523f5717e0c726f279be67`.
This confirms execution and provenance, not OCR transcription accuracy or an
exam-score improvement. The downstream paired evaluation is separate.
