# Bielik1.5 Q4_K_M: verified five adapters versus matched base

Own Codex GPT-6-Luna, local-luna-official-v4-imagegroups. Five GET adapter IDs, paths, zero scales and weight hashes verified. Both submissions contain all37answers/60official points.

| Category | Matched base primary | Five adapters primary | Base bounds | Adapter bounds |
|---|---:|---:|---:|---:|
| closed_without_images | 0/4 (0.00%) | 1/4 (25.00%) | 0–0 | 1–1 |
| closed_with_images | 4/7 (57.14%) | 4/7 (57.14%) | 4–4 | 4–4 |
| open_without_images | 4/11 (36.36%) | 3/11 (27.27%) | 4–4 | 3–3 |
| open_with_images | 4/23 (17.39%) | 2/23 (8.70%) | 4–7 | 1–7 |
| essay | 0/15 (0.00%) | 0/15 (0.00%) | 0–0 | 0–15 |

bielik15-full-q4-base: 982,161,371bytes. Primary/provisional 12/60; settled lower bound 12/60; unresolved upper 15/60. Exact score: None. Uncertain/missing IDs: ['4.1', '14.1', '14.2']. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True}.

bielik15-full-q4-trained: 1,062,839,451bytes. Primary/provisional 10/60; settled lower bound 9/60; unresolved upper 30/60. Exact score: None. Uncertain/missing IDs: ['4.1', '15', '18', '24', '26']. Essay checks: {'points': [0, 1, 1], 'uncertainty_flags': [False, False, False], 'disagreement': True, 'first_mark_retained': True}.

Trained minus matched base: provisional -2points; conservative delta interval [-6, 18]; exact delta None.

Historical original Bielik1.5 baseline used different serving harness and local visual per-item protocol. Its difference from this matched base is not an adapter effect or controlled causal comparison.

Bielik1.5 Ania15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs/55point subset differ; five-way unavailable; no comparable numerical delta.

Only saved Luna judgments aggregated. Image metadata failures remain unresolved; no assistant marks, no averaging or selecting highest essay repeat. Bounds are worst-case unresolved-point bounds, not confidence intervals.

Own Codex plan; monetary cost unknown. No Forgehand calls.
