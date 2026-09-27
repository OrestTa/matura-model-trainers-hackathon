import argparse,concurrent.futures as cf,hashlib,json,os,time,urllib.request
from pathlib import Path
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):raise RuntimeError('Redirect disabled')
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root;out=a.output;out.mkdir(parents=True,exist_ok=False);c=json.loads((root/'config.json').read_text());source=root/'candidate.jsonl';assert hashlib.sha256(source.read_bytes()).hexdigest()==c['candidate_sha256'];rows=list(map(json.loads,source.read_text().splitlines()));assert len(rows)==37 and len({r['id'] for r in rows})==37
 proof=json.loads((root/'server-network-proof.json').read_text());assert proof['outbound_tcp_denied'] and proof['udp_socket_denied'];http=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 def call(path,payload=None,timeout=10):
  req=urllib.request.Request('http://127.0.0.1:18935'+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with http.open(req,timeout=timeout) as r:return json.load(r)
 for _ in range(90):
  try:
   if call('/health')['status']=='ok':break
  except Exception:time.sleep(1)
 else:raise RuntimeError('Server unavailable')
 assert call('/lora-adapters')==[], 'Final base verification must load no adapters'
 manifest=dict(c,network_proof=proof,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),complete=False);(out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
 def one(row):
  assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
  if row['predicted_route'] not in ['closed_with_images','open_with_images']:assert not row.get('ocr_refs')
  payload={'messages':[{'role':'system','content':c['system']},{'role':'user','content':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False},'lora':[]}
  result={'id':row['id'],'answer':'','error':None,'predicted_route':row['predicted_route'],'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()};start=time.monotonic()
  try:
   response=call('/v1/chat/completions',payload,240);choice=response['choices'][0];result.update(answer=choice['message'].get('content') or '',finish_reason=choice.get('finish_reason'),usage=response.get('usage'))
  except Exception as exc:result['error']=type(exc).__name__+':'+str(exc)[:150]
  result['latency_s']=time.monotonic()-start;return result
 done=[]
 with cf.ThreadPoolExecutor(max_workers=4) as pool,(out/'answers.jsonl').open('w') as f:
  for future in cf.as_completed([pool.submit(one,r) for r in rows]):
   row=future.result();done.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno());print(json.dumps({'completed':len(done),'id':row['id'],'error':row['error']}),flush=True)
 manifest.update(complete=len(done)==37,answers=len(done),errors=sum(bool(r['error']) for r in done));(out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
