# Official mock 3B run

Committed copy of the completed Qwen2.5-3B official mock run for `history-2023-mock-v1`.

## Contents

- `answers.json` — final submission payload
- `answers.summary.json` — run metadata and category split
- `answers.runlog.jsonl` — per-item timing and previews
- `../../harness/run_official_mock.py` — harness used for the run

## Key facts

- Model: `Qwen2.5-3B-Instruct`
- Backend: `transformers-hf`
- Dtype: `bf16`
- Items: **37**
- Nonempty answers: **37/37**
- Wall time: **171.2 s**
- Images: **OCR only** (`vision_pixels_fed=false`)
- Essay item `26`: **301 words** after regeneration

## Category split

- `text_open`: 10/10 nonempty
- `text_closed`: 3/3 nonempty
- `image_open`: 19/19 nonempty
- `image_closed`: 4/4 nonempty
- `essay`: 1/1 nonempty
