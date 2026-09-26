#!/bin/bash
# Picture LoRA V1 (best-score thread, Orest OK 21:33 CEST): 135 past-paper picture items, frozen vision tower, LoRA on text layers.
L=/scratch/master_chain.log; log() { echo "$(date -u +%H:%M:%S) $*" >> $L; }
export HOME=/scratch/home HF_HOME=/scratch/hf
V=/scratch/work/venv-py312/bin; cd /scratch/repo4
$V/pip install -q pillow
rm -rf /scratch/work/vdata; mkdir -p /scratch/work/vdata && tar xzf /scratch/vision_pack.tgz -C /scratch/work/vdata && mv /scratch/work/vdata/vision.jsonl /scratch/work/vdata/all.jsonl
log "V1 data: $(wc -l < /scratch/work/vdata/all.jsonl) rows"
run() { $V/python scripts/train_lora.py --model gemma4-12b --category all --data-dir /scratch/work/vdata --out-dir /scratch/work/adapters-V1 --vision --epochs ${EP:-2} --batch 1 --grad-accum $1 --rank 16 --lr 1e-4 --min-examples 10; }
run 8 || { log "V1 failed at grad-accum 8, retrying at 16"; run 16; } || { log V1_TRAIN_FAILED; exit 1; }
D=/scratch/work/adapters-V1/gemma4-12b/all
$V/python /scratch/work/llama.cpp/convert_lora_to_gguf.py --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized --outtype f16 --outfile $D/adapter.gguf $D || { log V1_GGUF_FAILED; exit 1; }
ls -la $D/adapter.gguf >> $L; log "V1 GGUF written"
$V/python /scratch/hf_up.py orestta/matura-gemma4-12b-lora-V1 $D > /scratch/out/hf_up_V1.log 2>&1 && log "HF: orestta/matura-gemma4-12b-lora-V1"
