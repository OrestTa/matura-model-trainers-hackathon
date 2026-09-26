#!/bin/bash
# Essay arms (harness thread, 22:48 CEST) on the 12 dev essays, gemma4-12b-think8k (16k essay budget), own :8101 server (4 slots x 40k) beside main_v9 on :8100 (best-score thread 23:37 CEST).
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
export THINK_FALLBACK=1; cd /scratch/repo4
C="python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers dev --only-papers none --all-essays --model gemma4-12b-think8k --concurrency 4"
s=$(date +%s); $C --subtypes essay --candidates base,plan,guard,plan_guard --out results/subtype/essay-grid > /scratch/out/essay-grid.console 2>&1; log "END essay-grid rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); ESSAY_TARGET_WORDS=550 ESSAY_MIN_WORDS=350 $C --candidates none --raw --out results/subtype/essay-len > /scratch/out/essay-len.console 2>&1; log "END essay-len rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); ESSAY_BEST_OF=3 ESSAY_TARGET_WORDS=550 ESSAY_MIN_WORDS=350 $C --subtypes essay --candidates plan --raw --out results/subtype/essay-bo3 > /scratch/out/essay-bo3.console 2>&1; log "END essay-bo3 rc=$? wall $(( $(date +%s)-s ))s"
# E4 (raw think8k on the practice papers) is covered by sweep arms tb8k + te16k.
