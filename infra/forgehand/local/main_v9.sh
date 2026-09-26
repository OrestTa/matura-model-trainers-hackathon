#!/bin/bash
# v9 (coordinator 22:45 CEST, Modal out): 1 held-out rerun raw 2k vs harness (heldout-v5), 2 thinking-budget sweep
# (4k, 8k first), 3 essay arms. Own llama-server on :8100 (base QAT + mmproj, no adapter), next to SD1's build on :8090.
# Shared box (Codex): only our own processes are stopped, by pid/port.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
export HOME=/scratch/home HF_HOME=/scratch/hf THINK_FALLBACK=1 PATH=/scratch/work/venv-py312/bin:$PATH
cd /scratch/repo4
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
pkill -9 -f "llama-server.*--port 8100"
/scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8100 -ngl 999 --parallel 8 -c 262144 --jinja -fa on --no-webui > /scratch/out/v9-server.log 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && break; sleep 5; done
log "server :8100 up"
SW="python scripts/subtype_sweep.py --base-url http://127.0.0.1:8100/v1 --concurrency 8"
rm -rf /tmp/smoke-v5
$SW --papers heldout --candidates none --raw --selected --model gemma4-12b-think --per-subtype 1 --out /tmp/smoke-v5 > /scratch/out/smoke-v5.console 2>&1
log "smoke-v5 rc=$? blanks=$(cat /tmp/smoke-v5/*/*/answers.jsonl 2>/dev/null | python3 -c 'import sys,json;r=[json.loads(l) for l in sys.stdin];print(sum(1 for x in r if not (x.get("answer") or "").strip()), "of", len(r))')"
s=$(date +%s); log "START heldout-v5"
$SW --papers heldout --candidates none --raw --selected --model gemma4-12b-think --out results/subtype/heldout-v5 > /scratch/out/heldout-v5.console 2>&1
log "END heldout-v5 rc=$? wall $(( $(date +%s)-s ))s"
NONESSAY=closed_text,closed_image,open_text,open_image
arm() { local key=$1 subs=$2 extra=$3; local s=$(date +%s); log "START sweep $key"
  $SW --papers dev --only-papers probny-2026-01,pokaz-2022-03 $extra --subtypes $subs --candidates none --raw \
    --model gemma4-12b-think-$key --out results/subtype/think-sweep/$key > /scratch/out/sweep-$key.console 2>&1
  log "END sweep $key rc=$? wall $(( $(date +%s)-s ))s"; }
arm tb4k $NONESSAY ""
arm tb8k $NONESSAY ""
arm te8k essay --all-essays
arm te16k essay --all-essays
arm tb1k $NONESSAY ""
arm te24k essay --all-essays
arm tb16k $NONESSAY ""
touch /scratch/sweep_done; log "sweep done (SD1 training may start)"
[ -f /scratch/essay_arms.sh ] && { log "START essay arms"; bash /scratch/essay_arms.sh; log "END essay arms rc=$?"; }
pkill -9 -f "llama-server.*--port 8100"; log DONE
