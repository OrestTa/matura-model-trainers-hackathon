# Bielik1.5 Q8_0: verified five adapters versus matched base

Own Codex GPT-6-Luna, local-luna-official-v4-imagegroups. Five GET adapter IDs, paths, zero scales and weight hashes verified. Both submissions contain all37answers/60official points.

| Category | Matched base primary | Five adapters primary | Base bounds | Adapter bounds |
|---|---:|---:|---:|---:|
| closed_without_images | 2/4 (50.00%) | 1/4 (25.00%) | 2–2 | 1–1 |
| closed_with_images | 4/7 (57.14%) | 4/7 (57.14%) | 4–4 | 3–5 |
| open_without_images | 5/11 (45.45%) | 4/11 (36.36%) | 5–5 | 4–4 |
| open_with_images | 5/23 (21.74%) | 3/23 (13.04%) | 5–8 | 2–3 |
| essay | 0/15 (0.00%) | 0/15 (0.00%) | 0–0 | 0–0 |

bielik15-full-q8-base: 1,708,932,059bytes. Primary/provisional 16/60; settled lower bound 16/60; unresolved upper 19/60. Exact score: None. Uncertain/missing IDs: ['1', '4.1', '4.2']. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True}.

bielik15-full-q8-trained: 1,789,610,139bytes. Primary/provisional 12/60; settled lower bound 10/60; unresolved upper 13/60. Exact score: None. Uncertain/missing IDs: ['4.1', '19']. Essay checks: {'points': [0, 0, 0], 'uncertainty_flags': [False, False, False], 'disagreement': False, 'first_mark_retained': True}.

Trained minus matched base: provisional -4points; conservative delta interval [-9, -3]; exact delta None.

Historical original Bielik1.5 baseline used different serving harness and local visual per-item protocol. Its difference from this matched base is not an adapter effect or controlled causal comparison.

Bielik1.5 Ania15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs/55point subset differ; five-way unavailable; no comparable numerical delta.

Only saved Luna judgments aggregated. Image metadata failures remain unresolved; no assistant marks, no averaging or selecting highest essay repeat. Bounds are worst-case unresolved-point bounds, not confidence intervals.

Own Codex plan; monetary cost unknown. No Forgehand calls.
