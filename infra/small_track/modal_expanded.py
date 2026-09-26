"""Two bounded offline baselines, CPU-preloaded pinned assets, persistent output."""
import modal,json,time,hashlib
from pathlib import Path
app=modal.App('matura-expanded-independent')
volume=modal.Volume.from_name('matura-small-independent',create_if_missing=True)
image=modal.Image.from_registry('ghcr.io/ggml-org/llama.cpp:server-cuda',add_python='3.12').entrypoint([]).pip_install('huggingface_hub','requests')
CONFIGS=[{'name': 'qwen35-4b-vision', 'repo': 'unsloth/Qwen3.5-4B-GGUF', 'revision': 'e87f176479d0855a907a41277aca2f8ee7a09523', 'files': [{'file': 'Qwen3.5-4B-Q4_K_M.gguf', 'bytes': 2740937888, 'sha256': '00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'}, {'file': 'mmproj-F16.gguf', 'bytes': 672423616, 'sha256': 'cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864'}]}]
def select_smoke_rows(rows):
 labels=('closed_without_images','closed_with_images','open_without_images','open_with_images','essay')
 selected=[]
 for label in labels:
  row=next((r for r in rows if r.get('subtype')==label),None)
  if row is None:raise ValueError('Smoke requires one candidate task for each of five categories')
  selected.append(row)
 if len({r['id'] for r in selected})!=5:raise ValueError('Smoke IDs must be unique')
 return selected
@app.function(image=image,cpu=2,memory=2048,timeout=600,max_containers=2,retries=0,scaledown_window=2,volumes={'/outputs':volume})
def preload(config):
 from huggingface_hub import hf_hub_download
 paths=[]
 for f in config['files']:
  p=Path(hf_hub_download(config['repo'],f['file'],revision=config['revision'],cache_dir='/outputs/hf_cache'))
  with p.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
  assert p.stat().st_size==f['bytes'] and digest==f['sha256'];paths.append(str(p))
 volume.commit();return paths
@app.function(image=image,gpu='L4',cpu=4,memory=12288,timeout=900,max_containers=2,retries=0,scaledown_window=2,block_network=True,volumes={'/outputs':volume})
def evaluate(config,paths,rows,images,run):
 import requests,subprocess,socket,base64,concurrent.futures as cf
 volume.reload();dest=Path('/outputs')/run;dest.mkdir(exist_ok=False);start=time.time()
 try:socket.create_connection(('1.1.1.1',443),timeout=2).close();raise RuntimeError('network unexpectedly allowed')
 except OSError:pass
 for row in rows:assert not {'gold','rubric','official_solution','solution','answer','answers'}.intersection(row)
 log=(dest/'server.log').open('w');cmd=['/app/llama-server','-m',paths[0],'--host','127.0.0.1','--port','8080','-ngl','99','-c','32768','-np','4','--jinja','--reasoning-budget','0']
 if len(paths)>1:cmd+=['--mmproj',paths[1]]
 proc=subprocess.Popen(cmd,stdout=log,stderr=log)
 manifest={'run_id':run,'config':config,'serialized_weight_bytes':sum(f['bytes'] for f in config['files']),'remote_paths':paths,'original_candidate_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'original_image_sha256':{n:hashlib.sha256(data).hexdigest() for n,data in images.items()} if len(paths)>1 else {},'modality':'original PNG vision' if len(paths)>1 else 'text-only ablation','temperature':0,'seed':42,'short_tokens':500,'essay_tokens':1600,'block_network':True,'outbound_probe_denied':True,'timeout_seconds':900}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));volume.commit()
 try:
  for _ in range(180):
   if proc.poll() is not None:raise RuntimeError('server startup failed')
   try:
    if requests.get('http://127.0.0.1:8080/health',timeout=2).ok:break
   except requests.RequestException:pass
   time.sleep(1)
  else:raise TimeoutError('server startup')
  def one(row):
   text='\n\n'.join(str(row.get(k,'')) for k in ('context','question'));content=[{'type':'text','text':text}]
   if len(paths)>1:
    for linked in row.get('images',[]):
     data=images[Path(linked['path']).name];assert hashlib.sha256(data).hexdigest()==linked['sha256'];content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}})
   payload={'messages':[{'role':'system','content':'Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'},{'role':'user','content':content if len(paths)>1 else text}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False}}
   out={'id':row['id'],'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
   try:
    rr=requests.post('http://127.0.0.1:8080/v1/chat/completions',json=payload,timeout=180);rr.raise_for_status();b=rr.json();out.update(answer=b['choices'][0]['message'].get('content') or '',finish_reason=b['choices'][0].get('finish_reason'),usage=b.get('usage'))
   except Exception as e:out['error']=type(e).__name__
   return out
  answers=[]
  with cf.ThreadPoolExecutor(max_workers=4) as pool,(dest/'answers.jsonl').open('w') as handle:
   for future in cf.as_completed([pool.submit(one,r) for r in rows]):
    r=future.result();answers.append(r);handle.write(json.dumps(r,ensure_ascii=False)+'\n');handle.flush();volume.commit()
  manifest.update(elapsed_seconds=time.time()-start,answers=len(answers),errors=sum(bool(r['error']) for r in answers),complete_candidate_coverage={r['id'] for r in answers}=={r['id'] for r in rows},scope=config.get('evaluation_scope','full_paper'));
  if manifest['scope']=='SMOKE_ONLY_NOT_FULL_SCORE':manifest['smoke_valid']=len(answers)==5 and manifest['errors']==0 and manifest['complete_candidate_coverage']
  (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));volume.commit();return {'run_id':run,'answers':len(answers),'errors':manifest['errors']}
 finally:proc.terminate();log.close();volume.commit()
@app.local_entrypoint()
def main(preload_only:bool=False, quant:str="q4", candidate:str="data/small_track/official_mock_v1/canonical-b0-candidate.jsonl", smoke:bool=False):
 if quant not in ("q4","q3"):raise ValueError("supported quantizations:q4,q3")
 if quant=="q3":
  CONFIGS[0]["name"]="qwen35-4b-vision-q3"
  CONFIGS[0]["files"][0]={"file":"Qwen3.5-4B-Q3_K_M.gguf","bytes":2293388448,"sha256":"d6981ab4d77ba712b48ef69d69042d75b5e39b9dce5fb5a5b054fd08e06afb95"}
 source=Path(candidate);rows=list(map(json.loads,source.read_text().splitlines()));images={}
 if smoke:rows=select_smoke_rows(rows)
 for row in rows:
  if row.get('images'):
   for im in row['images']:images[Path(im['path']).name]=(source.parent/im['path']).read_bytes()
  elif row.get('page_images'):
   row['images']=[]
   for name in row['page_images']:
    p=Path(name);data=p.read_bytes();images[p.name]=data;row['images'].append({'path':p.name,'sha256':hashlib.sha256(data).hexdigest()})
 for config in CONFIGS:
  config['evaluation_scope']='SMOKE_ONLY_NOT_FULL_SCORE' if smoke else 'full_paper'
  if smoke:config['name']+='-smoke'
  config['source_candidate_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
  config['input_representation']='canonical task-crop PNG' if source.parent.name=='official_mock_v1' else 'official full-page PNG plus complete extracted task text; differs from2023mockcrops'
  if source.parent.name!='official_mock_v1':config['name']+='-'+source.parent.name
 stamp=time.strftime('%Y%m%d-%H%M%S',time.gmtime());preloads=[preload.spawn(c) for c in CONFIGS];calls=[]
 for config,call in zip(CONFIGS,preloads):
  paths=call.get()
  if preload_only:
   print(json.dumps({'preloaded':config['name'],'paths':paths}),flush=True);continue
  run=stamp+'-'+config['name']+'-offline-b0';calls.append(evaluate.spawn(config,paths,rows,images if len(paths)>1 else {},run));print(json.dumps({'launched':run}),flush=True)
 from concurrent.futures import ThreadPoolExecutor,as_completed
 def collect(call):
  import subprocess,sys
  summary=call.get();dest=Path('results/small_track')/summary['run_id'];dest.mkdir(parents=True,exist_ok=True)
  for name in ('answers.jsonl','manifest.json','server.log'):
   subprocess.run([sys.executable,'-m','modal','volume','get','matura-small-independent',summary['run_id']+'/'+name,str(dest/name),'--force'],check=True)
  return dict(summary,path=str(dest))
 with ThreadPoolExecutor(max_workers=2) as pool:
  for f in as_completed([pool.submit(collect,c) for c in calls]):print(json.dumps(f.result()),flush=True)
