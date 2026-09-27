#!/bin/bash
# Practice-paper arms P1-P3 (harness thread 00:19 CEST): raw 2k on probny-2026-01 + pokaz-2022-03, run inside main_v9 before tb1k (harness 00:20 CEST).
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
export HOME=/scratch/home HF_HOME=/scratch/hf THINK_FALLBACK=1 PATH=/scratch/work/venv-py312/bin:$PATH; cd /scratch/repo4
C="python scripts/subtype_sweep.py --base-url http://127.0.0.1:8100/v1 --papers dev --only-papers probny-2026-01,pokaz-2022-03 --candidates none --raw --model gemma4-12b-think --concurrency 8"
s=$(date +%s); OPEN_BEST_OF=3 $C --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rc=$? wall $(( $(date +%s)-s ))s"
# 01:25 CEST: :8100 was OOM-killed at 23:03Z during P1; P1/P2 results are void. Wait for the watchdog restart, rerun P2, P3, then P1 at concurrency 4 (harness thread).
w8100() { for i in $(seq 180); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && return 0; sleep 5; done; return 1; }
w8100; rm -rf results/subtype/practice-describe
s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rerun rc=$? wall $(( $(date +%s)-s ))s"
w8100; s=$(date +%s); OPEN_BEST_OF=3 PICTURE_DESCRIBE=1 $C --out results/subtype/practice-openbo3-describe > /scratch/out/practice-openbo3-describe.console 2>&1; log "END practice-openbo3-describe rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3
s=$(date +%s); OPEN_BEST_OF=3 ${C/--concurrency 8/--concurrency 4} --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rerun-c4 rc=$? wall $(( $(date +%s)-s ))s"
# 01:50 CEST: the OOM came from llama-server's 8 GiB host prompt cache (x2 servers). :8100 now runs --cache-ram 0; rerun P2, P3, P1 (c4).
w8100; rm -rf results/subtype/practice-describe; s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rerun2 rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3-describe; s=$(date +%s); OPEN_BEST_OF=3 PICTURE_DESCRIBE=1 $C --out results/subtype/practice-openbo3-describe > /scratch/out/practice-openbo3-describe.console 2>&1; log "END practice-openbo3-describe rerun2 rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3; s=$(date +%s); OPEN_BEST_OF=3 ${C/--concurrency 8/--concurrency 4} --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rerun2-c4 rc=$? wall $(( $(date +%s)-s ))s"
# rerun2 of P2 raced the server restart (6 s, all refused); run it once more.
w8100; rm -rf results/subtype/practice-describe; s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rerun3 rc=$? wall $(( $(date +%s)-s ))s"
