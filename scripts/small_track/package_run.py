#!/usr/bin/env python3
"""Standalone Bielik package dry-run/export or explicit offline inference."""
import argparse,hashlib,json,subprocess,sys,time,urllib.request
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
 a.output.mkdir(parents=True);plan=[{'id':r['id'],'route':r['subtype'],'ocr_required':r['subtype'] in {'closed_with_images','open_with_images'},'adapter_id':config['routes'][r['subtype']]['lora'][0]['id']} for r in rows]
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
  raw=a.output/'image-only-candidates.jsonl';derived=a.output/'ocr-image-candidates.jsonl';raw.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in image_rows));ocr.enrich(raw,derived,a.output/'ocr-assets',a.exam.parent,ROOT/'weights/ocr');changed={r['id']:r for r in map(json.loads,derived.read_text().splitlines())};rows=[changed.get(r['id'],r) for r in rows]
 route_keys=sorted(config['routes'],key=lambda k:config['routes'][k]['lora'][0]['id']);cmd=[sys.executable,str(ROOT/'offline_server.py'),str(a.output/'server-network-proof.json'),str(a.server),'-m',str(ROOT/config['artifacts']['model']['filename']),'-ngl','99','-c','8192','-np','1','-t','1','-b','128','-ub','64','--jinja','--reasoning-budget','0','--host','127.0.0.1','--port','18935']
 for key in route_keys:cmd+=['--lora',str(ROOT/config['artifacts'][key]['filename'])]
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
    result=harness.run_row(row,config,digest(ROOT/'config.json'),a.exam.parent);results.append(result)
    with (a.output/'answers.jsonl').open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
   (a.output/'answers.json').write_bytes(export_answers(exam,results));status['errors']=sum(bool(r['error']) for r in results);status['network_proof']=proof;(a.output/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status))
  finally:
   server.terminate()
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait()
if __name__=='__main__':main()
