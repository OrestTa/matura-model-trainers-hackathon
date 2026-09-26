# History extended multi-year eval (non-gauge)

Updated: 2026-09-26 15:52 Europe/Warsaw

## Gauge rule (do not blur)

**Only** `history-2023-mock-v1` submissions count as the official quality gauge.  
Path: `data/official/history-2023-mock-v1/`  
Submit via the organisers’ mock upload; see `notes/OFFICIAL_EVAL.md`.

Packs under `data/history_extended/` are for broader year coverage, regression, and later SFT — **not** a substitute for that mock score.

## Packs (Formuła 2023, maj)

| Pack | Path | Items | Role |
| --- | --- | ---: | --- |
| Official gauge | `data/official/history-2023-mock-v1/` | 37 | **ONLY submission-quality gauge** |
| 2024-05 | `data/history_extended/formulka-2023/history-2024-05/` | 40 | extended eval / SFT |
| 2025-05 | `data/history_extended/formulka-2023/history-2025-05/` | 38 | extended eval / SFT |
| 2026-05 | `data/history_extended/formulka-2023/history-2026-05/` | 39 | extended eval / SFT |

Validate any pack (does not mutate contents):

```bash
python scripts/validate_history_pack.py \
  data/history_extended/formulka-2023/history-2024-05
```

## Runners

Shared loader: `harness/history_pack.py`  
HF local: `harness/run_official_mock.py`  
vLLM HTTP: `harness/run_official_mock_vllm.py`

CLI:

- `--pack-dir` — pack root (default: official mock path)
- `--exam-id` — optional; must match pack `exam_id`
- `--exam-dir` — deprecated alias for `--pack-dir`
- `--dry-run` — load pack + write empty `answers.json`; **no model / no GPU**
- Output contract unchanged: Polish `answers.json` with only `{exam_id, answers:[{id,answer}]}`
- Images: PNG bytes loaded from item paths; text models get OCR/caption fallback if OCR unavailable or file missing (same spirit as the official mock)

### Official mock (gauge) — default pack

```bash
python harness/run_official_mock.py \
  --out runs/official_mock/answers.json \
  --model /path/to/legal-base \
  # --pack-dir defaults to data/official/history-2023-mock-v1
```

### Multi-year pack (e.g. 2024) — not a gauge

```bash
python harness/run_official_mock.py \
  --pack-dir data/history_extended/formulka-2023/history-2024-05 \
  --exam-id history-2024-05 \
  --out runs/history_ext/2024-05/answers.json \
  --model /path/to/legal-base
```

### Dry-run / template fill (no GPU)

```bash
python harness/run_official_mock.py \
  --pack-dir data/history_extended/formulka-2023/history-2024-05 \
  --dry-run \
  --out runs/history_ext/2024-05/dry_answers.json
```

Same flags work on `run_official_mock_vllm.py` (add `--base-url` / `--model` for real runs; `--dry-run` skips the server).

## Size-cap reminder

- Sunday **base ≤ 8.0 GB**; after tune **≤ 8.8 GB** (see `notes/SIZE_CAP_8GB.md`).
- Prefer Qwen2.5-3B bf16 or legal 7B quants (AWQ / GPTQ-Int4).
- **No Bielik-11B bf16** as Sunday base (illegal size).

## Notes

- Essay item id is usually `"26"`; **2025** uses `"25"` (15 pts / trzy tematy). Harness detects essay by points / prompt text, not a hard-coded id.
- Do not mutate pack contents or the official mock when evaluating.
- Do not treat multi-year scores as submission readiness.
