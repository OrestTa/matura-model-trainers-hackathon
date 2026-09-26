"""Matched real-specialist evaluation; candidate-only input, durable per-arm rows."""
import argparse,concurrent.futures as cf,hashlib,json,os,threading,time,urllib.request
from pathlib import Path
ROUTES=['closed_without_images','open_without_images','closed_with_images','open_with_images','essay']
SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise RuntimeError('HTTP redirects disabled')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--adapter-root',required=True);p.add_argument('--output',required=True);p.add_argument('--port',type=int,default=18932);p.add_argument('--resume',action='store_true');a=p.parse_args()
 root=Path(a.root);out=Path(a.output);adapter_root=Path(a.adapter_root);config=json.loads((root/'config.json').read_text());source=root/'candidate.jsonl';assert sha(source)==config['candidate_sha256'];assert sha(root/'adapter-manifests.json')==config['adapter_manifests_sha256']
 rows=list(map(json.loads,source.read_text().splitlines()));assert len(rows)==37 and len({r['id'] for r in rows})==37
 for row in rows:
  assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
  assert row['predicted_route'] in ROUTES
  if row['predicted_route'] not in ['closed_with_images','open_with_images']:assert not row.get('ocr_refs')
 reports={r['route']:r for r in json.loads((root/'adapter-manifests.json').read_text())};assert set(reports)==set(ROUTES)
 expected=[]
 for i,route in enumerate(ROUTES):
  path=adapter_root/route/'adapter-f16.gguf';assert path.stat().st_size==reports[route]['bytes'] and sha(path)==reports[route]['sha256'];expected.append({'id':i,'path':str(path),'scale':0.0,'sha256':reports[route]['sha256'],'bytes':reports[route]['bytes']})
 http=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def call(path,payload=None,timeout=10):
  assert path.startswith('/') and not path.startswith('//')
  req=urllib.request.Request(f'http://127.0.0.1:{a.port}'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with http.open(req,timeout=timeout) as r:return json.load(r)
 for _ in range(90):
  try:
   if call('/health')['status']=='ok':break
  except Exception:time.sleep(1)
 else:raise RuntimeError('server health timeout')
 initial=call('/lora-adapters');assert len(initial)==5
 call('/lora-adapters',[{'id':i,'scale':0.0} for i in range(5)]);loaded=call('/lora-adapters');assert len(loaded)==5
 for e in expected:assert any(all(v.get(k)==e[k] for k in ['id','path','scale']) for v in loaded)
 proof=json.loads((root/'server-network-proof.json').read_text());assert proof['outbound_tcp_denied'] and proof['udp_socket_denied']
 manifest=dict(config,system=SYSTEM,loaded_adapters=loaded,expected_adapters=expected,network_proof=proof,code_sha256=sha(__file__))
 if a.resume:assert json.loads((out/'manifest.json').read_text())==manifest
 else:out.mkdir(parents=True,exist_ok=False);(out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
 (out/'verified_lora_handshake.json').write_text(json.dumps({'verified':True,'expected':expected,'loaded':loaded,'initial':initial},indent=2))
 saved={};files={};lock=threading.Lock()
 for arm in ['base','trained']:
  folder=out/arm;folder.mkdir(exist_ok=True);path=folder/'answers.jsonl';old=list(map(json.loads,path.read_text().splitlines())) if path.exists() else [];assert len({x['id'] for x in old})==len(old) and {x['id'] for x in old}<={r['id'] for r in rows};saved[arm]={x['id']:x for x in old};files[arm]=path.open('a')
 def one(row):
  route=row['predicted_route'];payload={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False}}
  for arm in ['base','trained']:
   if row['id'] in saved[arm]:continue
   request=dict(payload,lora=[{'id':i,'scale':1.0 if arm=='trained' and ROUTES[i]==route else 0.0} for i in range(5)])
   result={'id':row['id'],'answer':'','error':None,'predicted_route':route,'request_sha256':hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()};start=time.monotonic()
   try:
    response=call('/v1/chat/completions',request,240);choice=response['choices'][0];result.update(answer=choice['message'].get('content') or '',finish_reason=choice.get('finish_reason'),usage=response.get('usage'))
   except Exception as exc:result['error']=type(exc).__name__+':'+str(exc)[:150]
   result['latency_s']=time.monotonic()-start
   with lock:files[arm].write(json.dumps(result,ensure_ascii=False)+'\n');files[arm].flush();os.fsync(files[arm].fileno())
  return row['id']
 try:
  with cf.ThreadPoolExecutor(max_workers=config['concurrency']) as pool:
   for n,f in enumerate(cf.as_completed([pool.submit(one,r) for r in rows if any(r['id'] not in saved[arm] for arm in saved)]),1):print(json.dumps({'pairs_completed_this_session':n,'id':f.result()}),flush=True)
 finally:
  for f in files.values():f.close()
if __name__=='__main__':main()
