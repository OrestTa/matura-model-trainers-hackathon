#!/bin/bash
# Stage dress rehearsal (best-score freeze d10726c, harness thread 02:59 CEST) on probny-2026-01.
# Waits for E8 (:8101) and P1/P2 (:8100) to finish, stops our :8101 essay server (pid 121889) for VRAM,
# holds main_v9's remaining arms (they wait for /scratch/rehearsal_done), then runs rehearsal.sh on :8000.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
until grep -q "END essay-ragbo3plan" $L; do sleep 30; done
kill 121889; sleep 5; kill -9 121889 2>/dev/null; log "stopped :8101 essay server for the rehearsal (E7 deferred)"
until grep -q "END practice-describe rerun3" $L; do sleep 30; done
export HOME=/scratch/home HF_HOME=/scratch/hf PATH=/scratch/work/venv-py312/bin:$PATH WORK=/scratch/work
export OUT=/scratch/repo4/results/rehearsal/stage-probny EVAL=/scratch/repo4/data/eval/matura_all.jsonl
cd /scratch/repo4; rm -rf $OUT; mkdir -p $OUT
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader >> $OUT/gpu_before.txt
s=$(date +%s); log "START rehearsal stage-probny"
ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1 MODEL=gemma4-12b-exam MODE=subtype CONCURRENCY=8 PAPERS=probny-2026-01 \
  bash infra/jobs/rehearsal.sh > /scratch/out/rehearsal-stage.console 2>&1
log "END rehearsal stage-probny rc=$? wall $(( $(date +%s)-s ))s"
touch /scratch/rehearsal_done
