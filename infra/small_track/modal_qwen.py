"""Pinned offline Qwen baseline: CPU asset preload, one network-blocked L4."""
import json,time,hashlib
from pathlib import Path
import modal
app=modal.App('matura-qwen-native-path')
volume=modal.Volume.from_name('matura-qwen-independent',create_if_missing=True)
image=modal.Image.from_registry('ghcr.io/ggml-org/llama.cpp:server-cuda',add_python='3.12').entrypoint([]).pip_install('huggingface_hub','requests')
CONFIG={'repo':'unsloth/Qwen3-4B-Instruct-2507-GGUF','revision':'a06e946bb6b655725eafa393f4a9745d460374c9','file':'Qwen3-4B-Instruct-2507-Q4_K_M.gguf','bytes':2497281120,'sha256':'3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597','native_repo':'Qwen/Qwen3-4B-Instruct-2507','native_revision':'cdbee75f17c01a7cc42f958dc650907174af0554'}
@app.function(image=image,cpu=2,memory=2048,timeout=600,max_containers=1,retries=0,scaledown_window=2,volumes={'/outputs':volume})
def preload():
 from huggingface_hub import hf_hub_download
 p=Path(hf_hub_download(CONFIG['repo'],CONFIG['file'],revision=CONFIG['revision'],cache_dir='/outputs/hf_cache'))
 with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 assert p.stat().st_size==CONFIG['bytes'] and sha==CONFIG['sha256'];volume.commit();return '/outputs/hf_cache/'+str(p).split('/hf_cache/',1)[1]
@app.function(image=image,gpu='L4',cpu=2,memory=8192,timeout=1200,max_containers=1,retries=0,scaledown_window=2,block_network=True,volumes={'/outputs':volume})
def evaluate(model,rows,run_id):
 import requests,subprocess,socket,concurrent.futures as cf
 volume.reload();dest=Path('/outputs')/run_id;dest.mkdir(exist_ok=False)
 for row in rows:assert not {'gold','rubric','official_solution','solution','answer','answers'}.intersection(row)
 probe=False
 try:
  socket.create_connection(('1.1.1.1',443),timeout=2).close()
 except OSError:probe=True
 if not probe:raise RuntimeError('Outbound network unexpectedly available')
 binary=next(str(p) for p in map(Path,['/app/llama-server','/llama-server']) if p.exists());log=(dest/'server.log').open('w')
 proc=subprocess.Popen([binary,'-m',model,'--host','127.0.0.1','--port','8080','-ngl','99','-c','65536','-np','8','--jinja'],stdout=log,stderr=log)
 manifest={'config':CONFIG,'run_id':run_id,'serialized_weight_bytes':CONFIG['bytes'],'input_sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'modality':'canonical unchanged text-only baseline; no OCR','temperature':0,'seed':42,'short_tokens':500,'essay_tokens':1600,'timeout_seconds':1200,'offline':{'modal_block_network':True,'outbound_connection_probe_denied':probe},'server_version':subprocess.run([binary,'--version'],capture_output=True,text=True).stdout}
 try:
  for _ in range(180):
   if proc.poll() is not None:raise RuntimeError('llama server exited')
   try:
    if requests.get('http://127.0.0.1:8080/health',timeout=2).ok:break
   except requests.RequestException:pass
   time.sleep(1)
  else:raise TimeoutError('model startup')
  def answer(row):
   start=time.monotonic();payload={'messages':[{'role':'system','content':'Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'},{'role':'user','content':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500};out={'id':row['id'],'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
   try:
    response=requests.post('http://127.0.0.1:8080/v1/chat/completions',json=payload,timeout=180);response.raise_for_status();body=response.json();out.update(answer=body['choices'][0]['message'].get('content') or '',finish_reason=body['choices'][0].get('finish_reason'),usage=body.get('usage'))
   except Exception as exc:out['error']=type(exc).__name__
   out['latency_s']=time.monotonic()-start;return out
  answers=[]
  with cf.ThreadPoolExecutor(max_workers=8) as pool,(dest/'answers.jsonl').open('w') as f:
   for future in cf.as_completed([pool.submit(answer,row) for row in rows]):r=future.result();answers.append(r);f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush()
  (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));volume.commit();return {'manifest':manifest,'answers':answers}
 finally:proc.terminate();proc.wait(timeout=20)
@app.local_entrypoint()
def main(candidate:str='data/small_track/official_mock_v1/canonical-b0-candidate.jsonl'):
 source=Path(candidate);rows=[json.loads(l) for l in source.read_text().splitlines()];assert len(rows)==37;model=preload.remote();run=time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-qwen3-4b-2507-q4-canonical-b0';result=evaluate.remote(model,rows,run);dest=Path('results/small_track')/run;dest.mkdir(parents=True);result['manifest'].update(candidate_file_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());(dest/'manifest.json').write_text(json.dumps(result['manifest'],indent=2));(dest/'answers.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in result['answers']));print(json.dumps({'path':str(dest),'rows':len(result['answers']),'errors':sum(bool(r['error']) for r in result['answers'])}))

@app.local_entrypoint()
def preload_only():
 print(json.dumps({'cached_model':preload.remote(),'config':CONFIG}))
