#!/usr/bin/env bash
# Evaluate one trained adapter on one (or a few) held-out papers through the on-stage path,
# so each paper of each adapter can run on its own GPU and be graded the moment it lands.
# Pulls the single adapter (<train job OUT>/adapters/<model>/all) from S3, then runs
# rehearsal.sh with it. Env:
#   ADAPTER_S3=s3://<bucket>/out/<train job>/adapters/gemma4-12b   (required; "none" = base model)
#   PAPERS=2023-05                MODEL=gemma4-12b-think             MODE=raw    THINK_FALLBACK=1
# Only all/ is fetched: train.sh copies adapters with cp -L, so the per-type entries in S3 are
# full copies of all/, and serve_exam.sh would stack every copy as a separate --lora.
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${WORK:-$REPO/work}"
: "${ADAPTER_S3:?set ADAPTER_S3 to s3://.../adapters/<model> or none}"
export MODEL="${MODEL:-gemma4-12b-think}" MODE="${MODE:-raw}" PAPERS="${PAPERS:-2023-05}"
# As on stage: an answer lost to runaway thinking is re-asked once with thinking off (daabce0).
export THINK_FALLBACK="${THINK_FALLBACK:-1}"
if [ "$ADAPTER_S3" = none ]; then
  export ADAPTERS=/nonexistent
else
  export ADAPTERS="$WORK/adapters-eval"
  rm -rf "$ADAPTERS" && mkdir -p "$ADAPTERS/all"
  aws s3 cp --recursive "${ADAPTER_S3%/}/all/" "$ADAPTERS/all/" --only-show-errors \
    || { echo "adapter download failed: $ADAPTER_S3"; exit 1; }
  [ -f "$ADAPTERS/all/adapter.gguf" ] || { echo "no adapter.gguf under $ADAPTER_S3/all"; exit 1; }
fi
exec bash "$REPO/infra/jobs/rehearsal.sh"
