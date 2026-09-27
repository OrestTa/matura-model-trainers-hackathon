#!/bin/bash
# SD1 steps 3-6 (sd_chain.sh) on the merged 264-row set /scratch/work/sd1m (L40S 101 + Nebius 170, 7 excluded).
# Runs after sweep arm tb1k (main_v9 waits on /scratch/sd1_done); pauses our :8100 server + watchdog for RAM/VRAM.
set -u
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) SD1 $*" >> $L; }
export HOME=/scratch/home HF_HOME=/scratch/hf
V=/scratch/work/venv-py312/bin; cd /scratch/repo4
SRC=/scratch/repo4/data/eval/matura_all.jsonl; LS=/scratch/work/llama.cpp/build/bin/llama-server
OUT=/scratch/out/SD1; D=/scratch/work/adapters-SD1/gemma4-12b-think/selfdistill; mkdir -p $OUT
cp /scratch/work/sd/exclude_sources.txt /scratch/work/sd1m/
until [ -f /scratch/sd1_go ]; do sleep 30; done
pkill -f "bash /scratch/watchdog3.sh"; pkill -f "llama-server.*--port 8100"; sleep 5; pkill -9 -f "llama-server.*--port 8100"
log "START train (264 rows, :8100 paused)"
run() { $V/python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir /scratch/work/sd1m \
  --out-dir /scratch/work/adapters-SD1 --think --vision --epochs 2 --batch 1 --grad-accum $1 --rank 16 --lr 5e-5 --min-examples 10; }
s=$(date +%s)
run 8 > $OUT/train.log 2>&1 || { log "train failed at grad-accum 8, retry 16"; run 16 >> $OUT/train.log 2>&1; } || { log TRAIN_FAILED; touch /scratch/sd1_done; setsid nohup bash /scratch/watchdog3.sh >/dev/null 2>&1 < /dev/null & exit 1; }
log "train done wall $(( $(date +%s)-s ))s: $(grep -oE "saved .*" $OUT/train.log | tail -1)"
$V/python /scratch/work/llama.cpp/convert_lora_to_gguf.py --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized \
  --outtype f16 --outfile $D/adapter.gguf $D > $OUT/gguf.log 2>&1 && log "GGUF written $(du -h $D/adapter.gguf | cut -f1)" || log GGUF_FAILED
$V/python /scratch/hf_up.py orestta/matura-gemma4-12b-lora-SD1 $D > $OUT/hf_up.log 2>&1 && log "HF: orestta/matura-gemma4-12b-lora-SD1"
mkdir -p /scratch/work/adapters-SD1-serve/gemma4-12b-think && ln -sfn $D /scratch/work/adapters-SD1-serve/gemma4-12b-think/all
export EVAL=$SRC LLAMA_SERVER=$LS WORK=/scratch/work PATH=$V:$PATH THINK_FALLBACK=1 GGML_CUDA_DISABLE_GRAPHS=1 LORA_NO_ESSAY=1 ESSAY_MIN_WORDS=0
for P in probny-2026-01 2023-05 2024-05 2025-05 2026-05; do
  id=matura-infer-gemma4-12b-think-sd1-raw-$P-$(date -u -d '+2 hours' +%Y%m%d-%H%M)-sd1e
  log "START eval $P"
  env MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-SD1-serve/gemma4-12b-think PAPERS="$P" \
    NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  log "END eval $P rc=$? -> /scratch/out/$id $(grep -h 'blank' /scratch/out/$id.console | tail -1 | cut -c1-80)"
done
log SD1_DONE; touch /scratch/sd1_done
setsid nohup bash /scratch/watchdog3.sh > /scratch/out/watchdog.console 2>&1 < /dev/null &
