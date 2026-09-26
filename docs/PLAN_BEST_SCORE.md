# Best score: Gemma 4 12B LoRA sweep (Orest, 20:00 CEST 2026-09-26)

Owner: thread "Win best matura score". Freeze by ~07:00 CEST Sunday; runbook in docs/EXAM_DAY_BEST_SCORE.md.

## Model

Gemma 4 12B QAT q4_0 GGUF + mmproj, 7.16 GB (`gemma4-12b`). Claude-graded 68.3% raw on the May 2023
mock; the organisers' deck has it at 76.7%. No other ≤8 GB model comes close (Gemma-3-27B via API
58.3%, Bielik-4.5B 40.0%), so no re-screen.

## Data (all in the repo, held-out May 2023–2026 papers excluded)

- `train_data/history_ext_synth.jsonl`: 3,956 items, the cleaned s3 synthetic set (row 37 dropped,
  dedup, filtered against the eval set; train_data/README.md)
- `train_data/claude_synth.jsonl`: 952 items
- `data/train/past_papers.jsonl` (133 real pre-2023 items) is added automatically when present
  (not in git; copy from the project files if the box has it)

## Train: one LoRA per config, one GPU each, in parallel

LoRA on `google/gemma-4-12B-it-qat-q4_0-unquantized` (the bf16 weights the q4_0 file was made from, so
the adapter matches the weights we serve), language model only (`lora_target` in models.yaml), then
converted to `adapter.gguf` by train.sh for llama-server `--lora`. ~40 GB GPU, bf16.

```bash
git pull origin main    # ≥ 08c7621
export TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF= SCORE_MODES=adapters,rag
export EXTRA_TRAIN="$PWD/train_data/history_ext_synth.jsonl $PWD/train_data/claude_synth.jsonl"
# 0. smoke, FIRST, ~10 min: must end with "GGUF LoRA: …/adapter.gguf"
NAME=gemma-lora-smoke EPOCHS=0.02 bash infra/jobs/train.sh
# then one config per GPU/box (A on the L40S, B and C on H100s):
NAME=gemma-lora-A RANK=16 LR=1e-4 EPOCHS=1 bash infra/jobs/train.sh
NAME=gemma-lora-B RANK=32 LR=2e-4 EPOCHS=1 bash infra/jobs/train.sh
NAME=gemma-lora-C RANK=16 LR=1e-4 EPOCHS=2 bash infra/jobs/train.sh
# each run writes work/adapters/gemma4-12b/: move it aside before the next run on the same box
mv work/adapters/gemma4-12b work/adapters-A     # (B, C likewise)
```

On Nebius (H100, one job per config; OUT, including `adapters/`, syncs to the bucket):

```bash
ENV="TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF= SCORE_MODES=adapters,rag \
EXTRA_TRAIN='/repo/train_data/history_ext_synth.jsonl /repo/train_data/claude_synth.jsonl'"
python infra/nebius/nb_job.py launch --job train --name gemma-lora-B --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb --env "$ENV RANK=32 LR=2e-4 EPOCHS=1"
python infra/nebius/nb_job.py launch --job train --name gemma-lora-C --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb --env "$ENV RANK=16 LR=1e-4 EPOCHS=2"
```

Step 4 of train.sh (`SCORE_MODES=adapters,rag`) answers the 154 held-out items with pictures twice on
the same box: with the adapter (`adapters` = routed prompts + RAG + LoRA) and without (`rag`, the same
harness untrained). Both `answers.jsonl` go to the grading thread; that pair is the ≥3-point test.

Adapter size at r=32 is ~0.2 GB, so base + adapter stays under the 8.8 GB limit.

## Evaluate: same harness, with and without the adapter

For each adapter, the 4 held-out papers with pictures, through the exact on-stage path, in the same
mode as the best untrained run (MODE from the untrained comparison; routed if not decided yet):

```bash
NAME=gemma-lora-A-eval OUT=runs/gemma-lora-A-eval MODEL=gemma4-12b MODE=routed \
  ADAPTERS=work/adapters-A bash infra/jobs/rehearsal.sh
```

serve_exam.sh loads the `adapter.gguf` with `--lora` (applied to every request). Commit
`runs/<name>/<paper>/answers.json` under `results/gemma4/<name>/`; the grading thread grades them
against the CKE key (Claude judge). Ship an adapter only if it beats the best untrained setup by
≥3 points over the four papers.
