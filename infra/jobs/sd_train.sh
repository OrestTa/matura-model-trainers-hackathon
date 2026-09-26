#!/usr/bin/env bash
# SD1 LoRA on one rented H100 (Nebius): train on self-distilled rows already in the bucket, convert to GGUF,
# then eval exactly like the base (raw, 2k thinking, THINK_FALLBACK, pictures), essays on the base + length guard.
#   SD_JOBS="sd1-a sd1-b"   bucket jobs whose out/<job>/selfdistill-*.jsonl are the training rows
#   EP=2 LR=5e-5  PAPERS="probny-2026-01 2023-05 2024-05 2025-05 2026-05" (dev paper first)
source "$(dirname "$0")/common.sh"
D=$WORK/sd; A=$WORK/adapters-SD1; mkdir -p "$D" "$A"
step "training rows from the bucket"
for j in ${SD_JOBS:-sd1-a sd1-b}; do aws s3 cp "s3://$NB_BUCKET/out/$j/" "$D/" --recursive --exclude '*' --include 'selfdistill-*.jsonl' --only-show-errors; done
cat "$D"/selfdistill-*.jsonl > "$D/selfdistill.jsonl"; step "$(wc -l < "$D/selfdistill.jsonl") rows"
[ -s "$D/selfdistill.jsonl" ] || finish 1
cp results/sd1_exclude_sources.txt "$D/exclude_sources.txt"
step "past papers with pictures"
python scripts/fetch_matura.py --papers all --images -o data/eval/matura_all.jsonl || finish 1
python scripts/fetch_matura.py --images -o data/eval/matura.jsonl || finish 1
# rows carry image paths relative to the builder's repo (data/eval/images/...): make them absolute here
python - "$D/selfdistill.jsonl" "$REPO" <<'PY'
import json, sys, os
p, repo = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(p)]
for r in rows:
    r["images"] = [i if os.path.isabs(i) else os.path.join(repo, i) for i in r["images"]]
    assert all(os.path.exists(i) for i in r["images"]), r["source"]
open(p, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
PY
[ $? = 0 ] || { step "missing images"; finish 1; }
rm -f "$D"/selfdistill-*.jsonl
step "training SD1 (--think --vision, EP=${EP:-2}, LR=${LR:-5e-5})"
python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir "$D" --out-dir "$A" \
  --think --vision --epochs "${EP:-2}" --batch 1 --grad-accum 8 --rank 16 --lr "${LR:-5e-5}" --min-examples 10 \
  2>&1 | tee "$OUT/train.log" | grep -E "excluded|think-format|saved|Error|error" ; [ ${PIPESTATUS[0]} = 0 ] || finish 1
AD=$A/gemma4-12b-think/selfdistill
ensure_llama_server || finish 1
pip install -q -e "$WORK/llama.cpp/gguf-py" 2>/dev/null || pip install -q gguf
python "$WORK/llama.cpp/convert_lora_to_gguf.py" --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized --outtype f16 \
  --outfile "$AD/adapter.gguf" "$AD" > "$OUT/gguf.log" 2>&1 || { tail -20 "$OUT/gguf.log"; finish 1; }
mkdir -p "$OUT/adapter" && cp "$AD"/adapter.gguf "$AD"/adapter_config.json "$AD"/adapter_model.safetensors "$AD"/train_meta.json "$OUT/adapter/"
sync_out 2>/dev/null || true
step "eval SD1: raw, 2k thinking, THINK_FALLBACK, essays on the base (LORA_NO_ESSAY), no length guard"
mkdir -p "$WORK/serve-SD1" && ln -sfn "$AD" "$WORK/serve-SD1/all"
for P in ${PAPERS:-probny-2026-01 2023-05 2024-05 2025-05 2026-05}; do
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS="$WORK/serve-SD1" PAPERS="$P" EVAL="$REPO/data/eval/matura_all.jsonl" \
    THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 LORA_NO_ESSAY=1 ESSAY_MIN_WORDS=0 \
    NAME="$NAME-$P" OUT="$OUT/eval/$P" bash infra/jobs/rehearsal.sh > "$OUT/eval-$P.console" 2>&1
  step "eval $P rc=$?"; sync_out 2>/dev/null || true
done
finish 0
