#!/usr/bin/env bash
# Run only after parent approval on the shared VM. No credential required.
set -euo pipefail
umask 077
ROOT_DIR=${1:?own scratch root required}
BUNDLE_DIR=${2:?directory containing trainer and clean-v3 data required}
case "$ROOT_DIR" in /workspace/codex-small-track-clean-v3*) ;; *) echo 'Refusing non-owned scratch path' >&2; exit 2;; esac
mkdir -p "$ROOT_DIR"
[ ! -e "$ROOT_DIR/venv" ] || { echo 'Refusing to modify an existing environment' >&2; exit 2; }
python3 -m venv --system-site-packages "$ROOT_DIR/venv"
PY="$ROOT_DIR/venv/bin/python"
# Reuse system torch read-only. Prevent pip from replacing it or upgrading shared packages.
"$PY" -c 'import torch; print("torch=="+torch.__version__.split("+")[0])' > "$ROOT_DIR/torch-constraint.txt"
"$PY" -m pip install --constraint "$ROOT_DIR/torch-constraint.txt" 'transformers==5.17.0' 'peft==0.21.0' 'accelerate==1.15.0' sentencepiece
"$PY" - "$ROOT_DIR" <<'PY'
import importlib.metadata as md,json,sys,torch
from pathlib import Path
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import LoraConfig,get_peft_model
root=Path(sys.argv[1]);assert Path(sys.prefix).resolve()==(root/'venv').resolve()
assert torch.version.cuda and torch.cuda.is_available(),'CUDA torch required'
(root/'runtime-versions.json').write_text(json.dumps({x:md.version(x) for x in ['torch','transformers','peft','accelerate','huggingface_hub','safetensors']},indent=2))
PY
mkdir "$ROOT_DIR/source"
# Public pinned converter; do not use or modify another agent's checkout.
curl --fail --location --silent --show-error 'https://github.com/ggml-org/llama.cpp/archive/694ec235484b3b0bf827ab7992a512d285f0e66b.tar.gz' -o "$ROOT_DIR/source/llama.tar.gz"
tar -xzf "$ROOT_DIR/source/llama.tar.gz" -C "$ROOT_DIR/source"
"$PY" - "$ROOT_DIR" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
from huggingface_hub import snapshot_download
root=Path(sys.argv[1]);model=root/'model';os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
snapshot_download('cpral/Bielik-1.5B-v3.0-Instruct-ungated',revision='a3a660b10fdba3a7b03c3349567e54d8875f9ac9',local_dir=model,allow_patterns=['*.json','*.safetensors','*.jinja','*.txt'],token=False)
p=model/'model.safetensors'
with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
assert p.stat().st_size==3193073112 and h=='3c337d1d0d3f8cafb27f617b97a9a0cf70a2067648cb3946311e2fe370c28978'
(root/'model-provenance.json').write_text(json.dumps({'repo':'cpral/Bielik-1.5B-v3.0-Instruct-ungated','revision':'a3a660b10fdba3a7b03c3349567e54d8875f9ac9','bytes':p.stat().st_size,'sha256':h},indent=2))
PY
cp "$BUNDLE_DIR/train_bielik_real_native.py" "$ROOT_DIR/"
cp -R "$BUNDLE_DIR/data" "$ROOT_DIR/data"
"$PY" - "$ROOT_DIR" <<'PY'
import hashlib,json,sys,importlib.util
from pathlib import Path
root=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('trainer',root/'train_bielik_real_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=root/'data/manifest.json';h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==m.CLEAN_MANIFEST_SHA
manifest=json.loads(p.read_text());count=0
for route,entry in manifest['files'].items():
 p=root/'data'/route/'train.jsonl';assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
 for line in p.read_text().splitlines():m.validate_real_row(json.loads(line),h);count+=1
assert count==138
print('Staged138 verified rows. No training launched.')
PY
