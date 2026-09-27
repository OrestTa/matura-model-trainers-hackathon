#!/usr/bin/env python3
"""Standalone Bielik package dry-run/export or explicit offline inference."""
import argparse,hashlib,json,subprocess,sys,time,urllib.request,shutil
from pathlib import Path
import harness,train_router,infer,ocr
from official_format import validate_exam,export_answers
ROOT=Path(__file__).resolve().parent

def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate_candidate(exam):
 if infer.FORBIDDEN.intersection(exam):raise ValueError('Exam contains grading data')
 for item in exam['items']:
  if infer.FORBIDDEN.intersection(item):raise ValueError('Task contains grading data')

def adapter_args(config,root):
 keys=sorted(config['routes'],key=lambda k:next(x['id'] for x in config['routes'][k]['lora'] if x['scale']==1.0))
 ids=[next(x['id'] for x in config['routes'][k]['lora'] if x['scale']==1.0) for k in keys]
 if ids!=list(range(5)):raise ValueError('Five unique contiguous adapter IDs required')
 paths=[str(root/config['artifacts'][k]['filename']) for k in keys]
 if any(',' in p for p in paths):raise ValueError('Comma in adapter path unsupported')
 return ['--lora',','.join(paths),'--lora-init-without-apply']

def submission_payload(row,config):
 route=config['routes'][row['subtype']]
 return {'messages':[{'role':'system','content':route['system_prompt']},{'role':'user','content':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}],'temperature':config.get('temperature',0),'seed':config.get('seed',42),'max_tokens':route['essay_tokens'] if row.get('points',0)>=10 else route['max_tokens'],'chat_template_kwargs':{'enable_thinking':False},'lora':sorted(route['lora'],key=lambda x:x['id'])}

def package_answer(row,config):
 payload=submission_payload(row,config);start=time.monotonic()
 result={'id':row['id'],'answer':'','error':None,'predicted_route':row['subtype'],'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
 try:
  req=urllib.request.Request('http://127.0.0.1:18935/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=240) as response:reply=json.load(response)
  choice=reply['choices'][0];result.update(answer=choice['message'].get('content') or '',finish_reason=choice.get('finish_reason'),usage=reply.get('usage'))
 except Exception as exc:result['error']=type(exc).__name__+':'+str(exc)[:150]
 result['latency_s']=time.monotonic()-start
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--exam',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--server',type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve existing output')
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):raise ValueError('Offline redirects forbidden')
 urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()))
 config=json.loads((ROOT/'config.json').read_text());manifest=json.loads((ROOT/'weights-manifest.json').read_text());missing=[]
 expected={a['filename']:(a['bytes'],a['sha256']) for a in list(config['artifacts'].values())+config['auxiliary_artifacts']}
 assert expected=={a['path']:(a['bytes'],a['sha256']) for a in manifest['weights']},'Config/manifest artifact mismatch'
 assert sum(a['bytes'] for a in manifest['weights'])==manifest['aggregate_weight_bytes']<=8800000000
 for art in manifest['weights']:
  path=ROOT/art['path']
  if not path.exists():missing.append(art['path']);continue
  assert path.stat().st_size==art['bytes'] and digest(path)==art['sha256'],'Weight identity mismatch'
 exam=json.loads(a.exam.read_text());validate_candidate(exam);ids=validate_exam(exam,a.exam.parent);rows=harness.load_rows(a.exam);router=json.loads((ROOT/'weights/router.json').read_text())
 for r in rows:r.update(train_router.predict(r,router));infer.messages(r)
 a.output.mkdir(parents=True);plan=[{'id':r['id'],'route':r['subtype'],'ocr_required':r['subtype'] in {'closed_with_images','open_with_images'},'adapter_id':next(x['id'] for x in config['routes'][r['subtype']]['lora'] if x['scale']==1.0)} for r in rows]
 (a.output/'route-plan.json').write_text(json.dumps(plan,indent=2));status={'mode':'inference' if a.run else 'DRY_RUN_ONLY','items':len(ids),'max_points':exam['max_points'],'image_checksums':'verified','missing_weights':missing,'all_weights_verified':not missing,'aggregate_weight_bytes':manifest['aggregate_weight_bytes'],'evaluation_status':'Below35percent target; no passing claim','original_exam_sha256':digest(a.exam),'classifier_before_ocr':True,'six_models':'one classifier and five trained LoRA specialists sharing one base; OCR auxiliary'}
 (a.output/'status.json').write_text(json.dumps(status,indent=2))
 if not a.run:
  (a.output/'answers.DRY_RUN.EMPTY.json').write_bytes(export_answers(exam,[{'id':i,'answer':''} for i in ids]));print(json.dumps(status));return
 if missing:raise ValueError('Restore missing weights before offline inference')
 if not a.server or digest(a.server)!='efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf':raise ValueError('Pinned supported llama-server required')
 mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines());assert int(mem['MemAvailable'].strip().split()[0])>=6*1024*1024,'Require6GiB available hostRAM'
 free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0]);assert free>=6144,'Require6GiB freeVRAM'
 a.server=a.server.resolve()
 image_rows=[r for r in rows if r['subtype'] in {'closed_with_images','open_with_images'}]
 if image_rows:
  if config.get("ocr_runtime"):
   executable=shutil.which("tesseract")
   if not executable or digest(Path(executable))!=config["ocr_runtime"]["binary_sha256"]:raise ValueError("Pinned Tesseract runtime required; OCR versions change candidate inputs")
  raw=a.output/'image-only-candidates.jsonl';derived=a.output/'ocr-image-candidates.jsonl';raw.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in image_rows));ocr.enrich(raw,derived,a.output/'ocr-assets',a.exam.parent,ROOT/'weights/ocr');changed={r['id']:r for r in map(json.loads,derived.read_text().splitlines())};rows=[changed.get(r['id'],r) for r in rows]
 route_keys=sorted(config['routes'],key=lambda k:next(x['id'] for x in config['routes'][k]['lora'] if x['scale']==1.0));cmd=[sys.executable,str(ROOT/'offline_server.py'),str(a.output/'server-network-proof.json'),str(a.server),'-m',str(ROOT/config['artifacts']['model']['filename']),'-ngl','99','-c','8192','-np','1','-t','1','-b','128','-ub','64','--jinja','--reasoning-budget','0','--host','127.0.0.1','--port','18935']
 cmd+=adapter_args(config,ROOT)
 with (a.output/'server.log').open('w') as log:
  server=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(90):
    if server.poll() is not None:raise RuntimeError('Server failed')
    try:
     with urllib.request.urlopen('http://127.0.0.1:18935/health',timeout=1) as r:
      if r.status==200:break
    except Exception:time.sleep(1)
   else:raise RuntimeError('Server readiness timeout')
   proof=json.loads((a.output/'server-network-proof.json').read_text());assert proof['outbound_tcp_denied'] and proof['udp_socket_denied']
   with urllib.request.urlopen('http://127.0.0.1:18935/lora-adapters') as r:loaded=json.load(r)
   loaded=loaded.get('adapters',loaded) if isinstance(loaded,dict) else loaded
   assert len(loaded)==5
   for i,key in enumerate(route_keys):
    row=next(x for x in loaded if x['id']==i);assert Path(row['path']).resolve()==(ROOT/config['artifacts'][key]['filename']).resolve()
   reset=urllib.request.Request('http://127.0.0.1:18935/lora-adapters',data=json.dumps([{'id':i,'scale':0.0} for i in range(5)]).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(reset) as r:assert r.status==200
   results=[]
   for row in rows:
    result=package_answer(row,config);results.append(result)
    with (a.output/'answers.jsonl').open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
   (a.output/'answers.json').write_bytes(export_answers(exam,results));status['errors']=sum(bool(r['error']) for r in results);status['network_proof']=proof;(a.output/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status))
  finally:
   server.terminate()
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait()
if __name__=='__main__':main()
