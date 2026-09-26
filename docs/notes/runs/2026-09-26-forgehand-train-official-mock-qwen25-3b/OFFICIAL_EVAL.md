# Official Matura eval (mock)

**Guide:** https://matura-json-guide.ania-olchowik.chatgpt.site/  
**Submit:** https://warsawmodeltrainers.dev/submissions.html  
**Checked:** 2026-09-26 ~14:58 Europe/Warsaw

## Mock package

- `exam_id`: `history-2023-mock-v1` (May 2023 history extended, 37 items / 60 pts)
- Input: `separate-text-and-images-v1` - send question + source_text + PNG bytes
  (not just filenames)
- Output: `answers.json` with only `exam_id` + `answers[{id,answer}]`; Polish
  strings; essay id `"26"` >=300 words
- Box copy: `/workspace/hackathon/data/official/history-2023-mock-v1/`
  (`exam.json`, `answers-template.json`, `images/`)
- Final exam: **not released** (own exam_id later)
- Grading: LLM ~every 30 min after format check

## Size-cap reminder

Sunday base <=8.0 GB; after tune <=8.8. Prefer Qwen2.5-3B or quantized 7B for
serve/submit path.

## Box + VM layout (synced)

- Box: `/workspace/hackathon/data/official/history-2023-mock-v1/` (`exam.json`,
  `answers-template.json`, `images/` x19, zip)
- All 19 image SHA256s verified against exam.json
