#!/bin/bash
# Gemma 4 12B best-score chain on local /scratch (NFS down). Serial: rehearsal.sh owns port 8000.
export HOME=/scratch/home HF_HOME=/scratch/hf REPO=/scratch/repo WORK=/scratch/work VENV=/scratch/work/venv-py312
export EVAL=/scratch/repo/data/eval/matura.jsonl PAPERS="2023-05 2024-05 2025-05 2026-05"
export LLAMA_SERVER=/scratch/work/llama.cpp/build/bin/llama-server
cd /scratch/repo; ln -sfn /scratch/work /scratch/repo/work
TS=$(date -u -d '+2 hours' +%Y%m%d-%H%M)
run() { # run <job_id> MODEL=.. MODE=..
  local id=$1; shift
  echo "$(date -u +%H:%M:%S) START $id" >> /scratch/chain.log
  env "$@" NAME=$id OUT=/scratch/out/$id bash infra/jobs/rehearsal.sh > /scratch/out/$id.console 2>&1
  echo "$(date -u +%H:%M:%S) END $id rc=$?" >> /scratch/chain.log
}
mkdir -p /scratch/out
run matura-infer-gemma4-12b-raw-heldout-$TS-g4r0 MODEL=gemma4-12b MODE=raw
run matura-infer-gemma4-12b-routed-heldout-$TS-g4t0 MODEL=gemma4-12b MODE=routed
run matura-infer-gemma4-12b-text-raw-heldout-$TS-img0 MODEL=gemma4-12b-text MODE=raw
run matura-infer-gemma4-12b-think-routed-heldout-$TS-g4k0 MODEL=gemma4-12b-think MODE=routed
echo "$(date -u +%H:%M:%S) CHAIN_DONE" >> /scratch/chain.log
