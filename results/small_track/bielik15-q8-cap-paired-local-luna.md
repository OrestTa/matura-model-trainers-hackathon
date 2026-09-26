# Bielik1.5 Q8_0: output-cap ablation

Same base-only answering model, candidate input, classifier/OCR, serving binary81bc6b8, seed42, temperature0. Only output caps500/1600 versus1000/2400 differ. Earlier Nebius serving binary and concurrency differ; no causal comparison across harnesses.

Both arms ship 1,708,932,059bytes. Full37-pair inference gate: True.

| Category | Control primary | Raised primary | Control bounds | Raised bounds |
|---|---:|---:|---:|---:|
| closed_without_images | 1/4 (25.00%) | 1/4 (25.00%) | 1–1 | 1–1 |
| closed_with_images | 3/7 (42.86%) | 2/7 (28.57%) | 3–3 | 2–2 |
| open_without_images | 3/11 (27.27%) | 2/11 (18.18%) | 3–3 | 2–3 |
| open_with_images | 4/23 (17.39%) | 5/23 (21.74%) | 4–6 | 5–5 |
| essay | 0/15 (0.00%) | 1/15 (6.67%) | 0–0 | 0–15 |

bielik15-cap-control: primary/provisional 11/60; settled lower 11/60; unresolved upper 13/60. Exact: None. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True, 'sources': ['/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-control/essay_repeats/26-r1.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-control/essay_repeats/26-r2.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-control/essay_repeats/26-r3.json']}.

bielik15-cap-raised: primary/provisional 11/60; settled lower 10/60; unresolved upper 26/60. Exact: None. Essay checks: {'points': [1, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': True, 'first_mark_retained': True, 'sources': ['/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-raised/essay_repeats/26-r1.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-raised/essay_repeats/26-r2.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-cap-grades-v4/bielik15-cap-raised/essay_repeats/26-r3.json']}.

Raised minus control: {'primary_provisional_points': 0, 'conservative_interval_points': [-3, 15]}.

Bielik1.5 Ania15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs/55point subset differ; five-way unavailable; no comparable numerical delta.

Saved Luna judgments only. Keep first essay mark and flag repeat disagreement. Missing or image-metadata-invalid marks unresolved; worst-case bounds are not expected scores. No assistant adjudication.

Own Codex plan; monetary cost unknown. Zero Forgehand grading requests.
