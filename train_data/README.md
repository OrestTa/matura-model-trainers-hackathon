# Training data we wrote ourselves

`claude_synth.jsonl`: 953 matura-style items (poziom rozszerzony, formuła 2023 shapes) written by
Claude on 2026-09-26 for the hackathon (closed LLMs are allowed for synthetic training data before the
exam). 72 topics from `scripts/gen_synthetic.py`, 13 tasks per topic (5 source analysis, 3 short open,
2 closed choice, 2 true/false, 1 matching) plus 20 essays. Sources in `context` are short paraphrases of
public historical texts. The writers were told not to read the eval set or reproduce real CKE tasks, and
`scripts/merge_synth.py` dropped 3 items too close to the headline eval set (May 2023–2026 papers).
Schema = gen_synthetic's: {category, topic, question, context, answer}. Use with
`infra/jobs/train.sh EXTRA_TRAIN=train_data/claude_synth.jsonl`.
