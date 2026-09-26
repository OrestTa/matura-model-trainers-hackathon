#!/usr/bin/env bash
# Continued pretraining (DAPT) on Polish history text, on any GPU box: `bash infra/jobs/dapt.sh`
#   1. (CPU) Polish Wikipedia + Wikisource + Wolne Lektury -> offline RAG index
#      ($CORPUS/rag/plwiki.sqlite) and history slices ($CORPUS/dapt/*.jsonl). Skipped when
#      they already exist. About 1 h on 4 vCPUs; needs ~20 GB disk. No GPU used.
#   2. (GPU) waits until the GPU is free, then one LoRA pass of next-token loss over the
#      best DAPT_TOKENS tokens -> $WORK/adapters/<model>/domain, merged model in
#      $WORK/models/<model>-dapt for the per-type SFT to start from.
# Env:
#   DAPT_MODEL=bielik-11b   key in configs/models.yaml
#   DAPT_TOKENS=20000000    token budget (~2-3 h for Bielik-11B on one L40S)
#   PREP_ONLY=1             only step 1 (safe while another job holds the GPU)
#   CORPUS=$WORK/corpus     where the corpora and index live (persistent across runs)
#   DAPT_MERGE=1            also write the merged model (22 GB for Bielik-11B)
#   FINEWEB=fineweb2hq      also filter the Polish web for history text (scripts/corpus/fineweb.py;
#                           180 GB streamed shard by shard, ~2 GB kept); FINEWEB= to skip,
#                           FINEWEB=fineweb2 for the full 226 GB FineWeb-2
source "$(dirname "$0")/common.sh"
MODEL="${DAPT_MODEL:-bielik-11b}"; TOKENS="${DAPT_TOKENS:-20000000}"
CORPUS="${CORPUS:-$WORK/corpus}"
pip install -q pyarrow zstandard

if [ -s "$CORPUS/rag/plwiki.sqlite" ] && [ -s "$CORPUS/dapt/plwiki_history.jsonl" ]; then
  step "reusing corpora in $CORPUS"
else
  step "downloading Polish Wikipedia"
  python scripts/corpus/plwiki.py download --src "$CORPUS/src/plwiki" || finish 1
  step "building the RAG index and the Wikipedia history slice"
  python scripts/corpus/plwiki.py build --src "$CORPUS/src/plwiki" --eval "$EVAL" \
    --db "$CORPUS/rag/plwiki.sqlite" --dapt "$CORPUS/dapt/plwiki_history.jsonl" || finish 1
  step "adding Wikisource and Wolne Lektury (SpeakLeash)"
  python scripts/corpus/speakleash.py download --src "$CORPUS/src/speakleash" &&
  python scripts/corpus/speakleash.py build --src "$CORPUS/src/speakleash" --eval "$EVAL" \
    --db "$CORPUS/rag/plwiki.sqlite" --dapt-dir "$CORPUS/dapt" || step "SpeakLeash failed; Wikipedia only"
fi
FINEWEB="${FINEWEB-fineweb2hq}"
if [ -n "$FINEWEB" ] && [ ! -s "$CORPUS/dapt/${FINEWEB}_history.jsonl" ]; then
  step "filtering $FINEWEB (Polish web) for history text"
  python scripts/corpus/fineweb.py --dataset "$FINEWEB" --workers 3 --eval "$EVAL" \
    --out "$CORPUS/src/fineweb" --tmp "$CORPUS/src/fineweb/tmp" --dapt-dir "$CORPUS/dapt" \
    || step "FineWeb filter failed; continuing without it"
fi
if [ ! -s "$CORPUS/rl/wiki_order.jsonl" ]; then
  step "RL question sets (PolQA, Global-MMLU history, Wikipedia years/ordering)"
  python scripts/corpus/rl_sets.py --src "$CORPUS/src/rl" --dapt "$CORPUS/dapt/plwiki_history.jsonl" \
    --out "$CORPUS/rl" --eval "$EVAL" || step "RL sets failed; continuing"
fi
cp "$CORPUS/rag/plwiki.meta.json" "$OUT/" 2>/dev/null
wc -l "$CORPUS"/dapt/*.jsonl "$CORPUS"/rl/*.jsonl
[ "${PREP_ONLY:-0}" = 1 ] && finish 0

until [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1)" -lt 2000 ]; do
  step "waiting for a free GPU"; sleep 60
done
step "DAPT $MODEL on $TOKENS tokens"
python scripts/train_dapt.py --model "$MODEL" --data "$CORPUS"/dapt/*.jsonl \
  --out-dir "$WORK/adapters" --max-tokens "$TOKENS" --merge-dir "$WORK/models" \
  $([ "${DAPT_MERGE:-1}" = 1 ] && echo --merge) || finish 1
cp "$WORK/adapters/$MODEL/domain/train_meta.json" "$OUT/dapt_meta.json"
finish 0
