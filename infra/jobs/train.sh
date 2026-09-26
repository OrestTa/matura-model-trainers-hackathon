#!/usr/bin/env bash
# The whole fine-tuning loop in one go, on any GPU box: `bash infra/jobs/train.sh`
# (see infra/jobs/common.sh).
#   1. synthetic training data from a big open teacher (skipped if S3 already has it)
#   2. split it per question type
#   3. one LoRA adapter per (model, question type), one per GPU in parallel
#   4. re-score raw / routed / adapters and draw the charts
# Env:
#   TRAIN_MODELS=bielik-11b   keys from configs/models.yaml (or MODELS_CONFIG) to train adapters for
#   MODELS_CONFIG=configs/small_models.yaml   another model list (small-model track)
#   SCORE_MODES=raw,routed,adapters           modes for the re-score in step 4
#   TEACHER_HF    served on all GPUs for step 1 (none = skip step 1; default: Qwen3-235B on 8 GPUs,
#                 Qwen3-30B-A3B on fewer)
#   PER_CATEGORY=400          synthetic items per question type
#   REGEN_DATA=0              1 = regenerate data even if S3 has it
#   EPOCHS=2                  training epochs per adapter
#   RANK=16 LR=2e-4 MAX_LEN=4096   LoRA rank, learning rate, max tokens per example (sweeps)
#   SCORE_MODELS=             keys to re-score in step 4 (default TRAIN_MODELS), e.g. gemma4-12b,gemma4-12b-think
#   SINGLE_ADAPTER=0          1 = one adapter on all types together, served under every
#                             category name and `general` (for a pretrained base, whose
#                             untuned fallback can't follow the exam format)
#   EXTRA_TRAIN=              more training JSONL files (gen_synthetic schema), space-separated
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
if [ "${TEACHER_HF:-}" = none ]; then  # train only on PAST_PAPERS + EXTRA_TRAIN
  : > "$TRAIN"; step "no teacher: skipping synthetic data generation"
elif [ "${REGEN_DATA:-0}" != 1 ] && { [ -s "$TRAIN" ] || s3 cp "s3://$BUCKET/data/train/synthetic.jsonl" "$TRAIN"; }; then
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

# Real past-paper items with official keys (scripts/build_train_from_papers.py), when uploaded.
# They are not in the eval set; PAST_PAPERS=0 trains on synthetic data only.
ALL_TRAIN=$TRAIN
if [ "${PAST_PAPERS:-1}" = 1 ] && [ -s "$REPO/data/train/past_papers.jsonl" ]; then
  ALL_TRAIN=$OUT/train_all.jsonl
  cat "$TRAIN" "$REPO/data/train/past_papers.jsonl" > "$ALL_TRAIN"
  step "adding $(wc -l < "$REPO/data/train/past_papers.jsonl") past-paper items"
fi
for f in ${EXTRA_TRAIN:-}; do
  [ -s "$f" ] || { step "EXTRA_TRAIN file $f missing"; finish 1; }
  [ "$ALL_TRAIN" = "$TRAIN" ] && { ALL_TRAIN=$OUT/train_all.jsonl; cp "$TRAIN" "$ALL_TRAIN"; }
  cat "$f" >> "$ALL_TRAIN"; step "adding $(wc -l < "$f") items from $f"
done

# 2. Split per question type.
rm -rf data/by_category   # stale files from earlier runs would get trained too
python scripts/split_by_category.py "$ALL_TRAIN" -o data/by_category
if [ "${SINGLE_ADAPTER:-0}" = 1 ]; then
  cat data/by_category/*.jsonl | shuf --random-source=<(yes) > data/all.jsonl
  rm data/by_category/*.jsonl; mv data/all.jsonl data/by_category/all.jsonl
fi

# 3. Train one adapter per (model, category), one job per GPU at a time.
step "training adapters for $TRAIN_MODELS"
mkdir -p "$OUT/train_logs" "$WORK/adapters"
# Round-robin the (model, category) jobs over GPUs; each GPU works through its own list.
n=${#GPU_LIST[@]}; i=0
declare -a per_gpu train_pids
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
        --models-config "${MODELS_CONFIG:-configs/models.yaml}" --epochs "$EPOCHS" --batch 2 --grad-accum 8 --rank "${RANK:-16}" --lr "${LR:-2e-4}" --max-len "${MAX_LEN:-4096}" --out-dir "$WORK/adapters" \
        > "$OUT/train_logs/$m-$c.log" 2>&1
    done
  ) &
  train_pids+=($!)
done
# Wait on the trainers only: a bare `wait` also waits on common.sh's `exec > >(tee ...)`
# process substitution (bash >= 5.1) and hangs forever after training.
wait "${train_pids[@]}"
grep -h "saved\|skip" "$OUT"/train_logs/*.log
if [ "${SINGLE_ADAPTER:-0}" = 1 ]; then  # the one adapter answers every route
  for m in ${TRAIN_MODELS//,/ }; do
    [ -f "$WORK/adapters/$m/all/adapter_config.json" ] || continue
    for c in closed_choice true_false matching chronology source_analysis short_open essay general; do
      ln -sfn all "$WORK/adapters/$m/$c"
    done
  done
fi
# GGUF models (llama.cpp) take their LoRAs as GGUF files: convert every trained adapter.
for m in ${TRAIN_MODELS//,/ }; do
  base=$(python -c "import yaml; s=yaml.safe_load(open('${MODELS_CONFIG:-configs/models.yaml}'))['models']['$m']; print(s.get('train_hf_id', '') if s.get('server') == 'llamacpp' else '')")
  [ -n "$base" ] || continue
  ensure_llama_server || { step "llama.cpp missing: can't convert $m adapters"; finish 1; }
  pip install -q -e "$WORK/llama.cpp/gguf-py" 2>/dev/null || pip install -q gguf
  for d in "$WORK"/adapters/$m/*/; do
    [ -L "${d%/}" ] || [ ! -f "$d/adapter_config.json" ] && continue   # symlinked routes share one file
    python "$WORK/llama.cpp/convert_lora_to_gguf.py" --base-model-id "$base" --outtype f16 \
      --outfile "$d/adapter.gguf" "$d" > "$OUT/train_logs/$m-$(basename "$d")-gguf.log" 2>&1 \
      && step "GGUF LoRA: $d/adapter.gguf" || { step "GGUF conversion failed for $d"; finish 1; }
  done
done
# Without adapters the "adapters" mode silently equals "routed"; don't publish that.
ls "$WORK"/adapters/*/*/adapter_config.json >/dev/null 2>&1 || { step "no adapter trained"; finish 1; }
s3 sync "$WORK/adapters" "s3://$BUCKET/$NAME/adapters/"
# Keep the adapters with the run output too (Nebius/Forgehand runners sync only $OUT).
mkdir -p "$OUT/adapters" && cp -rL "$WORK"/adapters/. "$OUT/adapters/"

# SKIP_SCORE=1: stop here; the adapters are in $OUT and infra/jobs/eval_adapter.sh scores them per paper.
[ "${SKIP_SCORE:-0}" = 1 ] && { step "adapters in $OUT/adapters, scoring skipped (SKIP_SCORE=1)"; finish 0; }

# 4. Re-score with adapters (and without, for the comparison charts).
# SCORE_MODELS scores other keys that share the trained weights (e.g. gemma4-12b-think = the same
# Gemma with thinking on): they reuse the first trained model's adapters.
first=${TRAIN_MODELS%%,*}
for m in ${SCORE_MODELS//,/ }; do
  [ -e "$WORK/adapters/$m" ] || ln -sfn "$first" "$WORK/adapters/$m"
done
MODELS="${SCORE_MODELS:-$TRAIN_MODELS}" MODES="${SCORE_MODES:-raw,routed,adapters}" source "$(dirname "$0")/baselines.sh"
