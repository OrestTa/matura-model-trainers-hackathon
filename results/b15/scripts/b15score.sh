#!/bin/bash
R=/scratch/claude-b15; P=/scratch/final_e2e/work/packages/probny-2026-01; CV=/workspace/codex-small-track-clean-v3/output/clean-v3-full-epoch
M=/scratch/codex-bielik-cap-2135/Bielik-1.5B-v3.0-Instruct-Q8_0.gguf
pkill -f "llama-server.*--port 8091"; sleep 3
mkdir -p $R/cv3; for r in closed_without_images closed_with_images open_without_images open_with_images essay; do cp $CV/$r/adapter-f16.gguf $R/cv3/$r.gguf; done
L=""; for r in closed_without_images closed_with_images open_without_images open_with_images essay; do L="$L --lora $R/output/b15-v1/$r/adapter-f16.gguf"; done
for r in closed_without_images closed_with_images open_without_images open_with_images essay; do L="$L --lora $R/cv3/$r.gguf"; done
LD_LIBRARY_PATH=/scratch/llama-build/bin /scratch/llama-build/bin/llama-server -m $M $L --lora-init-without-apply -ngl 99 -c 32768 -np 6 --jinja --reasoning-budget 0 --cache-ram 0 --host 127.0.0.1 --port 8091 > $R/server8091.log 2>&1 &
until curl -sf localhost:8091/health >/dev/null; do sleep 2; done
curl -s localhost:8091/lora-adapters > $R/lora-adapters.json
echo "$(date -u +%T) server up" >> $R/status.txt
for a in base ours cleanv3; do
  python3 /scratch/b15eval.py $P $a $R/eval-$a >> $R/status.txt 2>&1
  (cd /scratch/final_e2e && python3 scripts/check_submission.py $R/eval-$a/answers.json $P) > $R/eval-$a/check.txt 2>&1; tail -2 $R/eval-$a/check.txt >> $R/status.txt
done
echo "$(date -u +%T) SCORING DONE" >> $R/status.txt
