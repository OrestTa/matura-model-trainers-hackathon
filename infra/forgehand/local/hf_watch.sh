#!/bin/bash
# Uploads each new adapter dir (with adapter.gguf) on the box to a private orestta HF repo, once.
L=/scratch/master_chain.log; export HOME=/scratch/home HF_HOME=/scratch/hf
while true; do
  for d in /scratch/work/adapters-*/all; do
    n=$(basename $(dirname $d)); n=${n#adapters-}
    [ -f $d/adapter.gguf ] && [ ! -f /scratch/out/hf_done_$n ] || continue
    sleep 10  # let the move/convert settle
    /scratch/work/venv-py312/bin/python /scratch/hf_up.py orestta/matura-gemma4-12b-lora-$n $d > /scratch/out/hf_up_$n.log 2>&1 \
      && touch /scratch/out/hf_done_$n && echo "$(date -u +%T) HF: orestta/matura-gemma4-12b-lora-$n" >> $L
  done
  sleep 30
done
