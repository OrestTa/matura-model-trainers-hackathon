#!/bin/bash
C=/workspace/codex-small-track-clean-v3; R=/scratch/claude-b15; L=$C/source/llama.cpp-694ec235484b3b0bf827ab7992a512d285f0e66b
cd $R
echo "$(date -u +%T) START b15-v1" > $R/status.txt
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 PYTHONPATH=$L/gguf-py timeout 1500s $C/venv/bin/python $R/train_b15.py --model /scratch/bielik/1.5b-bf16 --data $R/data --output-root $R/output --converter $L/convert_lora_to_gguf.py --run b15-v1 --steps 0 --routes closed_without_images,closed_with_images,open_without_images,open_with_images,essay --gpu-memory-fraction 0.30 > $R/training.log 2>&1
echo "$(date -u +%T) END b15-v1 rc=$?" >> $R/status.txt
