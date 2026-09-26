# Sunday: honest base then tuned

Filed practice `probny` base (14/15) used geo harness - do NOT treat as untouched baseline for progress.

Local bare estimate (Qwen2.5-3B, no det/RAG): 4/15 -> `runs/official/probny-bare-model-local.json`
1.5B bare: 3/15

On final unlock:
1. `kind=base` - model only via `bare_geo_eval`-style / k3exam with `--bare` (no try_deterministic, no RAG)
2. `kind=tuned` - full geo_solver + local RAG + history LoRA if theme fits
3. Never call external AI/web during answering; organizer submit RPC OK
