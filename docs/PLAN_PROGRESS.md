# Improvement track ("best progress"): plan

Score = trained − base on the same model. Organisers (Anna Olchowik, 16:46 CEST): the declared
base/trained pair matters only for this track.

**Base:** `speakleash/Bielik-11B-v2`, the *pretrained* model (no chat/instruction tuning), stored as a
4-bit NF4 checkpoint (6.66 GB, `work/checkpoints/bielik-11b-base`). Scored raw: one generic prompt,
neutral Q/A template (`configs/chat_templates/plain_pl.jinja`), no router, no RAG, no adapters.

**Trained:** the same model after our own training, inside the full harness:

| step | what | why | cost on the L40S |
|---|---|---|---|
| DAPT | LoRA next-token pass over ~10M tokens of Polish history (Wikipedia, Wikisource, Wolne Lektury, filtered FineWeb-2), merged | domain knowledge the pretrained model lacks | ~36 GB, 2–3 h |
| SFT | one LoRA (served under every route) on 133 real past-paper items + 953 Claude-written matura items | exam formats: verdict + justification, P/F, matching, letters, essays | ~30 GB, ~1 h |
| harness | router per question type, answer-sheet templates, majority vote on closed types, BM25 RAG over Polish Wikipedia | fills the format and knowledge gaps at inference | inference only |

Trained size: NF4 DAPT checkpoint (~6.7 GB) + adapter (~0.13 GB) ≤ 8.8 GB.

**Chain** (one command, resumable, each stage skipped when its output exists):
`bash infra/jobs/progress_pipeline.sh` → quantize base → base raw/routed → SFT on the base (`sft0`, an
early number) → DAPT → quantize the DAPT model → SFT on it (`sft`) → compare → `$OUT/progress/exam.env`
(CHECKPOINT, ADAPTERS) for `scripts/serve_exam.sh`. Results table: `$OUT/progress/summary.md`.

**Exam day:** base submission = `run_exam.py --mode raw` on the stored base checkpoint (BOT_CHANNEL C-019);
trained submission = `serve_exam.sh` with exam.env, then `run_exam.py --mode adapters`.

**Honesty:** nothing trains on the May 2023–2026 papers (`merge_synth.py` and `build_train_from_papers.py`
filter them); the base is scored untouched.
