"""Single owned small-vision preprocessing ablation; never receives answer keys."""
import json,time,hashlib
from pathlib import Path
import modal
app=modal.App('matura-small-vision-independent')
volume=modal.Volume.from_name('matura-small-independent',create_if_missing=True)
image=(modal.Image.from_registry('ghcr.io/ggml-org/llama.cpp:server-cuda',add_python='3.12').entrypoint([]).pip_install('huggingface_hub','requests','pillow'))
PROMPT='Opisz dokładnie widoczne materiały źródłowe z historii. Przepisz czytelne napisy, daty, nazwiska i liczby. Dla mapy podaj legendę, nazwy obszarów, granice i kierunki strzałek. Dla ilustracji opisz osoby, przedmioty, symbole i relacje. Oddziel obserwacje od niepewnych identyfikacji. Nie rozwiązuj zadania egzaminacyjnego i nie dopowiadaj niewidocznych faktów. Odpowiedz po polsku.'
@app.function(image=image,gpu='L4',cpu=4,memory=12288,timeout=1200,max_containers=1,retries=0,scaledown_window=2,volumes={'/outputs':volume})
def caption(images:dict,run_id:str,candidate_rows:list=None):
 import os,subprocess,base64,io,requests
 from concurrent.futures import ThreadPoolExecutor
 from PIL import Image
 from huggingface_hub import HfApi,hf_hub_download
 dest=Path('/outputs')/run_id;dest.mkdir(parents=True,exist_ok=False)
 repo='unsloth/Qwen3.5-2B-GGUF';rev=HfApi().model_info(repo).sha
 paths=[hf_hub_download(repo,n,revision=rev,cache_dir='/outputs/hf_cache') for n in ('Qwen3.5-2B-Q4_K_M.gguf','mmproj-F16.gguf')]
 manifest={'run_id':run_id,'repo':repo,'revision':rev,'prompt':PROMPT,'input_images':{k:hashlib.sha256(v).hexdigest() for k,v in images.items()},'artifacts':[{'name':Path(p).name,'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths],'resize_max_side':1280,'max_tokens':900,'temperature':0,'image_count':len(images)}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2));volume.commit()
 log=open(dest/'server.log','w');proc=subprocess.Popen(['/app/llama-server','-m',paths[0],'--mmproj',paths[1],'--host','127.0.0.1','--port','8080','-ngl','99','-c','32768','-np','4','--jinja','--reasoning-budget','0'],stdout=log,stderr=log)
 started=time.time()
 try:
  for _ in range(120):
   if proc.poll() is not None: raise RuntimeError('vision server startup failed; see server.log')
   try:
    if requests.get('http://127.0.0.1:8080/health',timeout=2).ok: break
   except requests.RequestException: pass
   time.sleep(1)
  else: raise TimeoutError('vision startup')
  def one(item):
   name,data=item;im=Image.open(io.BytesIO(data)).convert('RGB');im.thumbnail((1280,1280));buf=io.BytesIO();im.save(buf,format='JPEG',quality=95);processed=buf.getvalue()
   out={'image':name,'source_sha256':hashlib.sha256(data).hexdigest(),'processed_sha256':hashlib.sha256(processed).hexdigest(),'caption':'','error':None}
   try:
    payload={'messages':[{'role':'user','content':[{'type':'text','text':PROMPT},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(processed).decode()}}]}],'temperature':0,'max_tokens':900,'chat_template_kwargs':{'enable_thinking':False}}
    r=requests.post('http://127.0.0.1:8080/v1/chat/completions',json=payload,timeout=180);r.raise_for_status();body=r.json();out.update(caption=body['choices'][0]['message'].get('content') or '',usage=body.get('usage'),finish_reason=body['choices'][0].get('finish_reason'))
   except Exception as exc:out['error']=type(exc).__name__
   return out
  def answer_one(row):
   content=[{'type':'text','text':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}]
   out={'id':row['id'],'answer':'','error':None,'run_id':run_id}
   for linked in row.get('images',[]):
    data=images[Path(linked['path']).name];im=Image.open(io.BytesIO(data)).convert('RGB');im.thumbnail((1280,1280));buf=io.BytesIO();im.save(buf,format='JPEG',quality=95)
    content.append({'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()}})
   try:
    payload={'messages':[{'role':'system','content':'Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'},{'role':'user','content':content}],'temperature':0,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False}}
    r=requests.post('http://127.0.0.1:8080/v1/chat/completions',json=payload,timeout=180);r.raise_for_status();body=r.json();out.update(answer=body['choices'][0]['message'].get('content') or '',usage=body.get('usage'),finish_reason=body['choices'][0].get('finish_reason'))
   except Exception as exc:out['error']=type(exc).__name__
   return out
  if candidate_rows:
   manifest.update(mode='direct_vision_answers',candidate_sha256=hashlib.sha256(json.dumps(candidate_rows,sort_keys=True).encode()).hexdigest(),max_tokens_short=500,max_tokens_essay=1600,prompt='Original baseline system plus full canonical text and linked images')
  results=[]
  with ThreadPoolExecutor(max_workers=4) as pool,open(dest/('answers.jsonl' if candidate_rows else 'captions.jsonl'),'w') as f:
   for row in pool.map(answer_one if candidate_rows else one,candidate_rows if candidate_rows else images.items()):
    results.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();volume.commit()
  manifest.update(elapsed_seconds=time.time()-started,nonempty_captions=sum(bool(r.get('answer',r.get('caption','')).strip()) for r in results));(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));volume.commit();return manifest,results
 finally:proc.terminate();log.close();volume.commit()
@app.local_entrypoint()
def main(images:str='data/small_track/official_mock_v1/images',candidate:str=''):
 files={p.name:p.read_bytes() for p in sorted(Path(images).glob('*.png'))}
 if len(files)!=19:raise ValueError('Expected exact official 19 PNGs')
 run=time.strftime('%Y%m%d-%H%M%S',time.gmtime())+('-qwen35-2b-direct-d0' if candidate else '-qwen35-2b-vision-captions')
 rows_in=[json.loads(x) for x in Path(candidate).read_text().splitlines() if x.strip()] if candidate else None
 manifest,rows=caption.remote(files,run,rows_in);dest=Path('results/small_track')/run;dest.mkdir(parents=True,exist_ok=True);(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));(dest/('answers.jsonl' if candidate else 'captions.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));print(json.dumps(manifest))
