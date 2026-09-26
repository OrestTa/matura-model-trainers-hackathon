"""Paired output-budget ablation; identical model, adapters, routing and inputs.
Run inside the answering server's network-disabled container after weights load.
"""
import argparse, concurrent.futures as cf, hashlib, json, socket, time, urllib.request
from pathlib import Path

SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
ROUTES=['closed_without_images','open_without_images','closed_with_images','open_with_images','essay']

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--candidate',required=True);p.add_argument('--adapter-manifests');p.add_argument('--base-only',action='store_true');p.add_argument('--port',type=int,default=8080);p.add_argument('--concurrency',type=int,default=4);p.add_argument('--server-seccomp',action='store_true');p.add_argument('--output',required=True);p.add_argument('--short-tokens',type=int,default=1000);p.add_argument('--essay-tokens',type=int,default=2400);a=p.parse_args()
 root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);source=Path(a.candidate);rows=[json.loads(l) for l in source.read_text().splitlines()];assert len(rows)==37 and len({r['id'] for r in rows})==37
 reports={} if a.base_only else {r['route']:r for r in json.loads(Path(a.adapter_manifests).read_text())};http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def call(path,payload=None,timeout=10):
  req=urllib.request.Request(f'http://127.0.0.1:{a.port}'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with http.open(req,timeout=timeout) as r:return json.load(r)
 for _ in range(90):
  try:
   if call('/health')['status']=='ok':break
  except Exception:time.sleep(1)
 else:raise RuntimeError('server health timeout')
 loaded=[]
 if not a.base_only:
  call('/lora-adapters',[{'id':i,'scale':0} for i in range(5)]);loaded=call('/lora-adapters');assert len(loaded)==5
  for i,route in enumerate(ROUTES):
   file=root/'adapters'/route/'adapter-f16.gguf';assert loaded[i]['id']==i and loaded[i]['path']==str(file) and loaded[i]['scale']==0
   assert file.stat().st_size==reports[route]['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==reports[route]['sha256']
 if a.server_seccomp:
  proof=json.loads((root/'server-network-proof.json').read_text());assert proof['outbound_tcp_denied'] and proof['udp_socket_denied']
 else:
  try:socket.create_connection(('1.1.1.1',443),timeout=2)
  except OSError:pass
  else:raise RuntimeError('outbound networking is not blocked')
 manifest={'candidate_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'loaded_adapters':loaded,'adapter_manifests_sha256':None if a.base_only else hashlib.sha256(Path(a.adapter_manifests).read_bytes()).hexdigest(),'comparison':'caps only; same selected trained adapter in both arms','control_caps':[500,1600],'variant_caps':[a.short_tokens,a.essay_tokens],'temperature':0,'seed':42,'concurrency':a.concurrency,'base_only':a.base_only,'network_scope':'server outbound TCP and UDP socket seccomp denial; client fixed loopback only' if a.server_seccomp else 'network namespace denial','system':SYSTEM,'offline_outbound_probe_denied':True}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
 for arm in ['control','raised']:(out/arm).mkdir()
 def answer(row):
  assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
  route=row['predicted_route'];text='\n\n'.join(str(row.get(k,'')) for k in ('context','question'));payload={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':text}],'temperature':0,'seed':42,'chat_template_kwargs':{'enable_thinking':False},'lora':[] if a.base_only else [{'id':ROUTES.index(route),'scale':1.0}]};result={}
  for arm,short,essay in [('control',500,1600),('raised',a.short_tokens,a.essay_tokens)]:
   request=dict(payload,max_tokens=essay if row.get('points',0)>=10 else short);r={'id':row['id'],'predicted_route':route,'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()};start=time.monotonic()
   try:
    response=call('/v1/chat/completions',request,240);choice=response['choices'][0];r.update(answer=choice['message'].get('content') or '',finish_reason=choice.get('finish_reason'),usage=response.get('usage'))
   except Exception as exc:r['error']=type(exc).__name__+':'+str(exc)[:150]
   r['latency_s']=time.monotonic()-start;result[arm]=r
  return result
 with cf.ThreadPoolExecutor(max_workers=a.concurrency) as pool,(out/'control/answers.jsonl').open('w') as control,(out/'raised/answers.jsonl').open('w') as raised:
  for n,future in enumerate(cf.as_completed([pool.submit(answer,r) for r in rows]),1):
   result=future.result()
   for arm,f in [('control',control),('raised',raised)]:f.write(json.dumps(result[arm],ensure_ascii=False)+'\n');f.flush()
   print(json.dumps({'completed':n,'id':result['raised']['id'],'errors':[result[k]['error'] for k in result]}),flush=True)

if __name__=='__main__':main()
