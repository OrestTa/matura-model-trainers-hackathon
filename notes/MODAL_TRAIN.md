# Modal LoRA training (matura hackathon)

Workspace: `orestta` - Volume: `model-training-workshop` (prefix `matura/`)
Script: `harness/modal_lora_train.py`
Token: already at `~/.modal.toml` (do not commit).

## What it does

- Image: torch 2.5.1 + transformers 4.46 + peft 0.13 + accelerate (Python 3.11)
- Data: mounts local `data/history/history_mcq_v1.jsonl` (90 MCQs)
- Base models from HF: `Qwen/Qwen2.5-3B-Instruct` or `Qwen/Qwen2.5-1.5B-Instruct`
- LoRA: r=16, alpha=32, targets `q/k/v/o_proj`, bf16, lr=2e-4, max_steps~=300 / epochs=3
- GPU: L4 (cost-first; change `gpu=` in the `@app.function` decorator for A10G/H100)
- Writes adapter + `train_meta.json` + `live.log` to volume:
  - `matura/lora-3b-v3/`
  - `matura/lora-1.5b-v1/`

## Re-run

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /workspace

# 3B
modal run harness/modal_lora_train.py --model-size 3b --max-steps 300 --epochs 3

# 1.5B (size track)
modal run harness/modal_lora_train.py --model-size 1.5b --max-steps 300 --epochs 3
```

Optional flags: `--lr 0.0002 --lora-r 16 --lora-alpha 32`.

## Download adapters to the box

```bash
mkdir -p runs/lora/modal-3b-v3 runs/lora/modal-1.5b-v1
modal volume get model-training-workshop matura/lora-3b-v3 runs/lora/modal-3b-v3 --force
modal volume get model-training-workshop matura/lora-1.5b-v1 runs/lora/modal-1.5b-v1 --force
```

Or copy individual files:

```bash
modal volume ls model-training-workshop matura/lora-3b-v3
```

## Monitor

```bash
modal app list
# dashboard URL printed at start of `modal run`
tail -f runs/lora/modal-3b-v3-train.log
modal billing summary
```

## Notes

- Prefer L4/A10G; only bump to H100 if L4 is too slow.
- If billing/spend-limit errors appear, stop and check Usage & billing.
- Bielik is gated - skip; Qwen only.
- Do not commit secrets / TEAM_KEY / `.modal.toml`.
