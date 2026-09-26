# COMMIT_AUDIT insights (Matura Hack pull, 2026-09-26 ~15:38 Europe/Warsaw)

Pulled tip `91ab4475` on matura-model-trainers-hackathon and tip `e65a47e5` on tarasiuk-lab-matura-status.

## New honest CKE result (board sync)

- Canonical `notes/TRACK01_BEST_SCORE.md` adds legal **7B AWQ + forgehand fh LoRA (offline) at 29.8% full / 32.1% text-only**.
- That is a **−7.8** regression vs bare AWQ **37.6%**; keep demoted from the Sunday pack.
- Pages board at tip `e65a47e5` still showed illegal bf16 fh lanes and missed the AWQ+fh offline stage; Matura Hack is refreshing Pages `status.json` + `scores.json` from trainers `public-board/status.json`.

## Size-cap conflicts (≤8.0 GB base / ≤8.8 GB after-FT)

| Item | Risk | Action |
|---|---|---|
| `STATUS.md` still queues `progress-*` / `score-shootout` / `baselines-0926-1254` with **Bielik-11B** lanes | Conflicts with hard cancel of 11B Sunday bases unless a measured ≤8.0 pack is the *declared* base | Keep cancel_requested; do not promote 11B until organizers confirm NF4/AWQ-on-disk counts |
| `configs/models.yaml` claims `bielik-11b` NF4 ~6.7, `bielik-11b-v3` AWQ 6.19, `gemma4-12b` QAT 7.16, `qwen3.5-9b` Q5_K_M+mmproj 7.50 | Catalog claims under 8.0; **measured** `du -sb` must win before Sunday declare | Score for research OK; ship only after measured disk |
| `configs/small_models.yaml` `qwen3.5-4b` disk_gb **9.3**, `gemma4-e2b` **10.3** (bf16 scoring copies) | Over 8.0 unless quantized pack measured | YAML already notes quant required; do not declare bf16 |
| `qwen3-vl-4b` 8.9 / `gemma3-4b` 8.6 in small_models | Over base cap | Skip as Sunday base |
| AWQ + fh LoRA after-FT ~5.64 GB | Legal size, illegal *as promotion* because score regresses | Keep listed as demoted stage |

## Still open (not new, still blocking)

- CA-01: practice base filing used harness — Sunday must file raw shipped model.
- CA-08: registration still 3B vs preferred legal 7B AWQ — Orest decide once.
- Five public CKE category columns still null (no published per-category splits).
- Mały ale wariat still blocked (no ≤3B ≥35% public CKE).

## Hygiene

- No secrets/IPs in this note.
- Claude must not refresh the public Pages board; Matura Hack owns that sync.
