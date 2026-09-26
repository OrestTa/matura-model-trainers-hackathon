#!/usr/bin/env bash
# Scores every model in configs/models.yaml on the eval set and draws the charts.
# Run on any GPU box: `bash infra/jobs/baselines.sh` (see infra/jobs/common.sh). Env:
#   MODELS=all               keys from configs/models.yaml
#   MODES=raw,routed         baseline modes
#   HF_TOKEN                 needed for gated models (Gemma)
#   JUDGE_HF=Qwen/Qwen3-32B  open model that grades open answers (last 2 GPUs); "" = no judge
#   JUDGE_GB=18              on a 1-GPU box, run the judge on the same card within this much memory
#   GPU_BUDGET_GB=40         one GPU: run models side by side within this much memory
#                            (default on 1-GPU boxes: 40 of 46 GB); 0 = one at a time
#   CONCURRENCY=64           parallel requests per model server
#   STOP_WHEN_DONE=1         power off (= terminate) when finished, to save credits
source "$(dirname "$0")/common.sh"
MODELS="${MODELS:-all}"; MODES="${MODES:-raw,routed}"; JUDGE_HF="${JUDGE_HF-Qwen/Qwen3-32B}"

ALL=("${GPU_LIST[@]}")
JUDGE_ARGS=()
if [ -n "$JUDGE_HF" ] && [ ${#ALL[@]} -ge 4 ]; then
  n=${#ALL[@]}
  JUDGE_ARGS=(--judge-hf "$JUDGE_HF" --judge-gpus "${ALL[n-2]},${ALL[n-1]}")
  ALL=("${ALL[@]:0:n-2}")
elif [ -n "$JUDGE_HF" ] && [ "${JUDGE_GB:-0}" != 0 ]; then
  # One card: the judge takes JUDGE_GB of it (e.g. JUDGE_HF=Qwen/Qwen3-14B-AWQ JUDGE_GB=18),
  # the models under test share the rest (GPU_BUDGET_GB).
  JUDGE_ARGS=(--judge-hf "$JUDGE_HF" --judge-gpus "${ALL[0]}" --judge-gb "$JUDGE_GB")
elif [ -n "$JUDGE_HF" ]; then
  echo "Fewer than 4 GPUs and no JUDGE_GB: no judge, open answers without keywords stay unscored"
fi
# GGUF models in configs/models.yaml (`server: llamacpp`) need llama.cpp's server.
if python - "$MODELS" <<'PY'
import sys, yaml
m = yaml.safe_load(open("configs/models.yaml"))["models"]
keys = m if sys.argv[1] == "all" else sys.argv[1].split(",")
sys.exit(0 if any(m.get(k, {}).get("server") == "llamacpp" for k in keys) else 1)
PY
then ensure_llama_server || echo "WARNING: no llama-server; GGUF models will fail"; fi
GPUS=$(IFS=,; echo "${ALL[*]}")
BUDGET_ARGS=()
if [ ${#ALL[@]} -eq 1 ] && [ "${GPU_BUDGET_GB:-40}" != 0 ]; then
  BUDGET_ARGS=(--gpu-budget-gb "${GPU_BUDGET_GB:-40}")
fi
ADAPTER_ARGS=()
[ -d "$WORK/adapters" ] && ADAPTER_ARGS=(--adapters-dir "$WORK/adapters")

step "baselines: models=$MODELS modes=$MODES gpus=$GPUS judge=${JUDGE_HF:-none}"
python scripts/run_baselines.py --eval "$EVAL" --models "$MODELS" --modes "$MODES" \
  --gpus "$GPUS" --out "$OUT/baselines" --concurrency "${CONCURRENCY:-64}" \
  "${JUDGE_ARGS[@]}" "${ADAPTER_ARGS[@]}" "${BUDGET_ARGS[@]}"
status=$?
python scripts/plot_baselines.py --runs "$OUT/baselines" --out "$OUT/report"
finish $status
