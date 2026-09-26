#!/bin/bash
export HOME=/scratch/home HF_HOME=/scratch/hf THINK_FALLBACK=1 PATH=/scratch/work/venv-py312/bin:$PATH
M=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/gemma-4-12b-it-qat-q4_0.gguf)
P=$(ls /scratch/hf/hub/models--google--gemma-4-12B-it-qat-q4_0-gguf/snapshots/*/mmproj-gemma-4-12b-it-qat-q4_0.gguf)
/scratch/work/llama.cpp/build/bin/llama-server -m $M --mmproj $P --port 8101 -ngl 999 --parallel 4 -c 163840 --jinja -fa on --no-webui > /scratch/out/essay-server.log 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8101/v1/models >/dev/null && break; sleep 5; done
echo "$(date -u +%T) V9 essay server :8101 up" >> /scratch/master_chain.log
bash /scratch/essay_arms_8101.sh
pkill -9 -f "llama-server.*--port 8101"
