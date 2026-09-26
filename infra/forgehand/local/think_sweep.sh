#!/bin/bash
# Thinking-budget sweep (Orest 22:34 CEST): base Gemma 4 12B QAT + mmproj, no adapter, THINK_FALLBACK=1, no OCR,
# practice papers probny-2026-01 + pokaz-2022-03 (+ every dev essay). The 2k arm is the practice-l40s raw run.
# Runs next to SD1 target building (inference only), so wall times are shared-card times; SD1 training waits for /scratch/sweep_done.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) SWEEP $*" >> $L; }
until grep -q "END practice-l40s v2" $L; do sleep 20; done  # shares the card with SD1 target building; SD1 training waits for /scratch/sweep_done
export HOME=/scratch/home HF_HOME=/scratch/hf THINK_FALLBACK=1 PATH=/scratch/work/venv-py312/bin:$PATH
cd /scratch/repo4
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
pkill -9 -f "llama-server.*--port 8100"
/scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8100 -ngl 999 --parallel 8 -c 262144 --jinja -fa on --no-webui > /scratch/out/sweep-server.log 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && break; sleep 5; done
log "server up"
NONESSAY=closed_text,closed_image,open_text,open_image
arm() { local key=$1 subs=$2 extra=$3; local s=$(date +%s); log "START $key"
  python scripts/subtype_sweep.py --base-url http://127.0.0.1:8100/v1 --papers dev --only-papers probny-2026-01,pokaz-2022-03 $extra \
    --subtypes $subs --candidates none --raw --model gemma4-12b-think-$key --concurrency 8 --out results/subtype/think-sweep/$key \
    > /scratch/out/sweep-$key.console 2>&1
  log "END $key rc=$? wall $(( $(date +%s)-s ))s"; }
arm tb4k $NONESSAY ""
arm tb8k $NONESSAY ""
arm te8k essay --all-essays
arm te16k essay --all-essays
arm tb1k $NONESSAY ""
arm te24k essay --all-essays
arm tb16k $NONESSAY ""
pkill -9 -f "llama-server.*--port 8100"; touch /scratch/sweep_done; log DONE
