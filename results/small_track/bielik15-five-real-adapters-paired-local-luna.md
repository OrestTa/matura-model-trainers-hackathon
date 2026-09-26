# Bielik1.5 Q4_K_M: verified five adapters versus matched base

Own Codex GPT-6-Luna, local-luna-official-v3-imagegroups. Five GET adapter IDs, paths, zero scales and weight hashes verified. Both submissions contain all37answers/60official points.

| Category | Matched base primary | Five adapters primary | Base bounds | Adapter bounds |
|---|---:|---:|---:|---:|
| closed_without_images | 0/4 (0.00%) | 1/4 (25.00%) | 0–0 | 1–1 |
| closed_with_images | 4/7 (57.14%) | 4/7 (57.14%) | 4–4 | 3–4 |
| open_without_images | 5/11 (45.45%) | 3/11 (27.27%) | 5–5 | 3–3 |
| open_with_images | 2/23 (8.70%) | 1/23 (4.35%) | 2–4 | 1–4 |
| essay | 0/15 (0.00%) | 0/15 (0.00%) | 0–0 | 0–0 |

bielik15-five-base: 982,161,371bytes. Primary/provisional 11/60; settled lower bound 11/60; unresolved upper 13/60. Exact score: None. Uncertain/missing IDs: ['4.1', '4.2']. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True}.

bielik15-five-trained: 1,062,839,483bytes. Primary/provisional 9/60; settled lower bound 8/60; unresolved upper 12/60. Exact score: None. Uncertain/missing IDs: ['4.1', '4.2', '13.1', '13.2']. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True}.

Trained minus matched base: provisional -2points; conservative delta interval [-5, 1]; exact delta None.

Historical original Bielik1.5 baseline used different serving harness and local visual per-item protocol. Its difference from this matched base is not an adapter effect or controlled causal comparison.

Bielik1.5 Ania15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs/55point subset differ; five-way unavailable; no comparable numerical delta.

Only saved Luna judgments aggregated. Image metadata failures remain unresolved; no assistant marks, no averaging or selecting highest essay repeat. Bounds are worst-case unresolved-point bounds, not confidence intervals.

Own Codex plan; monetary cost unknown. No Forgehand calls.
