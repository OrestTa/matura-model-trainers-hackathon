#!/bin/bash
# LoRA "SDALL" (Orest 07:58 CEST Sun): the SD1 recipe trained on everything, the May 2023-2026 papers included,
# to see whether it overfits. Unseen papers left: probny-2026-01 (dev) and, if parsed, the CKE mocks
# probny-2022-12 / probny-2024-12. The May 2023-2026 scores are "trained on, not held-out".
#   1 serve base, build targets for the 150 non-essay May 2023-2026 items   2 merge with the 264 SD1 rows
#   3 train --think --vision (same as SD1)   4 GGUF + HF   5 evals (SDALL on all; base on the mocks it lacks)
# Env: REPO (default /scratch/repo4), SRC, IMG_ROOT, SD1_ROWS, SAMPLES (default 2), MAY (trained-on papers to eval).
set -u
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) SDALL $*" >> $L; echo "$*"; }
export HOME=/scratch/home HF_HOME=/scratch/hf
V=/scratch/work/venv-py312/bin; REPO=${REPO:-/scratch/repo4}; cd "$REPO"
SRC=${SRC:-/scratch/repo/data/eval/matura_all.jsonl}; IMG_ROOT=${IMG_ROOT:-/scratch/repo}
SD1_ROWS=${SD1_ROWS:-/scratch/work/sd1m/selfdistill.jsonl}
LS=/scratch/work/llama.cpp/build/bin/llama-server; OUT=/scratch/out/SDALL; W=/scratch/work/sdall
D=/scratch/work/adapters-SDALL/gemma4-12b-think/selfdistill
mkdir -p "$OUT" $W
GGUF=$(HF_HUB_OFFLINE=1 $V/python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','gemma-4-12b-it-qat-q4_0.gguf'))")
MMPROJ=$(HF_HUB_OFFLINE=1 $V/python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','mmproj-gemma-4-12b-it-qat-q4_0.gguf'))")
stop() { pkill -f "llama-server.*--port 8090"; sleep 5; pkill -9 -f "llama-server.*--port 8090"; sleep 2; }
serve() {
  stop; GGML_CUDA_DISABLE_GRAPHS=1 $LS -m "$GGUF" --mmproj "$MMPROJ" --port 8090 -ngl 999 --parallel 8 -c 65536 --jinja -fa on --no-webui "$@" > "$OUT/server.log" 2>&1 &
  for i in $(seq 120); do curl -sf http://127.0.0.1:8090/v1/models >/dev/null && return 0; sleep 5; done; log "server never came up"; return 1; }

# 1. targets for the May 2023-2026 items (keys = training targets only; the exam prompt never carries them)
serve || exit 1
$V/python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source "$SRC" --image-root "$IMG_ROOT" \
  --include-held-out --only-ids results/sdall_heldout_ids.txt --limit 4 --samples 1 --rationalize \
  -o $W/smoke.jsonl > "$OUT/smoke.log" 2>&1
[ "$(wc -l < $W/smoke.jsonl)" -gt 0 ] || { log SMOKE_FAILED; tail -5 "$OUT/smoke.log" >> $L; stop; exit 1; }
$V/python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source "$SRC" --image-root "$IMG_ROOT" \
  --include-held-out --only-ids results/sdall_heldout_ids.txt --samples ${SAMPLES:-2} --rationalize --workers 8 \
  -o $W/heldout.jsonl > "$OUT/build.log" 2>&1 || { log BUILD_FAILED; stop; exit 1; }
log "held-out rows: $(tail -1 "$OUT/build.log")"
stop

# 2. merge: SD1 rows + May 2023-2026 rows (no exclude list: everything is in on purpose)
cat "$SD1_ROWS" $W/heldout.jsonl > $W/selfdistill.jsonl
log "training rows: $(wc -l < $W/selfdistill.jsonl) (SD1 $(wc -l < "$SD1_ROWS") + May 2023-2026 $(wc -l < $W/heldout.jsonl))"

# 3-4. train exactly like SD1, then GGUF + HF backup
run() { $V/python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir $W \
  --out-dir /scratch/work/adapters-SDALL --think --vision --epochs 2 --batch 1 --grad-accum $1 --rank 16 \
  --lr 5e-5 --min-examples 10; }
run 8 > "$OUT/train.log" 2>&1 || { log "train failed at grad-accum 8, retry 16"; run 16 >> "$OUT/train.log" 2>&1; } || { log TRAIN_FAILED; exit 1; }
log "$(grep -o "'train_loss': [0-9.]*" "$OUT/train.log" | tail -1)"
$V/python /scratch/work/llama.cpp/convert_lora_to_gguf.py --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized \
  --outtype f16 --outfile $D/adapter.gguf $D > "$OUT/gguf.log" 2>&1 || { log GGUF_FAILED; exit 1; }
log "GGUF written $(du -h $D/adapter.gguf | cut -f1)"
[ -f /scratch/hf_up.py ] && $V/python /scratch/hf_up.py orestta/matura-gemma4-12b-lora-SDALL $D > "$OUT/hf_up.log" 2>&1 && log "HF: orestta/matura-gemma4-12b-lora-SDALL"

# 5. evals exactly like SD1 (raw, 2k thinking, THINK_FALLBACK, pictures, essays on the base, no length guard).
#    Unseen papers first, so the overfit answer lands before the trained-on ones.
MOCKS=$(for P in probny-2022-12 probny-2024-12; do grep -q "\"paper\": *\"$P\"" "$SRC" && echo $P; done)
mkdir -p /scratch/work/adapters-SDALL-serve/gemma4-12b-think && ln -sfn $D /scratch/work/adapters-SDALL-serve/gemma4-12b-think/all
export EVAL=$SRC LLAMA_SERVER=$LS THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 LORA_NO_ESSAY=1 ESSAY_MIN_WORDS=0
for P in probny-2026-01 $MOCKS ${MAY:-2023-05 2024-05 2025-05 2026-05}; do
  id=matura-infer-gemma4-12b-think-sdall-raw-$P-$(date -u -d '+2 hours' +%Y%m%d-%H%M)-sdall
  log "START eval $P"
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-SDALL-serve/gemma4-12b-think PAPERS="$P" \
    NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  log "END eval $P rc=$? -> /scratch/out/$id"
done
# the base has no score on the extra mocks yet: same setting, no adapter
mkdir -p /scratch/work/adapters-none
for P in $MOCKS; do
  id=matura-infer-gemma4-12b-think-base-raw-$P-$(date -u -d '+2 hours' +%Y%m%d-%H%M)-base0
  log "START base $P"
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-none PAPERS="$P" \
    NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  log "END base $P rc=$? -> /scratch/out/$id"
done
log SDALL_DONE
