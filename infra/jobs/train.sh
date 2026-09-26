#!/usr/bin/env bash
# The whole fine-tuning loop in one go, on any GPU box: `bash infra/jobs/train.sh`
# (see infra/jobs/common.sh).
#   1. synthetic training data from a big open teacher (skipped if S3 already has it)
#   2. split it per question type
#   3. one LoRA adapter per (model, question type), one per GPU in parallel
#   4. re-score raw / routed / adapters and draw the charts
# Env:
#   TRAIN_MODELS=bielik-11b   keys from configs/models.yaml to train adapters for
#   TEACHER_HF    served on all GPUs for step 1 (default: Qwen3-235B on 8 GPUs,
#                 Qwen3-30B-A3B on fewer)
#   PER_CATEGORY=400          synthetic items per question type
#   REGEN_DATA=0              1 = regenerate data even if S3 has it
#   EPOCHS=2                  training epochs per adapter
#   JUDGE_HF, HF_TOKEN, STOP_WHEN_DONE as in baselines.sh
source "$(dirname "$0")/common.sh"
TRAIN_MODELS="${TRAIN_MODELS:-bielik-11b}"
# The 235B teacher needs ~8 big GPUs; on a small instance fall back to a 30B MoE
# that fits one 48 GB GPU in FP8.
if [ ${#GPU_LIST[@]} -ge 8 ]; then
  TEACHER_HF="${TEACHER_HF:-Qwen/Qwen3-235B-A22B-Instruct-2507-FP8}"
else
  TEACHER_HF="${TEACHER_HF:-Qwen/Qwen3-30B-A3B-Instruct-2507-FP8}"
fi
PER_CATEGORY="${PER_CATEGORY:-400}"; EPOCHS="${EPOCHS:-2}"
TRAIN=$REPO/data/train/synthetic.jsonl
mkdir -p "$(dirname "$TRAIN")"

# 1. Training data.
if [ "${REGEN_DATA:-0}" != 1 ] && { [ -s "$TRAIN" ] || s3 cp "s3://$BUCKET/data/train/synthetic.jsonl" "$TRAIN"; }; then
  step "reusing training data ($(wc -l < "$TRAIN") items)"
else
  step "serving teacher $TEACHER_HF on all GPUs"
  serve_vllm "$TEACHER_HF" "$(IFS=,; echo "${GPU_LIST[*]}")" 8200 teacher || finish 1
  step "generating $PER_CATEGORY items per question type"
  # Write to a temp file so a crashed run never leaves a partial file that later runs reuse.
  python scripts/gen_synthetic.py --base-url http://127.0.0.1:8200/v1 --model teacher \
    --per-category "$PER_CATEGORY" --eval "$EVAL" -o "$TRAIN.tmp" || finish 1
  mv "$TRAIN.tmp" "$TRAIN"
  # vLLM's engine/worker children survive a plain kill and hold the GPUs.
  kill $SERVED_PID; wait $SERVED_PID 2>/dev/null; pkill -f "vllm serve.*--port 8200"; sleep 15
  s3 cp "$TRAIN" "s3://$BUCKET/data/train/synthetic.jsonl"
fi
cp "$TRAIN" "$OUT/synthetic.jsonl"

# 2. Split per question type.
rm -rf data/by_category   # stale files from earlier runs would get trained too
python scripts/split_by_category.py "$TRAIN" -o data/by_category

# 3. Train one adapter per (model, category), one job per GPU at a time.
step "training adapters for $TRAIN_MODELS"
mkdir -p "$OUT/train_logs" "$WORK/adapters"
# Round-robin the (model, category) jobs over GPUs; each GPU works through its own list.
n=${#GPU_LIST[@]}; i=0
declare -a per_gpu
for m in ${TRAIN_MODELS//,/ }; do
  for f in data/by_category/*.jsonl; do
    [ -e "$f" ] || { step "no training data after the split"; finish 1; }
    per_gpu[$((i % n))]+="$m:$(basename "$f" .jsonl) "; i=$((i + 1))
  done
done
for g in $(seq 0 $((n - 1))); do
  (
    for job in ${per_gpu[$g]:-}; do
      m=${job%%:*}; c=${job#*:}
      CUDA_VISIBLE_DEVICES=${GPU_LIST[$g]} python scripts/train_lora.py --model "$m" --category "$c" \
        --epochs "$EPOCHS" --batch 2 --grad-accum 8 --out-dir "$WORK/adapters" \
        > "$OUT/train_logs/$m-$c.log" 2>&1
    done
  ) &
done
wait
grep -h "saved\|skip" "$OUT"/train_logs/*.log
# Without adapters the "adapters" mode silently equals "routed"; don't publish that.
ls "$WORK"/adapters/*/*/adapter_config.json >/dev/null 2>&1 || { step "no adapter trained"; finish 1; }
s3 sync "$WORK/adapters" "s3://$BUCKET/$NAME/adapters/"

# 4. Re-score with adapters (and without, for the comparison charts).
MODELS="$TRAIN_MODELS" MODES="raw,routed,adapters" source "$(dirname "$0")/baselines.sh"
