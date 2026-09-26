# Data: what we train on and what we verify on (26 Sep 2026, 22:55 CEST)

Every exam item below comes from official CKE papers (cke.gov.pl) and their official scoring rules
("zasady oceniania"). They are parsed by `scripts/fetch_matura.py`, which lists every URL in its `PAPERS` dict.
Each item's `source_url` field also holds its paper's URL. The CKE PDFs, the parsed JSONL and the page images are **never
committed** (`data/` is gitignored). They live in the project files at `/mnt/project-files/data/eval/`
(`matura.jsonl` = held-out, `matura_all.jsonl` = every parsed paper, `images/`) and on each GPU box under
`<repo>/data/eval/`. Rebuild with `python scripts/fetch_matura.py --papers all --images`.

Points: formuła 2023 papers are worth 60 each, formuła 2015 papers 50 each. "Picture" means the item needs its image.

## Summary

| Role | Set | Papers | Items | Points | Picture items | Formuła |
|---|---|---|---|---|---|---|
| **Held-out verification** (never trained on) | May 2023, 2024, 2025, 2026 main exams | 4 | 154 (4 essays) | 240 | 85 | 2023 |
| **Checkpoint selection (dev)** | January 2026 CKE mock (`probny-2026-01`) | 1 | 38 (1 essay) | 60 | 23 | 2023 |
| **SD1 training** | 2022 demo + May 2015–2024 (formuła 2015) | 11 | 309 non-essay candidates → 292 after the overlap filter | – | 151 | 2015 + 2023 |
| **Excluded (contamination)** | items whose sources overlap a held-out item | – | 23 (17 in training papers, 6 in the dev paper) | – | – | – |
| **SD2 extra** (parsed, not yet trained) | CKE mocks 2014–2024 + 2013 demo | 6 | 192 → 172 after the overlap filter | 319 | 95 | 2015 + 2023 |
| **SD2 extra** | formuła 2005 ("stara matura"), May 2005–2020, June 2012, Jan 2006, 2 mocks | 20 | 488 (20 essays) → 485 after the overlap filter | 1,000 | 157 | 2005 |
| **Dropped** | Grok synthetic `train_data/history_ext_synth.jsonl` | – | 3,956 rows | – | – | synthetic |
| **Not used any more** | Claude synthetic `train_data/claude_synth.jsonl`, `open_claude_synth.jsonl`, `essay_claude_synth.jsonl` | – | 952 + 419 + 270 | – | – | synthetic |

CKE publishes no June or August history papers at this level for formuła 2015 or 2023. The August resit covers
only basic-level compulsory subjects. See the search notes in `scripts/fetch_matura.py` (the `_EXTRA` block).

## Held-out verification: May 2023–2026 (154 items, 240 points)

| Paper | Items | Points | Picture items | Essays | Arkusz (CKE) |
|---|---|---|---|---|---|
| 2023-05 | 37 | 60 | 18 | 1 | `.../2023/Historia/MHIP-R0-100-2305.pdf` |
| 2024-05 | 40 | 60 | 25 | 1 | `.../2024/Historia/MHIP-R0-100-A-2405-arkusz.pdf` |
| 2025-05 | 38 | 60 | 21 | 1 | `.../2025/Historia/MHIP-R0-100-A-2505-arkusz.pdf` |
| 2026-05 | 39 | 60 | 21 | 1 | `.../2026/Historia/MHIP-R0-100-A-2605-arkusz.pdf` |

(`...` = `https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne`.) Graded by the Claude
master judge against the CKE zasady, with pictures viewed and the full essay criteria (`scripts/claude_judge_official.py`).
Base = 163/240. These papers are never used for training, prompts or checkpoint choice. Their items are not quoted here.

## Checkpoint selection: January 2026 CKE mock

`probny-2026-01`: 38 items, 60 points, 23 picture items, 1 essay (formuła 2023). CKE URL:
`https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-A-2601-arkusz.pdf`.
It is held out of SD1 training. The SD1 and base-with-essay-guard evals run on it first.

## SD1 training data: real past papers, self-distilled

Candidates are every non-essay item of the papers below. Items whose question + sources share >10% of their 8-word runs
with a held-out item are dropped (`results/sd1_exclude_sources.txt`).

| Paper | Formuła | Items (all) | Essays (not trained) | Excluded overlap | Picture items |
|---|---|---|---|---|---|
| pokaz-2022-03 (CKE demo) | 2023 | 35 | 1 | 7 | 14 |
| f15-2015-05 | 2015 | 31 | 1 | 1 | 14 |
| f15-2016-05 | 2015 | 32 | 1 | 0 | 14 |
| f15-2017-05 | 2015 | 34 | 1 | 1 | 15 |
| f15-2018-05 | 2015 | 36 | 1 | 1 | 20 |
| f15-2019-05 | 2015 | 35 | 1 | 0 | 21 |
| f15-2020-05 | 2015 | 38 | 1 | 0 | 16 |
| f15-2021-05 | 2015 | 36 | 1 | 1 | 21 |
| f15-2022-05 | 2015 | 36 | 1 | 5 | 23 |
| f15-2023-05 | 2015 | 5 | 1 | 0 | 2 |
| f15-2024-05 | 2015 | 2 | 1 | 1 | 1 |

(The formuła 2015 May 2023/2024 papers share most tasks with the held-out formuła 2023 papers, so `fetch_matura.py`
already keeps only 5 and 2 items from them.)

How a training row is made (`scripts/build_selfdistill.py`):
1. The base model answers each item up to 4 times, with thinking on, the exam's raw prompt and the pictures attached.
2. An answer counts as correct in one of two ways. For closed items, it must match the CKE key. For open items, it
   must have the same verdict as the key, share enough of the key's content words, and be judged full-marks by the
   base model (thinking off) against the key and rubric.
3. An item the base never gets right gets one more try with the key shown as a hint. The kept row trains without
   the hint.
4. The row keeps the base's own reasoning in the thought channel. Keys are training targets only and never appear
   in an exam prompt.

Where it lives: the Forgehand L40S at `/scratch/work/sd/selfdistill.jsonl`, plus the Nebius shards at
`/mnt/project-files/runs/sd1/`. Early rate on the L40S: 23 of the first 25 items kept (5 of them from a hinted try).

Sample items (question → key excerpt):
- `f15-2018-05-z3.1` (source analysis, 1 pt): "Rozpoznaj polityka, którego karierę przedstawiono w źródle 2., i
  uzasadnij … że nie przebiegała ona zgodnie z zasadami opisanymi w źródle 1." → "Polityk: Juliusz Cezar.
  Przykładowe argumenty: dyktatura na 10 lat …; dożywotnia dyktatura; …"
- `f15-2018-05-z5.2` (short open, 1 pt): "Wyjaśnij … dlaczego przedstawiciele ostatniej generacji Karolingów … noszą
  równocześnie ten sam tytuł królewski." → "… podziału państwa Franków w 843 r. w Verdun na trzy części: każdy z
  braci zatrzymał tytuł króla Franków."
- `pokaz-2022-03-z1.1` (closed, picture, 1 pt): "Malowidło jest wytworem cywilizacji starożytnych A. Greków
  B. Rzymian C. Egipcjan D. Sumerów." → "C"

## SD2 extra papers (found 26 Sep 2026, not yet in training)

In `scripts/fetch_matura.py` `PAPERS`, set `extra`. Every URL was checked (HTTP 200, PDF).

| Paper | Formuła | Kind | Items | Points | After overlap filter |
|---|---|---|---|---|---|
| probny-2022-12 | 2023 | CKE diagnostic mock | 36 | 60 | 29 |
| probny-2024-12 | 2023 | CKE diagnostic mock | 37 | 60 | 31 |
| f15-pokaz-2013-12 | 2015 | CKE demo | 24 | 50 | 24 |
| f15-probny-2014-12 | 2015 | CKE mock | 24 | 50 | 23 |
| f15-probny-2020-04 | 2015 | CKE mock | 33 | 49 | 28 |
| f15-probny-2021-03 | 2015 | CKE mock | 38 | 50 | 37 |
| f05-* (20 papers) | 2005 | May 2005–2020, June 2012, Jan 2006, mocks Dec 2005 / Nov 2006 | 488 | 1,000 | 485 |

## Dropped / no longer used

- `train_data/history_ext_synth.jsonl` (3,956 rows, the Grok bot's synthetic exams). Dropped on Orest's decision
  (22:14 CEST): its essays repeat stock filler sentences, 245 of them carry the generator label "zestawu
  syntetycznego nr …", and its short answers run 4–12 words. See `docs/LORA_ROOT_CAUSE.md`.
- `train_data/claude_synth.jsonl`, `open_claude_synth.jsonl`, `essay_claude_synth.jsonl` (Claude-written
  synthetic items). They were used by the earlier LoRAs, and SD1 no longer uses them.
- `data/train/past_papers.jsonl` (133 text-only past-paper items with CKE keys, `scripts/build_train_from_papers.py`).
  SD1 supersedes it by using the same papers, pictures included.

SD2 build list (non-essay, overlap-filtered, 6 extra + 20 formuła 2005 papers): `results/sd2_new_ids.txt`.
Formuła 2005 parsing (`build05` in `scripts/fetch_matura.py`): 3 key layouts (table; answers printed in the
paper; "Zadanie N. (0–k)" sections); an item is kept only if its key exists and the points match. For essays of
2006-05/2007/2008 the gold is CKE's sample essay (no rubric in the key); 30 closed rows have `reference` (a key
that is not a plain letter) and are matched like open items.
