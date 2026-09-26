#!/usr/bin/env bash
# Parent-approved launch only. Unique owned scratch; no shared-process mutation.
set -euo pipefail
umask 077
ROOT=${1:?extracted owned smoke bundle root}
case "$ROOT" in /scratch/codex-qwen08-caption-*) ;; *) exit 2;; esac
OUT=${2:?new owned output directory}
case "$OUT" in /workspace/codex-small-track-qwen08-caption-*) ;; *) exit 2;; esac
BASE='https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/6ab461498e2023f6e3c1baea90a8f0fe38ab64d0'
for FILE in Qwen3.5-0.8B-Q4_K_M.gguf mmproj-F16.gguf; do
 test ! -e "$ROOT/$FILE"
 curl -fL --max-time 90 --retry 0 "$BASE/$FILE" -o "$ROOT/$FILE"
done
python3 - "$ROOT" <<'PY'
import sys,hashlib
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r));from qwen08_visual_smoke import ARTIFACTS,sha
for a in ARTIFACTS:
 p=r/a['filename'];assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256']
p=Path('/scratch/llama-build/bin/llama-server');assert sha(p)=='efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf'
PY
test "$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)" -gt 6000
python3 "$ROOT/offline_server.py" "$ROOT/server-network-proof.json" /scratch/llama-build/bin/llama-server -m "$ROOT/Qwen3.5-0.8B-Q4_K_M.gguf" --mmproj "$ROOT/mmproj-F16.gguf" -ngl 99 -c 4096 -np 1 -t 1 -b 128 -ub 64 --jinja --reasoning-budget 0 --host 127.0.0.1 --port 18934 > "$ROOT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep 2
timeout --signal=TERM --kill-after=10s 240s python3 "$ROOT/qwen08_visual_smoke.py" --root "$ROOT" --output "$OUT"
