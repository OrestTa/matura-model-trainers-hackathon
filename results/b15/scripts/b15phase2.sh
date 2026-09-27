#!/bin/bash
R=/scratch/claude-b15; P=/scratch/final_e2e/work/packages/probny-2026-01; CK=/scratch/smoke_e2e/scripts/check_submission.py
AP=/workspace/codex-small-track-all-papers-v2/output/all-papers-full-epoch
# Gemma raw on the warm exam stack (reads pictures itself)
( cd /scratch/smoke_e2e && s=$(date +%s) && python scripts/run_exam.py $P --model gemma4-12b-exam --mode raw --concurrency 8 -o $R/answers-gemma-raw.json > $R/gemma-raw.log 2>&1; echo "$(date -u +%T) gemma raw rc=$? wall $(( $(date +%s)-s ))s" >> $R/status.txt; python $CK $R/answers-gemma-raw.json $P > $R/gemma-raw.check 2>&1; tail -2 $R/gemma-raw.check >> $R/status.txt ) &
until grep -q "SCORING DONE" $R/status.txt; do sleep 5; done
for a in base ours cleanv3; do (cd /scratch/smoke_e2e && python3 $CK $R/eval-$a/answers.json $P) > $R/eval-$a/check.txt 2>&1; echo "check $a: $(tail -1 $R/eval-$a/check.txt)" >> $R/status.txt; done
mkdir -p $R/ap; L=""; for r in closed_without_images closed_with_images open_without_images open_with_images essay; do cp $AP/$r/adapter-f16.gguf $R/ap/$r.gguf; L="$L --lora $R/ap/$r.gguf"; done
B=/scratch/llama-build/bin; export LD_LIBRARY_PATH=$B
$B/llama-server -m /scratch/codex-bielik-cap-2135/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf $L --lora-init-without-apply -ngl 99 -c 32768 -np 6 --jinja --reasoning-budget 0 --cache-ram 0 --host 127.0.0.1 --port 8094 > $R/server8094.log 2>&1 &
$B/llama-server -m /scratch/bielik/4.5b-q8/Bielik-4.5B-v3.0-Instruct.Q8_0.gguf -ngl 99 -c 32768 -np 6 --jinja --reasoning-budget 0 --cache-ram 0 --host 127.0.0.1 --port 8093 > $R/server8093.log 2>&1 &
until curl -sf localhost:8094/health >/dev/null; do sleep 2; done
( python3 /scratch/b15eval.py $P allpapers $R/eval-allpapers 8094 >> $R/status.txt 2>&1; (cd /scratch/smoke_e2e && python3 $CK $R/eval-allpapers/answers.json $P) > $R/eval-allpapers/check.txt 2>&1; echo "check allpapers: $(tail -1 $R/eval-allpapers/check.txt)" >> $R/status.txt ) &
until curl -sf localhost:8093/health >/dev/null; do sleep 2; done
python3 /scratch/b15eval.py $P plain $R/eval-b45 8093 >> $R/status.txt 2>&1; (cd /scratch/smoke_e2e && python3 $CK $R/eval-b45/answers.json $P) > $R/eval-b45/check.txt 2>&1; echo "check b45: $(tail -1 $R/eval-b45/check.txt)" >> $R/status.txt
wait; echo "$(date -u +%T) PHASE2 DONE" >> $R/status.txt
