# Running on the Forgehand box's local disk (/scratch)

Since ~18:31 CEST on 26 Sep, /workspace and /team (NFS) on session 01a0ddc1 answer "Permission denied"
(same fault as 14:30 CEST; a session restart fixed it then). These scripts run everything from local /scratch:

- `fhput.py <local> <remote>`: copy a file onto the box through the Jupyter terminal (base64 lines; ~1 MB/s).
- `fhx.py exec '<cmd>'`: run a command on the box (cwd /scratch). Needs `fh login` first.
- `setup_box.sh`: unpack `git archive` of main into /scratch/repo, uv venv (vLLM 0.27.1 + training stack) at
  /scratch/work/venv-py312, and a llama-server wrapper that finds the CUDA libs from the pip nvidia wheels.
- `gemma_chain.sh`: best-score chain on the 4 held-out papers, serial (rehearsal.sh owns port 8000):
  gemma4-12b raw, routed, gemma4-12b-text raw (pictures A/B), gemma4-12b-think routed. Out: /scratch/out/<job_id>/.

HF cache: /scratch/hf (token in /scratch/hf/token, never committed).

## Model backups on Hugging Face (Orest, 26 Sep 21:28 CEST)

Every adapter trained on the L40S goes to a private repo under Orest's account `orestta`, for recovery.
`hf_watch.sh` runs on the box and uploads each `/scratch/work/adapters-<name>/all` once it has an
`adapter.gguf` (via `hf_up.py`, token from `/scratch/hf/token`, never in the repo).

| Adapter | HF repo (private) | What |
|---|---|---|
| A01 | `orestta/matura-gemma4-12b-lora-A01` | Gemma 4 12B QAT, single LoRA on all types, 0.1 epoch, r16, lr 1e-4, loss 1.26 |
| A1 | `orestta/matura-gemma4-12b-lora-A1` | same data, 1 epoch, r16, lr 1e-4 |
| V1 | `orestta/matura-gemma4-12b-lora-V1` | picture LoRA: 135 past-paper picture items (build_vision_train.py), train_lora.py --vision, 2 epochs, r16, lr 1e-4, loss 1.62 |

Each repo holds `adapter.gguf` (f16 GGUF LoRA for the `gemma4-12b` GGUF in configs/models.yaml)
and the PEFT `adapter_model.safetensors`, trained on `google/gemma-4-12B-it-qat-q4_0-unquantized`.
Restore: `huggingface-cli download orestta/matura-gemma4-12b-lora-A1 --local-dir work/adapters/gemma4-12b/all`.
