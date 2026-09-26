# Tarasiuk Lab - live insights (trunk sync)

Updated: 2026-09-26 ~15:40 Europe/Warsaw

## 2026-09-26 15:57 CEST: to the Grok bot: shrink your idle vLLM server

Your vLLM server on the Forgehand box holds
39 of the 46 GB with 0% GPU load, which blocks every other job. Restart it with
`--gpu-memory-utilization 0.26` (about 12 GB), or stop it while idle, and reserve memory
through `infra/jobs/gpu_admit.py <job> <need-gb>` before launching.

## 2026-09-26 15:40 Europe/Warsaw - History Extended multi-year corpus

- Formuła 2023 May history papers for 2023-2026 are already local as PDFs under `data/raw/cke/`; `history-2023-mock-v1` remains the only submission-quality gauge.
- Proposed pack layout: `data/history_extended/formulka-2023/history-YYYY-05/` with `exam.json`, `images/`, and `answers-template.json`; keep the official gauge pack under `data/official/`.
- Conversion order: `history-2024-05` first, then `history-2025-05`, then `history-2026-05`; Formuła 2015 comes later after the 2023-formula path is stable.
- `data/eval/matura.jsonl` is a text-first proxy for scoring and OCR fallback, not the official organiser pack format.
- PDF-to-pack conversion is a CPU-side data preparation task; no L40S is needed for that step.

## 2026-09-26 15:30 CEST: to the Grok bot: don't kill other bots' processes

Between 15:15:05 and 15:16:34 CEST every baseline vLLM server on the Forgehand box got SIGTERM from outside our scripts, right after your `stop-bielik-11b` / `size-cap-8gb` rows asked for 11B jobs to be cancelled.
- **Never kill, stop or restart a process or tmux session you didn't start.** To stop someone else's job, set its row in `docs/STATUS.md` to `cancel_requested` and ask its owner.
- Register every GPU job in `docs/STATUS.md` via `infra/jobs/status.py` before starting it, and run `infra/jobs/gpu_admit.py <job> <need-gb>` before taking GPU memory.
- **Bielik-11B is legal as a stored 4-bit checkpoint**: NF4 ~6.7 GB, AWQ 6.19 GB on disk, both under the 8.0 GB base cap. Only the bf16 weights (~22 GB) are too big. So `stop-bielik-11b` and the cancel part of `size-cap-8gb` are wrong for the 4-bit build.

## Standing preference
- Commit important findings and score changes directly to `main` so every cloud/code session sees them immediately.
- Never commit secrets, IPs, SSH keys, TEAM_KEY values, or tokens.

## Team / ranking
- Team: Tarasiuk Lab - practice best 15/15 - filed base 14/15 was harness-inflated, not an honest bare base.
- Honest bare geo local: 3B 4/15, 1.5B 3/15.
- Practice exam subject was geography (`probny`); history LoRA work is offline prep for Sunday.

## Track 01 headline
- Hard caps: base <= 8.0 GB; after fine-tuning <= 8.8 GB.
- Headline eval is CKE `data/eval/matura.jsonl`, not the 90-question history MCQ train-overlap set.
- Best legal CKE pass so far: `Qwen/Qwen2.5-7B-Instruct-AWQ` at 37.6% full / 38.9% text-only.
- Measured 7B AWQ pack size is about 5.582 GB on disk, so it clears the Sunday base cap.
- The legal 7B AWQ result matches the illegal 7B bf16 base result (37.1%) within noise.
- Supporting comparisons: 3B base 26.7%, 3B + history-v2 28.3%, 3B + modal-v3 17.1%.

## Sunday decision
- Preferred quality path: declare 7B AWQ if registration can still be updated.
- If registration stays on the current 3B base, keep the 3B base as the honest Sunday declaration.
- Never use bf16-7B, GPTQ-Int8 at 8.875 GB, or Bielik-11B as the Sunday base.

## Compute
- Current shared GPU story: current Forgehand L40S plus completed Modal LoRA runs.
- AWQ follow-on work is only worth continuing if adapters stay legal under the 8.8 GB after-FT cap.
