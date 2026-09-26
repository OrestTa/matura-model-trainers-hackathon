# History Extended multi-year inventory

Updated: 2026-09-26 ~15:40 Europe/Warsaw
Owner: History Ext Multi-Year bot

## Hard rule

`history-2023-mock-v1` remains the only gauge for submission quality. Multi-year packs are for broader testing and later SFT, not a substitute for that mock score.

## Official pack contract

From the organiser mock and repo notes:

- Layout: `exam.json` + `images/*.png` + `answers-template.json`
- Top-level exam fields: `exam_id`, `title`, `source_exam_id`, `source_url`, `input_format` (`separate-text-and-images-v1`), `language`, `max_points`, `instructions`, `items`
- Each item: `id` (string), `group`, `max_points`, `question`, `source_text`, `images[{path,source_page,sha256}]`, `answer_format`
- Answers file: `{"exam_id","answers":[{"id","answer"}]}` with Polish string answers; empty `""` is allowed
- Official mock: May 2023 = `MHIP-R0-100-2305`, 37 items / 60 points, 19 PNGs, 23 items with images

## Local raw PDFs

Repo-local raw inputs live under `data/raw/cke/` and are fetched by `scripts/fetch_matura.py`.

| Year | Session | Code | Arkusz | Zasady | Local |
| --- | --- | --- | --- | --- | --- |
| 2023 | maj | MHIP-R0-100-2305 | yes | yes | yes (also official mock pack) |
| 2024 | maj | MHIP-R0-100-A-2405 | yes | yes | yes |
| 2025 | maj | MHIP-R0-100-A-2505 | yes | yes | yes |
| 2026 | maj | MHIP-R0-100-A-2605 | yes | yes | yes |

Download base for Formuła 2023:
`https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/{YYYY}/Historia/`

## Already-parsed text proxy (not pack format)

`data/eval/matura.jsonl` covers the May 2023-2026 Formuła 2023 headline set via `scripts/fetch_matura.py`. It is useful as a text-first proxy, OCR fallback seed, and key source, but it is not the organiser pack format because it does not preserve the final `exam.json` package structure or separate image payloads.

## Formuła 2015 corpus

Older CKE codes differ (`MHI-R1_1P-YY2`; 2022 uses `EHIP-R0-100-2205`). The Formuła 2015 papers should be converted only after the Formuła 2023 path is stable. They are not the first conversion target.

## Proposed folder layout

```text
data/official/
  history-2023-mock-v1/          # gauge only; do not overwrite
  MANIFEST.md                    # year/session/status table
data/history_extended/           # multi-year packs, not the gauge
  README.md
  formulka-2023/
    history-2024-05/
      exam.json
      answers-template.json
      images/
      SOURCE.md                  # CKE URLs + PDF sha256; PDFs stay untracked
      gold/                      # optional zasady-derived keys for local grading
    history-2025-05/
    history-2026-05/
    history-2023-05/            # optional non-gauge twin for regression checks
  formulka-2015/                 # later
    history-YYYY-05/
  raw/                           # optional PDF mirror; gitignored
```

## Conversion and evaluation plan

1. Validate the official mock pack as the schema gold standard.
2. Convert `history-2024-05` first into `data/history_extended/formulka-2023/history-2024-05/`.
3. Convert `history-2025-05`.
4. Convert `history-2026-05`.
5. Revisit Formuła 2015 only after the 2023-formula packs are stable.

Implementation notes:

- Reuse PDF/image extraction logic from `scripts/fetch_matura.py`, but emit the official package layout with cropped item images.
- Keep `history-2023-mock-v1` under `data/official/` as the only submission gauge.
- `scripts/make_exam_package.py` is useful as a rehearsal-oriented reference, but the multi-year corpus should match the official mock contract rather than its current minimal `work/packages/` output.
- PDF-to-pack conversion is CPU work; no L40S is needed.

## Risks and guardrails

- Auto-cropped images may need manual QA against the organiser mock quality bar.
- Open-ended grading still needs judge support or curated `gold/` data for more than closed items.
- Do not commit CKE PDF binaries; keep PDFs untracked and record sources and hashes in text files only.
- If text-plus-image packs are ever pushed, settle the LICENSE/SOURCE policy first.
- Do not commit secrets, IPs, SSH keys, TEAM_KEY values, tokens, or passwords.
