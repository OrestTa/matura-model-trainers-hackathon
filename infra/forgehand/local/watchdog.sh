#!/bin/bash
# Restarts our :8100 llama-server if it dies (OOM-killed 23:03Z) while main_v9.sh (pid 109781) runs.
# --no-mmap keeps host RAM low (box: 30 GB, no swap, two servers). Touches only port 8100.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) V9 $*" >> $L; }
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
start() { GGML_CUDA_DISABLE_GRAPHS=1 nohup /scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8100 -ngl 999 --parallel 8 -c 262144 --jinja -fa on --no-webui --no-mmap >> /scratch/out/v9-server.log 2>&1 &
  for i in $(seq 120); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && break; sleep 5; done; log "watchdog: :8100 restarted (no-mmap)"; }
while kill -0 109781 2>/dev/null && [ ! -f /scratch/sweep_done ]; do
  if ! curl -sf -m 10 http://127.0.0.1:8100/health >/dev/null && ! pgrep -f "llama-server.*--port 8100" >/dev/null; then start; fi
  sleep 20
done
