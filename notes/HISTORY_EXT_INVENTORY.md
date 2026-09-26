# History Extended multi-year inventory

Updated: 2026-09-26 15:52 Europe/Warsaw  
Owner: History Ext Multi-Year

## Hard rule

`history-2023-mock-v1` remains the **only** gauge for submission quality. Multi-year packs are for broader testing + later SFT, not a substitute for that mock score.

---


## 0. Current landing status

- Three local May Formuła 2023 packs are now targeted by dedicated converters: `history-2024-05`, `history-2025-05`, `history-2026-05`.
- Repo-shipped code: `harness/history_pack.py`, pack-aware `run_official_mock*.py`, `scripts/convert_history_*_pack.py`, and `scripts/validate_history_pack.py`.
- Official quality gauge is still only `history-2023-mock-v1`; multi-year packs are local regression/SFT assets.
- Do **not** commit `data/history_extended/` packs, CKE PDFs, or past-paper pack images/json.

---

## 1. Local raw PDF inventory

Path: `data/raw/cke/` (local, untracked; fetched by `scripts/fetch_matura.py`)

| File | Size | Year | Role |
| --- | ---: | --- | --- |
| `MHIP-R0-100-2305.pdf` | 2.9 MB | 2023 | arkusz |
| `MHIP-R0-100-2305-zasady.pdf` | 423 KB | 2023 | zasady |
| `MHIP-R0-100-A-2405-arkusz.pdf` | 3.8 MB | 2024 | arkusz |
| `MHIP-R0-100-2405-zasady.pdf` | 423 KB | 2024 | zasady |
| `MHIP-R0-100-A-2505-arkusz.pdf` | 2.7 MB | 2025 | arkusz |
| `MHIP-R0-100-2505-zasady.pdf` | 406 KB | 2025 | zasady |
| `MHIP-R0-100-A-2605-arkusz.pdf` | 2.6 MB | 2026 | arkusz |
| `MHIP-R0-100-2605-zasady.pdf` | 634 KB | 2026 | zasady |

**Summary by year/session (all Formuła 2023, maj):**

| Year | Session | Code | Arkusz local | Zasady local | Karta local |
| --- | --- | --- | --- | --- | --- |
| 2023 | maj | MHIP-R0-100-2305 | yes | yes | no (CKE did not publish karta that year) |
| 2024 | maj | MHIP-R0-100-A-2405 | yes | yes | **missing** (CKE publishes it) |
| 2025 | maj | MHIP-R0-100-A-2505 | yes | yes | **missing** (CKE publishes it) |
| 2026 | maj | MHIP-R0-100-A-2605 | yes | yes | **missing** (CKE publishes it) |

Also local (pack format, not raw PDF): `data/official/history-2023-mock-v1/` — `exam.json`, `answers-template.json`, `images/`×19, zip.

Text proxy already parsed: `data/eval/matura.jsonl` = **154 items / 240 pts** (37+40+38+39) from May 2023–2026 via `scripts/fetch_matura.py`. Has `needs_image` flags; **no cropped PNGs**. Not the organiser pack format.

---

## 2. Official mock pack contract (~10 bullets)

Source: `data/official/history-2023-mock-v1/README.md` + `exam.json` + `notes/OFFICIAL_EVAL.md`

1. Layout: keep `exam.json` next to `images/`; fill `answers-template.json` → `answers.json`.
2. Top-level exam keys: `exam_id`, `title`, `source_exam_id`, `source_url`, `input_format`, `language`, `max_points`, `instructions`, `items`.
3. This mock: `exam_id=history-2023-mock-v1`, `source_exam_id=MHIP-R0-100-2305`, `input_format=separate-text-and-images-v1`, `language=pl`, `max_points=60`, **37 items**.
4. Each item: `id` (string, e.g. `"2.1"`), `group`, `max_points`, `question`, `source_text`, `images`, `answer_format`.
5. Each image: relative `path`, `source_page`, `sha256`; empty `images` = text-only item.
6. Shared sources may repeat across related items; maps/diagrams stay in PNGs (labels not re-OCRed into text).
7. Essay is item `"26"`: one of three topics; put topic number + full essay in one answer string (≥300 words).
8. Answers file top-level: only `exam_id` + `answers[{id,answer}]`; all answers Polish strings; `""` allowed; UTF-8 ≤1 MiB.
9. Upload validates schema only; organisers grade later vs CKE rubric (LLM ~every 30 min per OFFICIAL_EVAL).
10. Gauge rule (OFFICIAL_EVAL): **only** this mock judges model config quality; internal MCQ/CKE proxy scores are not the gauge.

Sample item shape (with image): `id/group/max_points/question/source_text` + `images:[{path:"images/Z01.png",source_page,sha256}]` + free-text `answer_format`.

---

## 3. Eval notes vs multi-year

| Note | Role |
| --- | --- |
| `notes/OFFICIAL_EVAL.md` | Mock-only gauge; box path for pack; final exam not released |
| `notes/HISTORY_EVAL.md` | Internal CKE headline = `matura.jsonl` May 2023–2026 Formuła 2023 (154/240); `matura_all` deferred; MCQ separate |

Multi-year mention: HISTORY_EVAL already treats 2023–2026 May as one headline set (text proxy). OFFICIAL_EVAL does **not** expand the gauge beyond the single mock pack.

---

## 4. Multi-year availability (CKE official)

### Formuła 2023 — MHIP (primary target)

Listing pages:

- 2023: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/arkusze/2023-2/
- 2024: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/arkusze/2024-2/
- 2025: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/arkusze/2025-2/
- 2026: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/arkusze/2026-2/
- Próbny sty 2026: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2023/materialy-dodatkowe/probny-egzamin-maturalny-2026/

| Year | Formula | Session | Code | Arkusz | Zasady | Karta | Local? | Official download URLs (HEAD 200 verified) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 2023 | maj | MHIP-R0-100-2305 | yes | yes | no | arkusz+zasady | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2023/Historia/MHIP-R0-100-2305.pdf) · [zasady](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2023/Historia/MHIP-R0-100-2305-zasady.pdf) |
| 2024 | 2023 | maj | MHIP-R0-100-A-2405 | yes | yes | yes | arkusz+zasady; **no karta** | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2024/Historia/MHIP-R0-100-A-2405-arkusz.pdf) · [karta](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2024/Historia/MHIP-R0-100-A-2405-karta.pdf) · [zasady](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2024/Historia/MHIP-R0-100-2405-zasady.pdf) |
| 2025 | 2023 | maj | MHIP-R0-100-A-2505 | yes | yes | yes | arkusz+zasady; **no karta** | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2025/Historia/MHIP-R0-100-A-2505-arkusz.pdf) · [karta](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2025/Historia/MHIP-R0-100-A-2505-karta.pdf) · [zasady](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2025/zasady_oceniania/MHIP-R0-100-2505-zasady.pdf) |
| 2026 | 2023 | maj | MHIP-R0-100-A-2605 | yes | yes | yes | arkusz+zasady; **no karta** | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Historia/MHIP-R0-100-A-2605-arkusz.pdf) · [karta](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Historia/MHIP-R0-100-A-2605-karta.pdf) · [zasady](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Historia/MHIP-R0-100-2605-zasady.pdf) |
| 2026 | 2023 | próbny sty | MHIP-R0-100-A-2601 | yes | yes | yes | no | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-A-2601-arkusz.pdf) · [karta](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-A-2601-karta.pdf) · [zasady](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-2601-zasady.pdf) |

**URL naming quirks:** zasady often drop the `-A-` segment (`MHIP-R0-100-2405-zasady.pdf`); 2025 zasady live under `.../2025/zasady_oceniania/`. Mirror host `static2.cke.gov.pl/EGZAMIN_MATURALNY/{Y}/Historia/` also serves some 2025/2026 arkusze+karty.

**Termin dodatkowy (czerwiec):** CKE Formuła 2023 arkusze index lists only May years (no dedicated czerwiec page found). Secondary mirrors (arkusze.pl) host June PDFs for 2023–2025 (codes like MHIP-R0-100-2306 reported for June 2023). Prefer waiting for/finding official CKE paths before converting June packs. **Poprawkowy:** history is optional extended subject — no standard August poprawka arkusz expected.

### Formuła 2015 — MHI / EHIP (secondary; convert later)

| Year | Formula | Session | Code | Arkusz | Zasady | Karta | Local? | Notes / CKE URL pattern |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2015 | 2015 | maj | MHI-R1_1P-152 | yes | yes (MHI-R1-N) | no | no | `.../2015/formula_od_2015/MHI-R1_1P-152.pdf` |
| 2016 | 2015 | maj | MHI-R1_1P-162 | yes | yes (MHI-R1-N) | no | no | `.../2016/formula_od_2015/MHI-R1_1P-162.pdf` |
| 2017 | 2015 | maj | MHI-R1_1P-172 | yes | yes | no | no | under `.../historia/` |
| 2018 | 2015 | maj | MHI-R1_1P-182 | yes | yes | no | no | |
| 2019 | 2015 | maj | MHI-R1_1P-192 | yes | yes (model) | no | no | |
| 2020 | 2015 | maj | MHI-R1_1P-202 | yes | yes (MHI-PR-202) | no | no | |
| 2021 | 2015 | maj | EHIP-R0-100-2105 | yes | yes | no | no | `.../2021/Historia/poziom_rozszerzony/` |
| 2022 | 2015 | maj | EHIP-R0-100-2205 | yes | yes | no | no | same layout |
| 2023 | 2015 | maj | EHIP-R0-100-2305 | yes | yes | no | no | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Arkusze_egzaminacyjne/2023/Historia/EHIP-R0-100-2305.pdf) |
| 2024 | 2015 | maj | EHIP-R0-100-A-2405 | yes | yes | yes | no | [arkusz](https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Arkusze_egzaminacyjne/2024/Historia/EHIP-R0-100-A-2405-arkusz.pdf) |
| 2025 | 2015 | maj | — | ? | ? | ? | no | No F2015 2025 listing page / EHIP-2505 URL found (404) |

F2015 index: https://cke.gov.pl/egzamin-maturalny/egzamin-maturalny-w-formule-2015/arkusze/  
Different structure/codes from MHIP → **defer** until Formuła 2023 packs are stable.

### Secondary indexes (not preferred for downloads)

- arkusze.pl — May + June mirrors (e.g. `historia-2024-czerwiec-matura-rozszerzona.pdf`)
- maturaminds.pl/zasoby/arkusze/historia — year index 2015–2025

---

## 5. GitHub remote check

`search_code` for `history_extended|MHIP|history-2023-mock|data/official` returned **0 hits** on both repos (likely private-repo code-search indexing lag). Manual tree/contents:

### `OrestTa/matura-model-trainers-hackathon` (private)

- Present: `scripts/fetch_matura.py` (May 2023–2026 MHIP URLs), `scripts/make_exam_package.py`, `notes/HISTORY_EXT_INVENTORY.md`, new pack-aware `harness/` helpers
- **Absent remotely:** `data/official/`, `cke_eval/`, raw PDFs (gitignored by design), converted `data/history_extended/` packs
- PDFs intentionally never committed (fetch script docstring)

### `OrestTa/tarasiuk-lab-matura-status` (public board)

- Only `README.md`, `index.html`, `scores.json`, `status.json`
- `status.json` already has track `history_ext_multi_year` + job `history-ext-pack-conversion` (RUNNING) — no MHIP PDF/pack assets

---

## 6. Recommended first 3 packs to convert

1. **history-2024-05** (`MHIP-R0-100-A-2405`) — arkusz+zasady local; same Formuła 2023 as mock; not the gauge year (safe to iterate crops); fetch missing karta if needed for closed-transfer items.
2. **history-2025-05** (`MHIP-R0-100-A-2505`) — PDFs local; zasady path quirk already handled in `fetch_matura.py`.
3. **history-2026-05** (`MHIP-R0-100-A-2605`) — PDFs local; newest May paper; mirrors mock schema most closely for “current” Formuła 2023.

Optional 4th: rebuild **history-2023-05** as a non-gauge twin and diff against organiser `history-2023-mock-v1` crops/IDs (regression QA).

Do **not** start with Formuła 2015 or June until May F2023 packs validate.

---

## 7. Blockers

| Blocker | Detail |
| --- | --- |
| Missing local karty | 2024–2026 karta PDFs published on CKE but not in `raw/cke/` (optional for pack conversion if closed answers stay in arkusz) |
| Formula mismatch | F2015 uses MHI-R1 / EHIP codes + different layout; not drop-in for MHIP converter |
| Image extraction risk | Organiser mock uses hand-cropped PNGs + sha256; auto-crop from PDF pages may miss shared sources / map labels — needs QA vs mock quality bar |
| June official URLs | Extra-session PDFs on arkusze.pl but no CKE May-index equivalent found; avoid batch download from secondary until CKE paths confirmed |
| Pack not on GitHub yet | `data/official/history-2023-mock-v1` is box-local; remote repo has inventory note + fetch script only |
| Copyright | Do not commit CKE PDF binaries; record URLs + sha256 in SOURCE.md |

---

## Proposed layout (unchanged intent)

```text
data/official/history-2023-mock-v1/   # gauge ONLY
data/history_extended/formulka-2023/history-YYYY-05/{exam.json,answers-template.json,images/,SOURCE.md,gold/}
data/history_extended/formulka-2015/  # later
```

Repo landing status: harness + converters + notes can be committed; converted packs, pack images/json, and CKE PDFs stay local/untracked.
