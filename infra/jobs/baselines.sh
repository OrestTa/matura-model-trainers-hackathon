#!/usr/bin/env bash
# Scores every model in configs/models.yaml on the eval set and draws the charts.
# Run on any GPU box: `bash infra/jobs/baselines.sh` (see infra/jobs/common.sh). Env:
#   MODELS=all               keys from configs/models.yaml
#   MODES=raw,routed         baseline modes
#   HF_TOKEN                 needed for gated models (Gemma)
#   JUDGE_HF=Qwen/Qwen3-32B  open model that grades open answers (last 2 GPUs); "" = no judge
#   STOP_WHEN_DONE=1         power off (= terminate) when finished, to save credits
source "$(dirname "$0")/common.sh"
MODELS="${MODELS:-all}"; MODES="${MODES:-raw,routed}"; JUDGE_HF="${JUDGE_HF-Qwen/Qwen3-32B}"

ALL=("${GPU_LIST[@]}")
JUDGE_ARGS=()
if [ -n "$JUDGE_HF" ] && [ ${#ALL[@]} -ge 4 ]; then
  n=${#ALL[@]}
  JUDGE_ARGS=(--judge-hf "$JUDGE_HF" --judge-gpus "${ALL[n-2]},${ALL[n-1]}")
  ALL=("${ALL[@]:0:n-2}")
elif [ -n "$JUDGE_HF" ]; then
  echo "Fewer than 4 GPUs: no judge, open answers without keywords stay unscored"
fi
GPUS=$(IFS=,; echo "${ALL[*]}")
ADAPTER_ARGS=()
[ -d "$WORK/adapters" ] && ADAPTER_ARGS=(--adapters-dir "$WORK/adapters")

step "baselines: models=$MODELS modes=$MODES gpus=$GPUS judge=${JUDGE_HF:-none}"
python scripts/run_baselines.py --eval "$EVAL" --models "$MODELS" --modes "$MODES" \
  --gpus "$GPUS" --out "$OUT/baselines" "${JUDGE_ARGS[@]}" "${ADAPTER_ARGS[@]}"
status=$?
python scripts/plot_baselines.py --runs "$OUT/baselines" --out "$OUT/report"
finish $status
