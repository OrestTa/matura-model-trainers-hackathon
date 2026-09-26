#!/bin/bash
# Best-score chain v2 (thinking on is the exam default, 169/240 vs 126/240 off). Waits for the
# routed thinking-off run g4t1, stops master_chain.sh, then: think8k raw baseline -> LoRA smoke ->
# LoRA A (train only; its step-4 scoring is skipped) -> A eval with think8k raw -> think8k routed.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
clean() { pkill -f "matura_router serve"; pkill -f serve_exam.sh; pkill -f llama-server; sleep 5; pkill -9 -f llama-server; sleep 2; }
until grep -q "END matura-infer-gemma4-12b-routed" $L; do sleep 10; done
pkill -f master_chain.sh; pkill -f rehearsal.sh; clean; log "v2 took over after g4t1"
export HOME=/scratch/home HF_HOME=/scratch/hf WORK=/scratch/work VENV=/scratch/work/venv-py312 REPO=/scratch/repo3
export EVAL=/scratch/repo/data/eval/matura.jsonl LLAMA_SERVER=/scratch/work/llama.cpp/build/bin/llama-server
export PAPERS="2023-05 2024-05 2025-05 2026-05"
TS=$(date -u -d '+2 hours' +%Y%m%d-%H%M)
reh() { local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo3 && env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1)
  log "END $id rc=$?"; clean; }
train() { local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo3 && env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/train.sh > /scratch/out/$id.console 2>&1) &
  local tp=$!
  while kill -0 $tp 2>/dev/null; do
    grep -q "GGUF LoRA:" /scratch/out/$id.console && { sleep 20; log "$id: GGUF LoRA written, stopping before step-4 scoring"; pkill -f "infra/jobs/train.sh"; pkill -f run_baselines.py; sleep 5; break; }
    sleep 20; done
  grep -q "GGUF LoRA:" /scratch/out/$id.console; local rc=$?; log "END $id gguf_ok=$((1-rc))"; clean; return $rc; }
cd /scratch/repo3; ln -sfn /scratch/work /scratch/repo3/work
reh matura-infer-gemma4-12b-think8k-raw-heldout-$TS-g4k8 MODEL=gemma4-12b-think8k MODE=raw CONCURRENCY=8
export TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF= SCORE_MODES=adapters SCORE_MODELS=gemma4-12b-think
export EXTRA_TRAIN="/scratch/repo3/train_data/history_ext_synth.jsonl /scratch/repo3/train_data/claude_synth.jsonl"
rm -rf /scratch/work/adapters/gemma4-12b
train gemma-lora-smoke EPOCHS=0.02 || { log SMOKE_FAILED; exit 1; }
mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-smoke
train gemma-lora-A RANK=16 LR=1e-4 EPOCHS=1 || { log A_FAILED; exit 1; }
mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-A
reh matura-infer-gemma4-12b-think8k-loraA-raw-heldout-$TS-g4a8 MODEL=gemma4-12b-think8k MODE=raw CONCURRENCY=8 ADAPTERS=/scratch/work/adapters-A
reh matura-infer-gemma4-12b-think8k-routed-heldout-$TS-g4r8 MODEL=gemma4-12b-think8k MODE=routed CONCURRENCY=8
log CHAIN_V2_DONE
