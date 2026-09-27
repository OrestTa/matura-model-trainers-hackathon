#!/usr/bin/env python3
"""Stage an exact selected configuration as a self-contained offline harness."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime',type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve existing package')
 c=json.loads(a.config.read_text());a.output.mkdir(parents=True);weights=[]
 for key,art in list(c['artifacts'].items())+[(x['role']+'-'+str(i),x) for i,x in enumerate(c.get('auxiliary_artifacts',[]))]:
  src=Path(art['filename']);src=src if src.is_absolute() else ROOT/src
  target='weights/router.json' if art.get('role')=='router' else ('weights/ocr/'+src.name if src.suffix=='.traineddata' else 'weights/'+('base.gguf' if key=='model' else key+'.gguf'))
  if not src.is_file():raise ValueError('Missing artifact '+str(src))
  if src.stat().st_size!=art['bytes'] or digest(src)!=art['sha256']:raise ValueError('Artifact mismatch '+str(src))
  dst=a.output/target;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  weights.append({'path':target,'bytes':art['bytes'],'sha256':art['sha256'],'source':art.get('recovery',{'status':'Packaged exact local artifact; upstream recovery recorded separately','repo':art.get('repo'),'revision':art.get('revision'),'filename':art['filename']})});art['filename']=target
 total=sum(x['bytes'] for x in weights);assert total<=8800000000;c['aggregate_weight_bytes']=total
 for r in c['routes'].values():r['base_url']='http://127.0.0.1:18935/v1'
 (a.output/'config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2));(a.output/'weights-manifest.json').write_text(json.dumps({'name':c['name'],'aggregate_weight_bytes':total,'weights':weights,'evaluation_status':'Awaiting final matched evaluation; training-set score only'},indent=2))
 for name in ['package_run.py','harness.py','infer.py','classifier.py','train_router.py','official_format.py','ocr.py','voting.py','offline_server.py']:
  shutil.copyfile(ROOT/'scripts/small_track'/name,a.output/('run.py' if name=='package_run.py' else name))
 if a.runtime:
  server=a.runtime/'bin/llama-server'
  if not server.is_file() or digest(server)!='efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf':raise ValueError('Unsupported runtime binary')
  shutil.copytree(a.runtime,a.output/'runtime')
 (a.output/'run.sh').write_text('''#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export LD_LIBRARY_PATH="$ROOT/runtime/lib:${LD_LIBRARY_PATH:-}"
exec python3 "$ROOT/run.py" --server "$ROOT/runtime/bin/llama-server" "$@"
''');(a.output/'run.sh').chmod(0o755)
 (a.output/'check-runtime.sh').write_text('#!/bin/sh\nset -eu\nROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexport LD_LIBRARY_PATH="$ROOT/runtime/lib:${LD_LIBRARY_PATH:-}"\ncommand -v python3 >/dev/null\ncommand -v tesseract >/dev/null\ncommand -v nvidia-smi >/dev/null\npython3 -c "import ctypes; ctypes.CDLL(\'libseccomp.so.2\')"\ntest -x "$ROOT/runtime/bin/llama-server"\n"$ROOT/runtime/bin/llama-server" --version\ntesseract --version\nprintf \'%s\\n\' \'Runtime prerequisites present; this does not grade the model.\'\n');(a.output/'check-runtime.sh').chmod(0o755)
 (a.output/'README.md').write_text('''# Bielik offline submission harness

Pass a NEW organizer exam JSON path and its adjacent original images. No fixed exam, key, rubric, previous answers or judge is included. One shared Bielik1.5B Q8_0 base plus five F16 specialist adapters, a learned classifier and Polish/English Tesseract weights. See weights-manifest.json for exact aggregate bytes and hashes. All weights must fit8.8GB.

Linux x86_64 CUDA host: Python3.11+, NVIDIA driver, libseccomp.so.2, Tesseract5 executable are runtime prerequisites. No pip packages are needed. runtime/bin/llama-server plus runtime/lib must be installed from the verified runtime archive before inference. There are no downloads in run.sh or run.py. Check all runtime-manifest hashes before use. The host needs6GiB freeRAM and6GiB freeGPU memory. Port18935 must be free.

Dry run validates weights, organizer schema, exact IDs, original image checksums and route plan; it emits explicitly EMPTY dry-run answers:

    ./run.sh --exam /absolute/path/new-exam/exam.json --output /absolute/path/new-dryrun

Actual inference recomputes routing and image-only OCR from the supplied exam, then writes organizer-format answers.json and detailed per-item logs:

    ./run.sh --exam /absolute/path/new-exam/exam.json --output /absolute/path/new-result --run

The supplied offline_server enforces outboundTCP/UDP denial for the model; OCR child denies network. Only the owned model process is stopped on exit. No external inference/judging is used. Preserve output directories; existing directories are rejected. Allpapers training includes2023 exam exposure, so reproduction on2023 is training-set performance, not an unseen-exam claim. OCR is not semantic vision.
''')
 hashes={str(f.relative_to(a.output)):digest(f) for f in a.output.rglob('*') if f.is_file() and 'weights' not in f.relative_to(a.output).parts}
 (a.output/'runtime-code-manifest.json').write_text(json.dumps(hashes,indent=2));print(json.dumps({'package':str(a.output),'aggregate_weight_bytes':total,'runtime_included':bool(a.runtime)}))
if __name__=='__main__':main()
