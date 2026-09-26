"""Bounded CPU-only offline OCR; uploads candidate inputs and their images only."""
import modal,json,base64,time
from pathlib import Path
app=modal.App('matura-small-ocr-independent')
image=modal.Image.debian_slim(python_version='3.12').apt_install('tesseract-ocr','tesseract-ocr-pol','tesseract-ocr-eng','libseccomp2')
if modal.is_local():image=image.add_local_file('scripts/small_track/ocr.py','/app/ocr.py')
@app.function(image=image,cpu=2,memory=2048,timeout=300,max_containers=1,retries=0)
def run(rows,images):
    import subprocess,sys,importlib.util
    root=Path('/inputs');(root/'images').mkdir(parents=True)
    for name,data in images.items():(root/'images'/name).write_bytes(base64.b64decode(data))
    (root/'candidate.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    spec=importlib.util.spec_from_file_location('ocr','/app/ocr.py');ocr=importlib.util.module_from_spec(spec);spec.loader.exec_module(ocr)
    blocked=False
    try:ocr.run_isolated([sys.executable,'-c','import socket; socket.socket()'])
    except subprocess.CalledProcessError:blocked=True
    if not blocked:raise RuntimeError('network isolation failed')
    subprocess.run([sys.executable,'/app/ocr.py','--input','/inputs/candidate.jsonl','--output','/outputs/ocr-candidate.jsonl','--artifact-dir','/outputs/ocr-assets','--image-root','/inputs'],check=True)
    return {'network_socket_denied':blocked,'files':{str(p.relative_to('/outputs')):base64.b64encode(p.read_bytes()).decode() for p in Path('/outputs').rglob('*') if p.is_file()}}
@app.local_entrypoint()
def main():
    source=Path('data/small_track/official_mock_v1');rows=[json.loads(s) for s in (source/'canonical-b0-candidate.jsonl').read_text().splitlines()]
    images={p.name:base64.b64encode(p.read_bytes()).decode() for p in (source/'images').glob('*.png')}
    result=run.remote(rows,images);dest=source/'ocr-offline-v1';dest.mkdir(exist_ok=True)
    for path,text in result['files'].items():p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(text))
    print(json.dumps({'destination':str(dest),'network_socket_denied':result['network_socket_denied'],'files':len(result['files'])}))
