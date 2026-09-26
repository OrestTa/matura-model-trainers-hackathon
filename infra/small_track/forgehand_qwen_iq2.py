import argparse,base64,concurrent.futures as cf,hashlib,json,os,time,urllib.request
from pathlib import Path
SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):raise RuntimeError('Redirect disabled')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root;out=a.output;out.mkdir(parents=True,exist_ok=False)
 config=json.loads((root/'config.json').read_text());source=root/'candidate.jsonl';assert hashlib.sha256(source.read_bytes()).hexdigest()==config['candidate_sha256'];rows=list(map(json.loads,source.read_text().splitlines()));assert len(rows)==37 and len({r['id'] for r in rows})==37
 proof=json.loads((root/'server-network-proof.json').read_text());assert proof['outbound_tcp_denied'] and proof['udp_socket_denied'];http=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def call(path,payload=None,timeout=10):
  req=urllib.request.Request('http://127.0.0.1:18933'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with http.open(req,timeout=timeout) as r:return json.load(r)
 for _ in range(120):
  try:
   if call('/health')['status']=='ok':break
  except Exception:time.sleep(1)
 else:raise RuntimeError('Server unavailable')
 manifest=dict(config,system=SYSTEM,network_proof=proof,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),complete=False)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2));images={}
 for row in rows:
  assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
  for im in row.get('images',[]):
   path=(root/im['path']).resolve();assert path.is_relative_to(root.resolve());data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==im['sha256'];images[im['sha256']]=base64.b64encode(data).decode()
 def one(row):
  content=[{'type':'text','text':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}]
  content += [{'type':'image_url','image_url':{'url':'data:image/png;base64,'+images[i['sha256']]}} for i in row.get('images',[])]
  payload={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':content}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False}}
  result={'id':row['id'],'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()};start=time.monotonic()
  try:
   response=call('/v1/chat/completions',payload,240);choice=response['choices'][0];result.update(answer=choice['message'].get('content') or '',finish_reason=choice.get('finish_reason'),usage=response.get('usage'))
  except Exception as e:result['error']=type(e).__name__+':'+str(e)[:160]
  result['latency_s']=time.monotonic()-start;return result
 routes=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay'];smoke=[next(r for r in rows if r['subtype']==route) for route in routes];assert len({r['id'] for r in smoke})==5
 done=[]
 with (out/'answers.jsonl').open('w') as handle:
  def save(result):
   done.append(result);handle.write(json.dumps(result,ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno());print(json.dumps({'completed':len(done),'id':result['id'],'error':result['error']}),flush=True)
  with cf.ThreadPoolExecutor(max_workers=2) as pool:
   for f in cf.as_completed([pool.submit(one,r) for r in smoke]):save(f.result())
  (out/'smoke.json').write_text(json.dumps(done,ensure_ascii=False,indent=2))
  if any(x['error'] or not x['answer'].strip() for x in done):raise RuntimeError('Five-category smoke failed; no full expansion')
  smokeids={r['id'] for r in smoke}
  with cf.ThreadPoolExecutor(max_workers=2) as pool:
   for f in cf.as_completed([pool.submit(one,r) for r in rows if r['id'] not in smokeids]):save(f.result())
 manifest.update(complete=len(done)==37,answers=len(done),errors=sum(bool(r['error']) for r in done));(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
