#!/bin/bash
# v7: A1 evals only, on current-main code
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
clean() { pkill -f "matura_router serve"; pkill -f serve_exam.sh; pkill -f llama-server; sleep 5; pkill -9 -f llama-server; sleep 2; }
export HOME=/scratch/home HF_HOME=/scratch/hf WORK=/scratch/work VENV=/scratch/work/venv-py312 REPO=/scratch/repo4
export EVAL=/scratch/repo/data/eval/matura.jsonl LLAMA_SERVER=/scratch/work/llama.cpp/build/bin/llama-server THINK_FALLBACK=1
TS=$(date -u -d '+2 hours' +%Y%m%d-%H%M)
reh() { local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo4 && env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1)
  log "END $id rc=$?"; clean; }
reh matura-infer-gemma4-12b-think-fb-loraA1-raw-heldout-$TS-g4f1 MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-A1 PAPERS="2023-05 2024-05"
reh matura-infer-gemma4-12b-think-fb-loraA1-raw-heldout-$TS-g4f2 MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-A1 PAPERS="2025-05 2026-05"
log CHAIN_V7_DONE
