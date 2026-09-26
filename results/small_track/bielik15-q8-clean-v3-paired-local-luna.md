# Bielik1.5 Q8_0: clean-v3 adapters versus matched base

Same base answering model, original candidate input with aligned classifier/OCR, serving run, seed42, temperature0 and caps500/1600. Only explicit adapter scales differ: all zero versus selected trained route at one. Clean138-trained adapters and aligned router differ from historical runs; no causal attribution across harnesses.

Base ships 1,708,760,306bytes; trained package 1,789,438,226bytes. Full37-pair inference gate: True.

| Category | Matched base primary | Trained primary | Base bounds | Trained bounds |
|---|---:|---:|---:|---:|
| closed_without_images | 1/4 (25.00%) | 2/4 (50.00%) | 1–1 | 2–2 |
| closed_with_images | 2/7 (28.57%) | 4/7 (57.14%) | 2–2 | 3–5 |
| open_without_images | 4/11 (36.36%) | 4/11 (36.36%) | 4–4 | 4–4 |
| open_with_images | 4/23 (17.39%) | 3/23 (13.04%) | 4–5 | 3–3 |
| essay | 0/15 (0.00%) | 0/15 (0.00%) | 0–0 | 0–0 |

bielik15-clean-v3-base: primary/provisional 11/60; settled lower 11/60; unresolved upper 12/60. Exact: None. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True, 'sources': ['/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-base/essay_repeats/26-r1.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-base/essay_repeats/26-r2.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-base/essay_repeats/26-r3.json']}.

bielik15-clean-v3-trained: primary/provisional 13/60; settled lower 12/60; unresolved upper 14/60. Exact: None. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True, 'sources': ['/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-trained/essay_repeats/26-r1.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-trained/essay_repeats/26-r2.json', '/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon/results/small_track/local-luna-bielik15-clean-v3-grades-v4/bielik15-clean-v3-trained/essay_repeats/26-r3.json']}.

Trained minus matched base: {'primary_provisional_points': 2, 'conservative_interval_points': [0, 3]}.

Bielik1.5 Ania15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs/55point subset differ; five-way unavailable; no comparable numerical delta.

Saved Luna judgments only. Keep first essay mark and flag repeat disagreement. Missing or image-metadata-invalid marks unresolved; worst-case bounds are not expected scores. No assistant adjudication.

Own Codex plan; monetary cost unknown. Zero Forgehand grading requests.

Task19 consistency flag: the saved Luna mark remains1, but its rationale contradicts its own point-count rule. Treat the full2point item as unresolved: trained bounds12–14/60, delta0–3. No replacement mark or further call. Both upper bounds remain below35%.
