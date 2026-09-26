# Commit review log

Adversarial review of every commit on main (Claude review thread, for all agents incl. the Grok bot).
Newest first, dated. Each entry: commit(s), verdict, problems, and what was fixed or needs an owner.
Rules we review against (from docs/hackathon-brief.pdf): each model <= 8 GB on disk as run (LoRA does not count),
no internet/closed APIs at exam time, no copyrighted content in the repo (sources + fetch script instead),
SOURCE.md with the exact required line, graded work made from Fri 18:00.

## 2026-09-26 11:20 UTC: router, scoring, baselines (40155a0, 4afb7ae, 168ec23)

What they do: rule classifier routes each question to one of 7 types + general, each with its own LoRA,
prompt, token cap and answer clean-up; scoring/evaluate/run_baselines measure raw vs routed vs adapters.
Tests: 29 pass. Classifier matches the gold type on 85.7% of the 154 eval rows.

Fixed on main (this commit):
- Raw baseline used the closed types' tiny token caps (16-48 tokens), cutting off wordy base answers and
  deflating the base score, which inflates "improvement". Raw mode now uses the general route's params.
- Letter extraction upper-cased the answer, so the Polish word "a" counted as option A
  ("C – Sejm Wielki, a konkretnie…" scored 0). Now case-sensitive.
- postprocess shrank any closed-type answer to bare letters; misrouted table/justification items
  ("A – 3\nB – 2") became "A, B" and scored 0. Now only answers of 40 chars or less are rewritten.
- Qwen3 <think> blocks are stripped before post-processing and in raw mode.
- True/false and matching gave proportional partial credit; now the CKE step rule
  (3 statements/2 pts: 3 right=2, 2 right=1; 2 statements/1 pt: both or nothing).
- A single judge exception killed a whole model's run; now the row is unscored. The judge sees the
  source (first 3000 chars) and essay rubrics are no longer sent twice. Rows with only `reference` get judged.
- New summary field `pct_all_rows` = earned / points of all rows (unscored = 0), comparable to an exam score.
- PEFT backend: lock around set_adapter+generate, since the server and evaluate call it from threads.

Open, needs an owner (LARGE):
- 8 GB limit: configs/models.yaml gives vLLM full HF repos + bitsandbytes, i.e. the full bf16 weights on
  disk: Bielik-11B 22.3 GB, Qwen3-8B 16.4 GB, gemma-3-12b 24.4 GB, Bielik-4.5B 9.5 GB. Only Bielik-1.5B and
  Qwen3-1.7B (4.1 GB, not 3.4) are legal as run. The exam model must be a pre-quantized <=8 GB checkpoint
  (AWQ/GPTQ/GGUF/saved bnb-4bit) and `disk_gb` should be measured, not guessed.
- Classifier: "A. …\nB. …" layout and the word "chronologicznie" push table-filling and "rozstrzygnij" items
  into closed types (2023-05-z2.2, 2025-05-z4, 2024-05-z7). Suggest requiring "zaznacz"/"dokończ zdanie" too.
- Matching prompt asks for "1 – B" but all 4 real matching items want names ("A – Karol IX"). Prompt should
  ask for "A – <answer>" with the item's own labels.
- Keyword scoring is raw substring: "Engels lub Marks lub Lenin" gets full credit, "konsul" matches
  "prokonsul", and inflected forms ("trybunem ludowym") miss. Multi-part "1. B\n2. C" answers score 0.
- server.py: OpenAI "content parts" lists cause a 500, and the caller's system message is dropped.
- Exam machine must run with HF_HUB_OFFLINE=1 and local paths (peft_local/vLLM otherwise contact the Hub).

## 2026-09-26 11:00 UTC: first pass, commits 33ef5cf..9081fad (24 commits)

- SOURCE.md: OK. Matches the brief's required line exactly (en dash in 25–27).
- 58d5dce docs/hackathon-brief.pdf: PROBLEM (owner: Orest). Page 9 has the venue door code, and the PDF is
  organiser material that should not be republished. Deleting it from HEAD is not enough: it stays in git
  history. Before the repo is shared with the jury, either keep the repo private and give the jury read access,
  or publish a fresh repo/squashed history without the PDF.
- Code review of the remaining commits in progress; results follow below.
