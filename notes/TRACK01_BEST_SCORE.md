# Track 01 - best legal CKE score

Updated: 2026-09-26 16:07 Europe/Warsaw

## Hard caps

- Base model on disk before fine-tuning: <= 8.0 GB
- After fine-tuning (base + adapters): <= 8.8 GB

## Headline result

- Headline eval set: `data/eval/matura.jsonl`
- Best legal CKE pass so far: `Qwen/Qwen2.5-7B-Instruct-AWQ`
  - CKE full: 37.6%
  - CKE text-only: 38.9%
  - Measured pack size: about 5.582 GB on disk
  - Status: legal Sunday base
- The legal 7B AWQ result stays ahead of every legal tuned variant committed so far.
- Latest legal tuned check: `Qwen/Qwen2.5-7B-Instruct-AWQ` + `forgehand-lora-7b-fh` (offline)
  - CKE full: 29.8%
  - CKE text-only: 32.1%
  - Status: regresses versus the bare AWQ base; do not promote as the Sunday pack

## Comparison table

| Pass | Full % | Text-only % | Sunday base status | Notes |
|---|---:|---:|---|---|
| 3B base | 26.7 | 27.4 | legal | Registered base today |
| 3B + history-v2 | 28.3 | 31.3 | legal | Small CKE lift |
| 3B + modal-v3 | 17.1 | 23.0 | legal | Regresses vs base |
| 7B bf16 base | 37.1 | 40.1 | illegal | Research signal only |
| 7B AWQ base | 37.6 | 38.9 | legal | Best legal CKE result |
| 7B AWQ + fh LoRA (offline) | 29.8 | 32.1 | legal but demoted | Regresses vs the bare AWQ base |

## Sunday quality path

- Preferred quality path: declare the bare 7B AWQ base if registration can still be updated.
- Do not promote the AWQ + fh offline LoRA pack until it beats the bare AWQ baseline on the headline CKE eval.
- If registration stays on the current 3B base, keep the 3B base as the honest Sunday declaration.
- Never use any of these as the Sunday base:
  - 7B bf16
  - 7B GPTQ-Int8 at 8.875 GB
  - Bielik-11B

## Official mock submission gauge

- Committed artifacts: `results/official_mock_awq7b/answers.json` and `results/official_mock_awq7b/answers.summary.json`
- Model / box: bare `Qwen/Qwen2.5-7B-Instruct-AWQ` on Forgehand L40S
- Exam: `history-2023-mock-v1` (official mock; sole submission gauge)
- Status: **format-complete only; not officially graded**
- Coverage: **37/37 nonempty**
- Category fill: `text_open` 10, `text_closed` 3, `image_open` 19, `image_closed` 4, `essay` 1
- Essay check: item `26` was regenerated from **291** to **811** words and stayed nonempty
- Runtime / IO notes: HF AutoAWQ serial, `wall_s` about **157.4**, `vision_pixels_fed: false`, OCR cache hits **19**
- Size rule still holds: base must be **<= 8.0 GB** on disk, so AWQ-7B remains legal
- Next size-track candidate in flight: **Bielik-4.5B FP8 (~4.9 GB)**

## Reporting rule

- The headline score is always CKE on `data/eval/matura.jsonl`.
- Do not headline the 90-question history MCQ numbers because they overlap training for some adapters and are dev-only evidence.

## Ops hygiene

- In committed notes, refer only to the current Forgehand L40S host.
- Do not commit IPs, SSH keys, TEAM_KEY values, tokens, or passwords.
