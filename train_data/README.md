# Training data we wrote ourselves

`claude_synth.jsonl`: 952 matura-style items (poziom rozszerzony, formuła 2023 shapes) written by
Claude on 2026-09-26 for the hackathon (closed LLMs are allowed for synthetic training data before the
exam). 72 topics from `scripts/gen_synthetic.py`, 13 tasks per topic (5 source analysis, 3 short open,
2 closed choice, 2 true/false, 1 matching) plus 20 essays. Sources in `context` are short paraphrases of
public historical texts. The writers were told not to read the eval set or reproduce real CKE tasks, and
`scripts/merge_synth.py` dropped 3 items too close to the headline eval set (May 2023–2026 papers); the review then dropped
one more (Communist Manifesto authors, the same question and answer as eval item 2023-05-z16.2).
Schema = gen_synthetic's: {category, topic, question, context, answer}. Use with
`infra/jobs/train.sh EXTRA_TRAIN=train_data/claude_synth.jsonl`.

`history_ext_synth.jsonl`: 3,956 items from the Grok bot's synthetic set (s3://matura-nf4-sft-20260926/train.jsonl,
9,284 rows from 250 synthetic formuła-2023 exams, the data of Nebius job me2k8), converted to gen_synthetic's schema
(topic = synthetic exam id) and run through `scripts/merge_synth.py --eval data/eval/matura_img.jsonl`: row 37
(history-synth-0001 z26, an essay topic paraphrasing May 2023 z26) dropped by hand, then 3,076 duplicates, 1,086
matching and 1,164 true/false items (answer shape) and 1 item too close to the eval set dropped. See docs/FINDINGS.md.
