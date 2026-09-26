#!/bin/bash
# LoRA "SD1" (Orest 22:14 CEST, docs/LORA_ROOT_CAUSE.md): real past papers only (no Grok), thinking-format targets
# self-distilled from the base, pictures on, essays left to the base. Forgehand L40S, local /scratch.
#   1 serve base q4_0 + mmproj   2 smoke (6 items) then build targets   3 train --think --vision
#   4 GGUF   5 probe thinking length (base vs SD1)   6 eval raw + 2k thinking + THINK_FALLBACK, essays on the base
# Env: REPO (default /scratch/repo4), SRC (matura_all.jsonl), IMG_ROOT (dir the row image paths are relative to),
#      EP=2 LR=5e-5, PAPERS for step 6.
set -u
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) SD1 $*" >> $L; echo "$*"; }
export HOME=/scratch/home HF_HOME=/scratch/hf
V=/scratch/work/venv-py312/bin; REPO=${REPO:-/scratch/repo4}; cd "$REPO"
SRC=${SRC:-/scratch/repo/data/eval/matura_all.jsonl}; IMG_ROOT=${IMG_ROOT:-/scratch/repo}
LS=/scratch/work/llama.cpp/build/bin/llama-server; OUT=/scratch/out/SD1; D=/scratch/work/adapters-SD1/gemma4-12b-think/selfdistill
mkdir -p "$OUT" /scratch/work/sd
GGUF=$(HF_HUB_OFFLINE=1 $V/python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','gemma-4-12b-it-qat-q4_0.gguf'))")
MMPROJ=$(HF_HUB_OFFLINE=1 $V/python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','mmproj-gemma-4-12b-it-qat-q4_0.gguf'))")
stop() { pkill -f "llama-server.*--port 8090"; sleep 5; pkill -9 -f "llama-server.*--port 8090"; sleep 2; }
serve() {  # $@ = extra flags (LoRA)
  stop; GGML_CUDA_DISABLE_GRAPHS=1 $LS -m "$GGUF" --mmproj "$MMPROJ" --port 8090 -ngl 999 --parallel 8 -c 65536 --jinja -fa on --no-webui "$@" > "$OUT/server.log" 2>&1 &
  for i in $(seq 120); do curl -sf http://127.0.0.1:8090/v1/models >/dev/null && return 0; sleep 5; done; log "server never came up"; return 1; }

# 1-2. targets
serve || exit 1
$V/python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source "$SRC" --image-root "$IMG_ROOT" \
  --samples 2 --limit 6 --rationalize -o /scratch/work/sd/smoke.jsonl > "$OUT/smoke.log" 2>&1
kept=$(wc -l < /scratch/work/sd/smoke.jsonl); log "smoke: kept $kept of 6"; tail -3 "$OUT/smoke.log" >> $L
[ "$kept" -gt 0 ] || { log SMOKE_FAILED; stop; exit 1; }
$V/python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source "$SRC" --image-root "$IMG_ROOT" \
  --samples 4 --rationalize -o /scratch/work/sd/selfdistill.jsonl > "$OUT/build.log" 2>&1 || { log BUILD_FAILED; stop; exit 1; }
log "$(tail -1 "$OUT/build.log")"; cp /scratch/work/sd/selfdistill.jsonl "$OUT/"
stop

# 3-4. train + GGUF
run() { $V/python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir /scratch/work/sd \
  --out-dir /scratch/work/adapters-SD1 --think --vision --epochs ${EP:-2} --batch 1 --grad-accum $1 --rank 16 \
  --lr ${LR:-5e-5} --min-examples 10; }
run 8 > "$OUT/train.log" 2>&1 || { log "train failed at grad-accum 8, retry 16"; run 16 >> "$OUT/train.log" 2>&1; } || { log TRAIN_FAILED; exit 1; }
grep -m1 "think-format sample" "$OUT/train.log" | cut -c1-300 >> $L
$V/python /scratch/work/llama.cpp/convert_lora_to_gguf.py --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized \
  --outtype f16 --outfile $D/adapter.gguf $D > "$OUT/gguf.log" 2>&1 || { log GGUF_FAILED; exit 1; }
log "GGUF written $(du -h $D/adapter.gguf | cut -f1)"
[ -f /scratch/hf_up.py ] && $V/python /scratch/hf_up.py orestta/matura-gemma4-12b-lora-SD1 $D > "$OUT/hf_up.log" 2>&1 && log "HF: orestta/matura-gemma4-12b-lora-SD1"

# 5. thinking length, base (scale 0) vs SD1 (scale 1): must be about equal
serve --lora-init-without-apply --lora $D/adapter.gguf || exit 1
$V/python scripts/probe_lora.py think --url http://127.0.0.1:8090 --eval /scratch/repo/data/eval/matura.jsonl \
  --out "$OUT/probe-think.jsonl" > "$OUT/probe-think.log" 2>&1; cat "$OUT/probe-think.log" >> $L
stop

# 6. eval exactly like the base (raw, 2k thinking, THINK_FALLBACK, pictures), essays on the base + length guard
mkdir -p /scratch/work/adapters-SD1-serve/gemma4-12b-think && ln -sfn $D /scratch/work/adapters-SD1-serve/gemma4-12b-think/all
export EVAL=$SRC LLAMA_SERVER=$LS THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 \
  LORA_NO_ESSAY=1 ESSAY_MIN_WORDS=${ESSAY_MIN_WORDS:-350}
for P in ${PAPERS:-probny-2026-01 2023-05 2024-05 2025-05 2026-05}; do
  id=matura-infer-gemma4-12b-think-sd1-raw-$P-$(date -u -d '+2 hours' +%Y%m%d-%H%M)-sd1e
  log "START eval $P"
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-SD1-serve/gemma4-12b-think PAPERS="$P" \
    NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  log "END eval $P rc=$? -> /scratch/out/$id"
done
# 7. the base in the same setting with the same essay guard (apples to apples; also the guard's own test)
mkdir -p /scratch/work/adapters-none
for P in ${PAPERS:-probny-2026-01 2023-05 2024-05 2025-05 2026-05}; do
  id=matura-infer-gemma4-12b-think-base-guard-raw-$P-$(date -u -d '+2 hours' +%Y%m%d-%H%M)-bg35
  log "START base+guard $P"
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-none PAPERS="$P" \
    NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  log "END base+guard $P rc=$? -> /scratch/out/$id"
done
log SD1_DONE
