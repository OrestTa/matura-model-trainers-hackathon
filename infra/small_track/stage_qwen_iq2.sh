#!/bin/bash
set -euo pipefail
ROOT=/scratch/codex-qwen35-iq2
mkdir -p "$ROOT/weights"
python3 - "$ROOT" <<'PY'
import hashlib,json,sys,urllib.request
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config.json').read_text())
for item in c['files']:
 p=root/'weights'/item['file']
 if not p.exists():
  url='https://huggingface.co/'+c['repo']+'/resolve/'+c['revision']+'/'+item['file']
  tmp=p.with_suffix('.partial')
  with urllib.request.urlopen(url,timeout=60) as response,tmp.open('wb') as out:
   while chunk:=response.read(8*1024*1024):out.write(chunk)
  assert tmp.stat().st_size==item['bytes']
  with tmp.open('rb') as handle:assert hashlib.file_digest(handle,'sha256').hexdigest()==item['sha256']
  tmp.rename(p)
 with p.open('rb') as handle:assert hashlib.file_digest(handle,'sha256').hexdigest()==item['sha256']
 assert p.stat().st_size==item['bytes'];print(item['file'],'verified',flush=True)
PY
