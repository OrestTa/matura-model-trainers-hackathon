#!/bin/bash
# R2: stage path on the 4 held-out papers (jury number); E9: essay bo5plan on dev essays (harness thread 06:38 CEST).
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
export HOME=/scratch/home HF_HOME=/scratch/hf PATH=/scratch/work/venv-py312/bin:$PATH WORK=/scratch/work THINK_FALLBACK=1
cd /scratch/repo4
export OUT=/scratch/repo4/results/rehearsal/stage-heldout EVAL=/scratch/repo4/data/eval/matura.jsonl; rm -rf $OUT; mkdir -p $OUT
s=$(date +%s); log "START rehearsal stage-heldout"
ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 MODEL=gemma4-12b-exam MODE=subtype CONCURRENCY=8 PAPERS="2023-05 2024-05 2025-05 2026-05" \
  bash infra/jobs/rehearsal.sh > /scratch/out/rehearsal-heldout.console 2>&1
log "END rehearsal stage-heldout rc=$? wall $(( $(date +%s)-s ))s"
unset OUT EVAL
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
GGML_CUDA_DISABLE_GRAPHS=1 /scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8101 -ngl 999 --parallel 8 -c 196608 --jinja -fa on --no-webui --cache-ram 0 --load-mode none > /scratch/out/essay-server-e9.log 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8101/v1/models >/dev/null && break; sleep 5; done
s=$(date +%s); ESSAY_BEST_OF=5 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers dev --only-papers none --all-essays --subtypes essay --candidates plan --model gemma4-12b-think8k --concurrency 8 --out results/subtype/essay-bo5plan > /scratch/out/essay-bo5plan.console 2>&1
log "END essay-bo5plan rc=$? wall $(( $(date +%s)-s ))s"
pkill -f "llama-server.*--port 8101"
