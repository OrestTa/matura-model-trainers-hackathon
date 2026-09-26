# Size caps (hard) — Warsaw Model Trainers / Tarasiuk Lab

Updated: 2026-09-26 ~14:35 Europe/Warsaw (CEST / UTC+2)

## Organizer constraints (user update — supersedes soft ~8.9)

| Cap | Limit | Notes |
|-----|------:|-------|
| **Max BASE on disk** | **8.0 GB** | Declared Sunday base weights only |
| **Max AFTER fine-tuning** | **8.8 GB** | Base + adapters counted as organizers require |

Previous soft OK of ~8.9 GB for GPTQ-Int8 is **revoked**. Adapters are **no longer free** relative to the after-FT budget.

## On-disk / catalog size table

Decimal GB = bytes / 1e9. Sources: local `du -sb` on box `models/`; HF tree API for catalog.

| Candidate | Source | Bytes | Decimal GB | <=8.0 base? | +typical LoRA (~20–60 MB) <=8.8? | Verdict |
|-----------|--------|------:|-----------:|:-----------:|:--------------------------------:|---------|
| Qwen2.5-1.5B-Instruct bf16/fp16 | local `models/` | 3,098,975,924 | **3.099** | YES | YES | **OK Sunday** (size track) |
| Qwen2.5-3B-Instruct bf16/fp16 | local `models/` | 6,183,468,086 | **6.183** | YES | YES | **OK Sunday — preferred progress base** |
| Qwen2.5-7B-Instruct bf16 | HF catalog | 15,242,807,270 | **15.243** | NO | NO | **ILLEGAL as exam base** (train-only in cloud) |
| Qwen2.5-7B-Instruct-GPTQ-Int8 | local `models/` | 8,875,102,503 | **8.875** | **NO** | NO (base alone >8.0; +adapter >8.8) | **DROP — was old primary** |
| Qwen2.5-7B-Instruct-AWQ | local `du -sb` 2026-09-26 ~14:41 CEST | 5,582,403,508 | **5.582** | YES | YES | **OK 7B path — DOWNLOADED** |
| Qwen2.5-7B-Instruct-GPTQ-Int4 | HF catalog | 5,586,964,999 | **5.587** | YES | YES | OK alt 7B |
| Bielik-1.5B-v3.0-Instruct | HF catalog | 3,195,064,883 | **3.195** | YES | YES | OK if gated access; local stub only (10 KB) |
| Bielik-4.5B FP8-Dynamic | HF catalog | 4,897,614,776 | **4.898** | YES | YES | OK Polish-strong quant |
| Bielik-11B-v2.3-Instruct bf16 | HF catalog | 22,340,056,750 | **22.340** | **NO** | NO | **ILLEGAL — cancel DAPT/train/serve** |

### Measured adapters (box `runs/lora/`)

| Adapter | Bytes | GB |
|---------|------:|---:|
| forgehand-lora-7b-fh | 56,287,512 | 0.056 |
| forgehand-lora-7b-fh-v2 | 56,293,698 | 0.056 |
| modal-3b-v3 | 45,417,906 | 0.045 |
| modal-1.5b-v1 | 33,350,605 | 0.033 |
| qwen25-3b-history-v2 | 18,825,763 | 0.019 |

Example after-FT: AWQ 5.582 + fh-v2 0.056 = **5.638 GB** << 8.8.  
Counter-example: GPTQ-Int8 8.875 alone already **>8.0 base** and **>8.8 after FT**.

## Recommended Sunday bases + quants

1. **Primary (safe, registered-compatible):** `Qwen/Qwen2.5-3B-Instruct` bf16/fp16 (~6.18 GB) + LoRA <=~0.06 GB -> ~6.24 GB after FT.
2. **7B quality path:** `Qwen/Qwen2.5-7B-Instruct-AWQ` (~5.58 GB) as declared base; load fh LoRA if PEFT accepts AWQ. GPTQ-Int4 (~5.59 GB) is the equivalent fallback.
3. **Size track:** Qwen2.5-1.5B (~3.10 GB) or Bielik-1.5B if gated download completes.
4. **Polish-strong alt:** Bielik-4.5B FP8-Dynamic (~4.90 GB) — only with HF access; train LoRA on full BF16 off-exam, ship FP8 for Sunday.
5. **Do not declare:** any Bielik-11B*, full bf16 7B, or GPTQ-Int8 7B (8.875 GB).

## Forgehand fh LoRA note (critical)

`forgehand-lora-7b-fh` / `fh-v2` were trained on **full bf16** `Qwen2.5-7B-Instruct` (~15.2 GB). That bf16 checkpoint **cannot** be the Sunday declared base. Sunday path requires:

- quantized base <= **8.0 GB** (AWQ or GPTQ-Int4), **and**
- base + adapter <= **8.8 GB**.

Adapters alone (~56 MB) fit; the illegal piece is the bf16 base. MCQ/CKE numbers on bf16+LoRA are **research signal only**, not exam-legal packing.

## Jobs to cancel / stop (certain oversize for exam path)

| Job / path | Why | Action |
|------------|-----|--------|
| dapt-bielik (Bielik-11B) | base ~22.3 GB >> 8.0 | **STOP** / do not start GPU DAPT |
| train-bielik-l40s | SFT on 11B DAPT | **STOP** / dequeue |
| baselines-all2 serving bielik-11b | 11B exam-illegal; if used as submission path | **STOP** 11B serve; keep smaller models if any |
| router-ablation on bielik-11b | same | **STOP** or retarget <=8 GB base |
| cke_7b_fh / cke_7b_fh_v2 / any eval declaring bf16 7B as base | bf16 weights ~15.2 GB | Prefer **SIGTERM** for oversize evals; keep 3B CKE |
| GPTQ-Int8 as declared Sunday base | 8.875 > 8.0 | **Demote**; switch docs to AWQ |

## Enforcement summary

- Hard caps are now **8.0 GB base** and **8.8 GB after FT**, with adapters counted.
- Bielik-11B lanes and bf16 7B-as-base lanes should be treated as cancelled for Sunday submission planning.
- Prefer **Qwen2.5-3B** for the safe path, or **Qwen2.5-7B AWQ / GPTQ-Int4** for the legal 7B path.
- This note intentionally omits operational access details, keys, IPs, session identifiers, and tunnel information.

## Related notes

- Supersedes soft-cap language in `notes/BASE_7B.md` (GPTQ-Int8 primary).
- Constraints mirrored in `notes/public_status.json` -> `constraints.max_base_disk_gb: 8.0`, `max_after_ft_gb: 8.8`.
