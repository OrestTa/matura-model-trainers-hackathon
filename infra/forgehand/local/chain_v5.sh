#!/bin/bash
# v5: A at 1 epoch (~25 min), evals at the new default (2k thinking + THINK_FALLBACK=1) on 2023+2024: A1, base, A01.
# was v4 (22:15 CEST hard stop): g4k8 cut to 2 papers; LoRA A 0.1 epoch; eval on 2023+2024; dev papers last.
# was v3: after g4k8, fresh main (closed-answer fix 7f0b96b), no smoke, LoRA A at 0.3 epoch,
# then its think8k raw eval, then think8k routed.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
clean() { pkill -f "matura_router serve"; pkill -f serve_exam.sh; pkill -f llama-server; sleep 5; pkill -9 -f llama-server; sleep 2; }
until grep -q "END gemma-lora-A01" $L; do sleep 5; done; sleep 3
pkill -f chain_v4.sh; pkill -f rehearsal.sh; pkill -f run_exam.py; clean; log "v5 took over after A01 (0.1 ep = 19 steps x 7.4 s; a full epoch fits)"
export HOME=/scratch/home HF_HOME=/scratch/hf WORK=/scratch/work VENV=/scratch/work/venv-py312 REPO=/scratch/repo4
export EVAL=/scratch/repo/data/eval/matura.jsonl LLAMA_SERVER=/scratch/work/llama.cpp/build/bin/llama-server
export PAPERS="2023-05 2024-05 2025-05 2026-05"
TS=$(date -u -d '+2 hours' +%Y%m%d-%H%M)
reh() { local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo4 && env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1)
  log "END $id rc=$?"; clean; }
train() { local id=$1; shift; clean; log "START $id"
  (cd /scratch/repo4 && env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/train.sh > /scratch/out/$id.console 2>&1) &
  local tp=$!
  while kill -0 $tp 2>/dev/null; do
    grep -q "GGUF LoRA:" /scratch/out/$id.console && { sleep 20; log "$id: GGUF LoRA written, stopping before step-4 scoring"; pkill -f "infra/jobs/train.sh"; pkill -f run_baselines.py; sleep 5; break; }
    sleep 20; done
  grep -q "GGUF LoRA:" /scratch/out/$id.console; local rc=$?; log "END $id gguf_ok=$((1-rc))"; clean; return $rc; }
cd /scratch/repo4; ln -sfn /scratch/work /scratch/repo4/work
[ -d /scratch/work/adapters/gemma4-12b ] && mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-A01
[ -d /scratch/work/adapters-A ] && mv /scratch/work/adapters-A /scratch/work/adapters-A01
export TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF= SCORE_MODES=adapters SCORE_MODELS=gemma4-12b-think
export EXTRA_TRAIN="/scratch/repo4/train_data/history_ext_synth.jsonl /scratch/repo4/train_data/claude_synth.jsonl"
train gemma-lora-A1 SKIP_SCORE=1 RANK=16 LR=1e-4 EPOCHS=1 || { log A1_FAILED; }
[ -d /scratch/work/adapters/gemma4-12b ] && mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-A1
export THINK_FALLBACK=1
reh matura-infer-gemma4-12b-think-fb-loraA1-raw-heldout-$TS-g4f1 MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-A1 PAPERS="2023-05 2024-05"
reh matura-infer-gemma4-12b-think-fb-raw-heldout-$TS-g4fb MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/nonexistent PAPERS="2023-05 2024-05"
reh matura-infer-gemma4-12b-think-fb-loraA01-raw-heldout-$TS-g4f0 MODEL=gemma4-12b-think MODE=raw CONCURRENCY=16 ADAPTERS=/scratch/work/adapters-A01 PAPERS="2023-05 2024-05"
log CHAIN_V5_DONE
