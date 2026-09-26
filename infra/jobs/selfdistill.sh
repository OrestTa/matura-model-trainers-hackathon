#!/usr/bin/env bash
# One shard of SD1's self-distilled targets (scripts/build_selfdistill.py) on a rented GPU (Nebius/Modal).
# The base Gemma 4 12B QAT q4_0 + mmproj on llama-server, thinking on; writes $OUT/selfdistill-$SHARD.jsonl.
#   SHARD=a|b   item-id list results/sd1_shard_nebius_$SHARD.txt (or IDS=<file>)
#   SAMPLES=4 SLOTS=16
source "$(dirname "$0")/common.sh"
IDS="${IDS:-$REPO/results/sd1_shard_nebius_${SHARD:?SHARD=a or b}.txt}"
step "past papers with pictures (CKE, not in the repo)"
python -m pip install -q pymupdf
python scripts/fetch_matura.py --papers all --images -o data/eval/matura_all.jsonl || finish 1
python scripts/fetch_matura.py --images -o data/eval/matura.jsonl || finish 1
ensure_llama_server || { step "no llama-server"; finish 1; }
GGUF=$(python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','gemma-4-12b-it-qat-q4_0.gguf'))")
MMPROJ=$(python -c "from huggingface_hub import hf_hub_download as h; print(h('google/gemma-4-12B-it-qat-q4_0-gguf','mmproj-gemma-4-12b-it-qat-q4_0.gguf'))")
SLOTS=${SLOTS:-16}
GGML_CUDA_DISABLE_GRAPHS=1 "$LLAMA_SERVER" -m "$GGUF" --mmproj "$MMPROJ" --port 8090 -ngl 999 --parallel $SLOTS \
  -c $((SLOTS * 8192)) --jinja -fa on --no-webui > "$OUT/server.log" 2>&1 &
for i in $(seq 120); do curl -sf http://127.0.0.1:8090/v1/models >/dev/null && break; sleep 5; done
curl -sf http://127.0.0.1:8090/v1/models >/dev/null || { tail -30 "$OUT/server.log"; finish 1; }
step "smoke (2 items)"
python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source data/eval/matura_all.jsonl --image-root . \
  --only-ids "$IDS" --limit 2 --samples 1 -o "$OUT/smoke.jsonl" || finish 1
step "building $(wc -l < "$IDS") items"
python scripts/build_selfdistill.py --url http://127.0.0.1:8090 --source data/eval/matura_all.jsonl --image-root . \
  --only-ids "$IDS" --samples "${SAMPLES:-4}" --rationalize --workers $SLOTS -o "$OUT/selfdistill-${SHARD:-x}.jsonl" \
  2>&1 | tee "$OUT/build.log"
finish $([ -s "$OUT/selfdistill-${SHARD:-x}.jsonl" ] && echo 0 || echo 1)
