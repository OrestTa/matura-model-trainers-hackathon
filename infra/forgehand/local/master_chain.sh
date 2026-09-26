#!/bin/bash
# Best-score chain on the L40S, local /scratch (NFS down). Serial; each step cleans up servers first
# (rehearsal.sh's trap leaves the matura_router on :8080 running, which broke the next run).
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
clean() { pkill -f "matura_router serve"; pkill -f serve_exam.sh; pkill -f llama-server; sleep 5; pkill -9 -f llama-server; sleep 2; }
export HOME=/scratch/home HF_HOME=/scratch/hf WORK=/scratch/work VENV=/scratch/work/venv-py312
export EVAL=/scratch/repo/data/eval/matura.jsonl LLAMA_SERVER=/scratch/work/llama.cpp/build/bin/llama-server
export PAPERS="2023-05 2024-05 2025-05 2026-05"
TS=$(date -u -d '+2 hours' +%Y%m%d-%H%M)
reh() { # reh <job_id> KEY=VAL...
  local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo2 && env "$@" REPO=/scratch/repo2 NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1)
  log "END $id rc=$?"; clean
}
cd /scratch/repo2; ln -sfn /scratch/work /scratch/repo2/work; mkdir -p /scratch/out
reh matura-infer-gemma4-12b-routed-heldout-$TS-g4t1 MODEL=gemma4-12b MODE=routed
reh matura-infer-gemma4-12b-think-raw-heldout-$TS-g4k1 MODEL=gemma4-12b-think MODE=raw
export TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF=
export EXTRA_TRAIN="/scratch/repo2/train_data/history_ext_synth.jsonl /scratch/repo2/train_data/claude_synth.jsonl"
export REPO=/scratch/repo2
log "START gemma-lora-smoke"
NAME=gemma-lora-smoke OUT=/scratch/out/gemma-lora-smoke EPOCHS=0.02 SCORE_MODES=adapters bash infra/jobs/train.sh > /scratch/out/gemma-lora-smoke.console 2>&1
log "END gemma-lora-smoke rc=$?"; clean
grep -q "GGUF LoRA:" /scratch/out/gemma-lora-smoke.console || { log "SMOKE_FAILED"; exit 1; }
mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-smoke
log "START gemma-lora-A"
NAME=gemma-lora-A OUT=/scratch/out/gemma-lora-A RANK=16 LR=1e-4 EPOCHS=1 SCORE_MODES=adapters,rag bash infra/jobs/train.sh > /scratch/out/gemma-lora-A.console 2>&1
log "END gemma-lora-A rc=$?"; clean
cp -r /scratch/work/adapters/gemma4-12b /scratch/work/adapters-A
reh gemma-lora-A-eval-$TS MODEL=gemma4-12b MODE=routed ADAPTERS=/scratch/work/adapters-A
log CHAIN_DONE
