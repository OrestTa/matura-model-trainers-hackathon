import concurrent.futures as cf,hashlib,json,pathlib,time,urllib.request,socket
ROOT=pathlib.Path('/opt/codex-small-track/bielik-real-2050'); OUT=ROOT/'evaluation';OUT.mkdir(exist_ok=True)
ROUTES=['closed_without_images','open_without_images','closed_with_images','open_with_images','essay']
EXPECTED_ADAPTER_SHA256={'closed_without_images': 'ba3a3249822e8978303f9da15ce53d58db31b9399af991b133feba6d62a8c704', 'open_without_images': 'f9cab931dcea3e03c2aa66f23475c1dd79da4432e3bd0f970c5c52d12983a77d', 'closed_with_images': '6c5231bc427b237e2fbd9fff56182b68b1880ef348f9106017ffef353b4ab2d9', 'open_with_images': '39364c09119a70381a9bd772ab2fdab14bdcd07cf27f385ad1473da424cad0a3', 'essay': '0021aa278c2d6fb124b2b9ed4bd4aceff2f45b47c9dc92ac87423ca0f13d92ab'}
SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with http.open('http://127.0.0.1:8080'+path,timeout=5) as r:return json.load(r)
for _ in range(90):
 try:
  if get('/health')['status']=='ok':break
 except Exception:time.sleep(1)
else:raise RuntimeError('server unavailable')
initial=get('/lora-adapters');(OUT/'initial-adapters.json').write_text(json.dumps(initial,indent=2));assert len(initial)==5
zero=urllib.request.Request('http://127.0.0.1:8080/lora-adapters',data=json.dumps([{'id':i,'scale':0.0} for i in range(5)]).encode(),headers={'Content-Type':'application/json'},method='POST')
with http.open(zero,timeout=10) as response: response.read()
adapters=get('/lora-adapters');(OUT/'loaded-adapters.json').write_text(json.dumps(adapters,indent=2));assert isinstance(adapters,list) and len(adapters)==5,adapters
for i,a in enumerate(adapters):assert a['id']==i and a['path']==str(ROOT/'adapters'/ROUTES[i]/'adapter-f16.gguf') and float(a['scale'])==0.0,adapters
for route in ROUTES:
 assert hashlib.sha256((ROOT/'adapters'/route/'adapter-f16.gguf').read_bytes()).hexdigest()==EXPECTED_ADAPTER_SHA256[route]
try:socket.create_connection(('1.1.1.1',443),timeout=2)
except OSError:blocked=True
else:raise RuntimeError('outbound network not blocked')
source=ROOT/'candidate.jsonl';rows=[json.loads(l) for l in source.read_text().splitlines()];assert len(rows)==37
manifest={'candidate_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'offline_outbound_probe_failed':blocked,'loaded_adapters':adapters,'routes':ROUTES,'seed':42,'temperature':0,'short_tokens':500,'essay_tokens':1600,'system':SYSTEM,'images_encoded_by_model':False,'ocr_only_image_routes':True,'comparison':'zero adapter versus selected real adapter, identical request except lora'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
def one(row):
 assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
 route=row['predicted_route'];text='\n\n'.join(str(row.get(k,'')) for k in ('context','question'))
 payload={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':text}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False}}
 result={'id':row['id'],'predicted_route':route,'answer':'','base_answer':'','error':None}
 for label,loras in [('base_answer',[]),('answer',[{'id':ROUTES.index(route),'scale':1.0}])]:
  p=dict(payload,lora=loras);result[label+'_request_sha256']=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  try:
   req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
   with http.open(req,timeout=180) as r:result[label]=json.load(r)['choices'][0]['message'].get('content') or ''
  except Exception as e:result['error']=type(e).__name__+':'+str(e)[:150]
 return result
with cf.ThreadPoolExecutor(max_workers=4) as pool,(OUT/'answers.jsonl').open('w') as f:
 for n,future in enumerate(cf.as_completed([pool.submit(one,r) for r in rows]),1):
  result=future.result();f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush();print(json.dumps({'completed':n,'id':result['id'],'error':result['error']}),flush=True)
