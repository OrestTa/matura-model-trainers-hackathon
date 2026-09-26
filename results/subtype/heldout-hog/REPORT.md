chosen on dev: {'closed_text': 'base', 'closed_image': 'base', 'open_text': 'base', 'open_image': 'ocr', 'essay': 'base'}

| subtype | items | raw | base (think) | optimised | setup |
|---|---|---|---|---|---|
| closed_text | 10 | 6/9 = 66.7% (3 missing) | 7/8 = 87.5% (4 missing) | 7/8 = 87.5% (4 missing) | base |
| closed_image | 19 | 8/15 = 53.3% (8 missing) | 8/14 = 57.1% (10 missing) | 8/14 = 57.1% (10 missing) | base |
| open_text | 40 | 19.5/26 = 75.0% (18 missing) | 17/33 = 51.5% (12 missing) | 17/33 = 51.5% (12 missing) | base |
| open_image | 78 | 30/54 = 55.6% (35 missing) | 36/53 = 67.9% (34 missing) | 28/49 = 57.1% (34 missing) | ocr |
| essay | 4 | 16/30 = 53.3% (2 missing) | 9/30 = 30.0% (2 missing) | 9/30 = 30.0% (2 missing) | base |
| **total** | 152 | **79.5/134 = 59.3%** | **77/138 = 55.8%** | **69/134 = 51.5%** | |

| paper | raw | base | optimised |
|---|---|---|---|
| 2023-05 | 33/54 | 33/57 | 33/57 |
| 2024-05 | 25.5/46 | 26/47 | 17/44 |
| 2025-05 | 12/22 | 12/21 | 10/19 |
| 2026-05 | 10/13 | 6/13 | 9/14 |

May 2023 in the deck's categories (deck = Ania's Gemma 4 12B bf16, images, 8k/16k thinking):
| category | deck | raw (Δ deck) | base (Δ deck) | optimised (Δ deck) |
|---|---|---|---|---|
| Closed /11 | 10 | 4/8 (-6) | 5/9 (-5) | 5/9 (-5) |
| Open /34 | 24 | 18/31 (-6) | 19/33 (-5) | 19/33 (-5) |
| Essay /15 | 12 | 11/15 (-1) | 9/15 (-3) | 9/15 (-3) |
| Text-only /28 | 24 | 21/28 (-3) | 17/27 (-7) | 17/27 (-7) |
| Text + table /30 | 26 | 21/28 (-5) | 18/29 (-8) | 18/29 (-8) |
| Total /60 | 46 | 33/54 (-13) | 33/57 (-13) | 33/57 (-13) |

## closed_text (6 base items)
- base **chosen**: +0.0 pts vs base on 6 paired items; alone 7/8 = 87.5% on 6 items; 43s median / 179s max per answer
- rag: +0.0 pts vs base on 3 paired items; alone 5/6 = 83.3% on 5 items; 56s median / 183s max per answer
- t2k: +0.0 pts vs base on 3 paired items; alone 6/9 = 66.7% on 7 items; 46s median / 166s max per answer
- v3: +0.0 pts vs base on 1 paired items; alone 2/3 = 66.7% on 3 items; 147s median / 262s max per answer
- nothink: -20.0 pts vs base on 3 paired items; alone 3/8 = 37.5% on 5 items; 98s median / 115s max per answer
## closed_image (9 base items)
- base **chosen**: +0.0 pts vs base on 9 paired items; alone 8/14 = 57.1% on 9 items; 55s median / 295s max per answer
- look_ocr: +0.0 pts vs base on 4 paired items; alone 5/8 = 62.5% on 6 items; 41s median / 175s max per answer
- v3: +0.0 pts vs base on 1 paired items; alone 1/2 = 50.0% on 1 items; 174s median / 174s max per answer
- ocr: -9.1 pts vs base on 7 paired items; alone 6/14 = 42.9% on 10 items; 40s median / 298s max per answer
- nothink: -18.2 pts vs base on 7 paired items; alone 9/21 = 42.9% on 16 items; 5s median / 111s max per answer
- t2k: -22.2 pts vs base on 6 paired items; alone 10/16 = 62.5% on 12 items; 38s median / 218s max per answer
## open_text (28 base items)
- facts **chosen**: +6.7 pts vs base on 14 paired items; alone 18/26 = 69.2% (3 ungraded) on 24 items; 53s median / 180s max per answer
- rag: +6.7 pts vs base on 14 paired items; alone 24.5/34 = 72.1% (4 ungraded) on 29 items; 58s median / 181s max per answer
- base: +0.0 pts vs base on 21 paired items; alone 17/33 = 51.5% (7 ungraded) on 28 items; 38s median / 172s max per answer
- t2k: +0.0 pts vs base on 8 paired items; alone 14.5/23 = 63.0% (3 ungraded) on 21 items; 56s median / 175s max per answer
- nothink: -5.6 pts vs base on 17 paired items; alone 22.5/32 = 70.3% on 30 items; 12s median / 119s max per answer
## open_image (44 base items)
- base **chosen**: +0.0 pts vs base on 40 paired items; alone 36/53 = 67.9% (4 ungraded) on 44 items; 57s median / 243s max per answer
- t2k: -4.8 pts vs base on 19 paired items; alone 33/60 = 55.0% (11 ungraded) on 53 items; 48s median / 194s max per answer
- ocr: -6.5 pts vs base on 26 paired items; alone 28/49 = 57.1% (8 ungraded) on 44 items; 57s median / 220s max per answer
- describe: -11.5 pts vs base on 21 paired items; alone 33/50 = 66.0% (4 ungraded) on 43 items; 66s median / 202s max per answer
- look_ocr: -12.9 pts vs base on 26 paired items; alone 31/53 = 58.5% (7 ungraded) on 48 items; 48s median / 229s max per answer
- nothink: -24.2 pts vs base on 29 paired items; alone 28/73 = 38.4% (9 ungraded) on 64 items; 10s median / 127s max per answer
## essay (2 base items)
- rubric **chosen**: +20.0 pts vs base on 1 paired items; alone 18/45 = 40.0% (1 ungraded) on 3 items; 107s median / 120s max per answer
- base: +0.0 pts vs base on 1 paired items; alone 9/30 = 30.0% (1 ungraded) on 2 items; 113s median / 113s max per answer
- plan: +0.0 pts vs base on 0 paired items; alone 7/15 = 46.7% on 1 items; 113s median / 113s max per answer
- rag_plan: +0.0 pts vs base on 0 paired items; alone 7/30 = 23.3% (1 ungraded) on 2 items; 139s median / 139s max per answer
- t2k: +0.0 pts vs base on 0 paired items; alone 0/15 = 0.0% (1 ungraded) on 1 items; 116s median / 116s max per answer
- t4k: +0.0 pts vs base on 0 paired items; alone 0/15 = 0.0% (1 ungraded) on 1 items; 107s median / 107s max per answer
