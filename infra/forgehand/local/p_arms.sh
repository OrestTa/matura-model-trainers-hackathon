#!/bin/bash
# Practice-paper arms P1-P3 (harness thread 00:19 CEST): raw 2k on probny-2026-01 + pokaz-2022-03, :8100 after main_v9.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
until grep -q "V9 DONE" $L; do sleep 30; done
export HOME=/scratch/home HF_HOME=/scratch/hf THINK_FALLBACK=1 PATH=/scratch/work/venv-py312/bin:$PATH; cd /scratch/repo4
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
/scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8100 -ngl 999 --parallel 8 -c 262144 --jinja -fa on --no-webui > /scratch/out/p-server.log 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && break; sleep 5; done
C="python scripts/subtype_sweep.py --base-url http://127.0.0.1:8100/v1 --papers dev --only-papers probny-2026-01,pokaz-2022-03 --candidates none --raw --model gemma4-12b-think --concurrency 8"
s=$(date +%s); OPEN_BEST_OF=3 $C --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); OPEN_BEST_OF=3 PICTURE_DESCRIBE=1 $C --out results/subtype/practice-openbo3-describe > /scratch/out/practice-openbo3-describe.console 2>&1; log "END practice-openbo3-describe rc=$? wall $(( $(date +%s)-s ))s"
pkill -9 -f "llama-server.*--port 8100"; log "P arms done"
