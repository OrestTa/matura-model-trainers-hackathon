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

| Candidate | Source | Bytes | Decimal GB | ≤8.0 base? | +typical LoRA (~20–60 MB) ≤8.8? | Verdict |
|-----------|--------|------:|-----------:|:----------:|:-------------------------------:|---------|
| Qwen2.5-1.5B-Instruct bf16/fp16 | local `models/` | 3 098 975 924 | **3.099** | YES | YES | **OK Sunday** (size track) |
| Qwen2.5-3B-Instruct bf16/fp16 | local `models/` | 6 183 468 086 | **6.183** | YES | YES | **OK Sunday — preferred progress base** |
| Qwen2.5-7B-Instruct bf16 | HF catalog | 15 242 807 270 | **15.243** | NO | NO | **ILLEGAL as exam base** (train-only in cloud) |
| Qwen2.5-7B-Instruct-GPTQ-Int8 | local `models/` | 8 875 102 503 | **8.875** | **NO** | NO (base alone >8.0; +adapter >8.8) | **DROP — was old primary** |
| Qwen2.5-7B-Instruct-AWQ | **local `du -sb` 2026-09-26 ~14:41 CEST** | 5 582 403 508 | **5.582** | YES | YES | **OK 7B path — DOWNLOADED** |
| Qwen2.5-7B-Instruct-GPTQ-Int4 | HF catalog | 5 586 964 999 | **5.587** | YES | YES | OK alt 7B |
| Bielik-1.5B-v3.0-Instruct | HF catalog | 3 195 064 883 | **3.195** | YES | YES | OK if gated access; local stub only (10 KB) |
| Bielik-4.5B FP8-Dynamic | HF catalog | 4 897 614 776 | **4.898** | YES | YES | OK Polish-strong quant |
| Bielik-11B-v2.3-Instruct bf16 | HF catalog | 22 340 056 750 | **22.340** | **NO** | NO | **ILLEGAL — cancel DAPT/train/serve** |

### Measured adapters (box `runs/lora/`)

| Adapter | Bytes | GB |
|---------|------:|---:|
| forgehand-lora-7b-fh | 56 287 512 | 0.056 |
| forgehand-lora-7b-fh-v2 | 56 293 698 | 0.056 |
| modal-3b-v3 | 45 417 906 | 0.045 |
| modal-1.5b-v1 | 33 350 605 | 0.033 |
| qwen25-3b-history-v2 | 18 825 763 | 0.019 |

Example after-FT: AWQ 5.582 + fh-v2 0.056 = **5.638 GB** << 8.8.  
Counter-example: GPTQ-Int8 8.875 alone already **>8.0 base** and **>8.8 after FT**.

## Recommended Sunday bases + quants

1. **Primary (safe, registered-compatible):** `Qwen/Qwen2.5-3B-Instruct` bf16/fp16 (~6.18 GB) + LoRA ≤~0.06 GB -> ~6.24 GB after FT.
2. **7B quality path:** download **`Qwen/Qwen2.5-7B-Instruct-AWQ`** (~5.58 GB) as declared base; load fh LoRA if PEFT accepts AWQ (else QLoRA retrain on AWQ). GPTQ-Int4 (~5.59 GB) is equivalent fallback.
3. **Size track:** Qwen2.5-1.5B (~3.10 GB) or Bielik-1.5B if gated download completes.
4. **Polish-strong alt:** Bielik-4.5B FP8-Dynamic (~4.90 GB) — only with HF access; train LoRA on full BF16 off-exam, ship FP8 for Sunday.
5. **Do not declare:** any Bielik-11B*, full bf16 7B, or GPTQ-Int8 7B (8.875 GB).

## Forgehand fh LoRA note (critical)

`forgehand-lora-7b-fh` / `fh-v2` were trained on **full bf16** `Qwen2.5-7B-Instruct` (~15.2 GB). That bf16 checkpoint **cannot** be the Sunday declared base. Sunday path requires:

- quantized base ≤ **8.0 GB** (AWQ or GPTQ-Int4), **and**
- base + adapter ≤ **8.8 GB**.

Adapters alone (~56 MB) fit; the illegal piece is the bf16 base. MCQ/CKE numbers on bf16+LoRA are **research signal only**, not exam-legal packing.

## Jobs to cancel / stop (certain oversize for exam path)

| Job / path | Why | Action |
|------------|-----|--------|
| dapt-bielik (Bielik-11B) | base ~22.3 GB >> 8.0 | **STOP** / do not start GPU DAPT |
| train-bielik-l40s | SFT on 11B DAPT | **STOP** / dequeue |
| baselines-all2 serving bielik-11b | 11B exam-illegal; if used as submission path | **STOP** 11B serve; keep smaller models if any |
| router-ablation on bielik-11b | same | **STOP** or retarget ≤8 GB base |
| cke_7b_fh / cke_7b_fh_v2 / any eval declaring bf16 7B as base | bf16 weights ~15.2 GB | Prefer **SIGTERM** our oversize evals; keep 3B CKE |
| GPTQ-Int8 as declared Sunday base | 8.875 > 8.0 | **Demote**; switch docs to AWQ |

Claude STOP note (leave on Forgehand when SSH works): see `/workspace/size-cap-push/FORGEHAND_STOP_OVERSIZE.md`.

## Local vs Forgehand measurement status

- **Box `models/`:** measured 2026-09-26 ~14:30 CEST (table above).
- **Forgehand `/workspace/hackathon/models` + `/workspace/hf`:** SSH to session host reset at banner (kex) during this window — sizes for HF cache on VM pending reconnect; catalog numbers apply. Cancel script staged in size-cap-push.

## Related notes

- Supersedes soft-cap language in `notes/BASE_7B.md` (GPTQ-Int8 primary).
- Constraints mirrored in `notes/public_status.json` -> `constraints.max_base_disk_gb: 8.0`, `max_after_ft_gb: 8.8`.

## Enforced — executor attempt 2026-09-26 14:34 Europe/Warsaw (CEST)

### Session lookup (API via signed-in browser cookies; no Start/Stop)
- Workspace **matura-hack** id `01a0dd4b-4c82-73b7-8d65-9b217e851030`
- Session id `01a0dd4b-7179-72b4-a089-bb38eec8c18a` · class `gpu-l40s-small` · **state=running**
- API `publicIp` / UI SSH: **`<previous Forgehand host>`** (unchanged; connect cmd `ssh root@<previous Forgehand host>`)
- Forgehand session **not** stopped

### SSH from box
- TCP 22 **connects**, then **`kex_exchange_identification: Connection reset by peer`** (no SSH banner)
- Key used: `/workspace/hackathon/secrets/orest-noninteractive` · BatchMode · ConnectTimeout 15–20s
- **Result: SSH failed — no VM inventory, no process kills, no VM STOP note written by this executor**

### Alternate path
- JupyterLab `/go` issues a one-time `code=` redirect; parent dispatched **computerUse** to open JupyterLab on matura-hack to kill Bielik/oversize jobs and write `STOP_SIZE_CAP.md` on the VM
- Port `…-3000.sessions.forgehand.app` returned **502** during this window
- CLI PAT `secrets/forgehand_token` still **401**; cookie session auth works for read-only `/api/v1/me` + sessions

### Kills by this executor
- **none — could not reach VM over SSH** (oversize kill delegated to Jupyter computerUse)

### Caps reminder (do not start until measured)
- Declared base ≤ **8.0 GB**; after FT ≤ **8.8 GB**
- Do **not** start Bielik-11B bf16 / `dapt-bielik` / `train-bielik` on full 11B until quantized base `du` ≤ 8.0
- Prefer Qwen2.5-3B or quantized 7B (AWQ / GPTQ-Int4); GPTQ-Int8 (~8.875 GB) illegal as base

## Access blocked (Forgehand Train, 2026-09-26 ~14:36 Europe/Warsaw)

Tried to kill oversize jobs on matura-hack after Matura Hack size-cap ping:
- SSH `root@<previous Forgehand host>`: TCP 22 connects, then `kex_exchange_identification: Connection reset by peer`
- JupyterLab via Forgehand UI: blank / HTTP 500 on `/lab/api/workspaces`, chunk-load failures
- **No GPU inventory, no kills, no VM STOP note**
- Session left **Running** (not stopped)
- Matura Hack notified of blocker

## TRACK02 executor — AWQ on box (2026-09-26 ~14:41 Europe/Warsaw)

- Downloaded `Qwen/Qwen2.5-7B-Instruct-AWQ` -> `models/Qwen__Qwen2.5-7B-Instruct-AWQ/`
- Measured `du -sb` = **5 582 403 508** (5.582 GB) — legal Sunday 7B base
- Bare geo/CKE on AWQ: **pending GPU** (box has no NVIDIA; Forgehand SSH still kex-reset)
- GPTQ-Int8 remains demoted at 8.875 GB

## AWQ measured COMPLETE — 2026-09-26 14:37 Europe/Warsaw (CEST)

- Path: `models/Qwen__Qwen2.5-7B-Instruct-AWQ/`
- Pack (no `.cache`): **5 582 400 357 bytes = 5.582 GB** ≤ **8.0** base
- + fh LoRA ~0.056 GB -> **~5.638 GB** ≤ **8.8** after FT
- TRACK01: Modal CKE eval `cke_7b_awq_base` launched; Forgehand bootstrap staged pending SSH.

## Enforced on new VM (2026-09-26 ~14:53 Europe/Warsaw)

- New SSH: `ssh -i /workspace/hackathon/secrets/orest-noninteractive root@${FORGEHAND_HOST}`
- GPU idle (0 MiB); no Bielik/train/serve processes
- Models present: Qwen2.5-3B (~5.8G), Qwen2.5-1.5B (~2.9G); 7B dir stub 28K
- STOP notes written: `/workspace/hackathon/STOP_SIZE_CAP.md` and `/workspace/STOP_SIZE_CAP.md`
- Old IP `<previous Forgehand host>` abandoned (kex reset / dead session)
