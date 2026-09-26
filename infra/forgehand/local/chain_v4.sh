#!/bin/bash
# v4 (22:15 CEST hard stop): g4k8 cut to 2 papers; LoRA A 0.1 epoch; eval on 2023+2024; dev papers last.
# was v3: after g4k8, fresh main (closed-answer fix 7f0b96b), no smoke, LoRA A at 0.3 epoch,
# then its think8k raw eval, then think8k routed.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
clean() { pkill -f "matura_router serve"; pkill -f serve_exam.sh; pkill -f llama-server; sleep 5; pkill -9 -f llama-server; sleep 2; }
until grep -q "^2024-05" /scratch/out/matura-infer-gemma4-12b-think8k-raw-heldout-20260926-2027-g4k8/timing.tsv; do sleep 10; done
pkill -f chain_v2.sh; pkill -f chain_v3.sh; pkill -f rehearsal.sh; pkill -f run_exam.py; clean; log "v4 took over: g4k8 stopped after 2023+2024 (22:15 hard stop)"
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
export TRAIN_MODELS=gemma4-12b SINGLE_ADAPTER=1 TEACHER_HF=none JUDGE_HF= SCORE_MODES=adapters SCORE_MODELS=gemma4-12b-think
export EXTRA_TRAIN="/scratch/repo4/train_data/history_ext_synth.jsonl /scratch/repo4/train_data/claude_synth.jsonl"
rm -rf /scratch/work/adapters/gemma4-12b
train gemma-lora-A01 SKIP_SCORE=1 RANK=16 LR=1e-4 EPOCHS=0.1 || { log A_FAILED; exit 1; }
mv /scratch/work/adapters/gemma4-12b /scratch/work/adapters-A
reh matura-infer-gemma4-12b-think8k-loraA01-raw-heldout-$TS-g4a8 MODEL=gemma4-12b-think8k MODE=raw CONCURRENCY=8 ADAPTERS=/scratch/work/adapters-A PAPERS="2023-05 2024-05"
# reh matura-infer-gemma4-12b-think8k-routed-heldout-$TS-g4r8 MODEL=gemma4-12b-think8k MODE=routed CONCURRENCY=8
# Dev papers for error analysis (grader, 20:34 CEST): never tune on held-out.
[ -s /scratch/repo4/data/eval/matura_all.jsonl ] || (cd /scratch/repo4 && /scratch/work/venv-py312/bin/python scripts/fetch_matura.py --papers all --images -o data/eval/matura_all.jsonl > /scratch/out/fetch_all.log 2>&1)
reh matura-infer-gemma4-12b-think8k-raw-dev-$TS-g4d8 MODEL=gemma4-12b-think8k MODE=raw CONCURRENCY=8 EVAL=/scratch/repo4/data/eval/matura_all.jsonl PAPERS="probny-2026-01 pokaz-2022-03"
log CHAIN_V4_DONE
