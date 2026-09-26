# Commit audit insights

Pull audit refreshed 2026-09-26 16:14 Europe/Warsaw.

- Tips: `matura-model-trainers-hackathon` at `97a4dc6c` (C-009 joint GPU plan) and `tarasiuk-lab-matura-status` at `727d7c29` (History Ext multi-year).
- Board: public `status.json` already has AWQ 37.6%, AWQ+fh offline 29.8% demoted, and History Ext highlights. No board score refresh in this pull: no new honest CKE numbers.
- Size caps: base <= 8.0 GB, after-FT <= 8.8 GB, measured on the quantized on-disk pack. Legal: Bielik-11B 4-bit/NF4 (~6.7 GB) and Bielik-11B-v3 AWQ (~6.19 GB); G-001 withdrew the stop/cancel for those packs. Still illegal: bf16 Bielik-11B and bf16 7B. Gemma-4-12B QAT q4_0 GGUF (~7.16 GB) and claimed Qwen3.5-9B packs still need measured `du` before Sunday declare.
- BOT_CHANNEL: C-009 should ask Grok for the job list + ETA, confirm or counter-propose the joint L40S order, and say "go". G-001/G-002 already acknowledged the rules and queue behind `official_mock_bielik45_fp8`; C-009 still needs a fresh G-### reply.
- `docs/STATUS.md` is stale: several rows still say `progress-dapt` / `train-bielik-dapt` are running even though Orest paused Claude compute threads until Grok says go.
- Board ownership is unchanged: Matura Hack refreshes Pages; Claude audits only.
- Still open: registration 3B vs preferred 7B AWQ; five CKE category columns still null; "Maly ale wariat" still blocked (no <=3B >=35% public CKE).
- `notes/TRACK01_BEST_SCORE.md` still saying "never use Bielik-11B" is fine for the best-score Sunday path and is not a conflict with progress-track 4-bit 11B jobs.
