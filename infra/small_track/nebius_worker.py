import concurrent.futures as cf, hashlib,json,pathlib,subprocess,time,urllib.request
from huggingface_hub import HfApi,hf_hub_download
ROOT=pathlib.Path('/opt/codex-small-track'); SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
def worker(size,port):
 repo=f'second-state/Bielik-{size}B-v3.0-Instruct-GGUF'; filename=f'Bielik-{size}B-v3.0-Instruct-Q4_K_M.gguf'; revision=HfApi().model_info(repo).sha
 path=pathlib.Path(hf_hub_download(repo,filename,revision=revision,local_dir=str(ROOT/'models')))
 out=ROOT/f'bielik{size}-2024-baseline';out.mkdir(exist_ok=True)
 manifest={'model_repo':repo,'revision':revision,'weight_file':filename,'weight_bytes':path.stat().st_size,'weight_sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'input_sha256':hashlib.sha256((ROOT/'candidate.jsonl').read_bytes()).hexdigest(),'variant':'bare_text_2024_development','system':SYSTEM,'temperature':0,'seed':42,'max_tokens':500,'essay_tokens':1600,'concurrency':8,'provider':'Nebius','instance_id':'computeinstance-e00nvzyqe70tcyzpnt'}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 subprocess.run(['sudo','docker','pull','ghcr.io/ggml-org/llama.cpp:server-cuda'],check=True,stdout=open(out/'pull.log','w'),stderr=subprocess.STDOUT)
 name='codex-bielik-'+size.replace('.','');subprocess.run(['sudo','docker','run','-d','--name',name,'--gpus','all','-p',f'127.0.0.1:{port}:8080','-v',f'{ROOT}/models:/models:ro','ghcr.io/ggml-org/llama.cpp:server-cuda','-m',f'/models/{filename}','--host','0.0.0.0','--port','8080','-ngl','99','-c','65536','-np','8','--jinja'],check=True)
 for _ in range(120):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as r:
    if r.status==200:break
  except Exception:time.sleep(2)
 else:raise RuntimeError('server unavailable')
 print(json.dumps({'model':size,'state':'inference_running'}),flush=True)
 rows=[json.loads(x) for x in (ROOT/'candidate.jsonl').read_text().splitlines()]
 def answer(row):
  assert not {'answer','answers','rubric','official_solution','gold','solution'}.intersection(row)
  body={'model':filename,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'\n\n'.join(str(row[k]) for k in ('context','question') if row.get(k))}],'temperature':0,'seed':42,'max_tokens':1600 if row['points']>=10 else 500}
  result={'id':row['id'],'paper_id':row.get('paper_id'),'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True).encode()).hexdigest()};start=time.monotonic()
  try:
   request=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(request,timeout=240) as response:r=json.load(response)
   result.update(answer=r['choices'][0]['message']['content'],finish_reason=r['choices'][0].get('finish_reason'),usage=r.get('usage'))
  except Exception as e:result['error']=type(e).__name__
  result['latency_s']=time.monotonic()-start;return result
 with cf.ThreadPoolExecutor(max_workers=8) as pool,(out/'answers.jsonl').open('w') as f:
  for future in cf.as_completed([pool.submit(answer,row) for row in rows]):f.write(json.dumps(future.result(),ensure_ascii=False)+'\n');f.flush()
 subprocess.run(['sudo','docker','logs',name],stdout=open(out/'server.log','w'),stderr=subprocess.STDOUT)
 print(json.dumps({'model':size,'state':'complete','rows':len(rows)}),flush=True)
with cf.ThreadPoolExecutor(max_workers=2) as pool:
 for future in cf.as_completed([pool.submit(worker,'1.5',18101),pool.submit(worker,'4.5',18102)]):future.result()
