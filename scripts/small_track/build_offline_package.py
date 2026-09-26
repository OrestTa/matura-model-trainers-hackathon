#!/usr/bin/env python3
"""Build a versioned offline package; no downloads or inference at build time."""
import argparse,json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RECOVERY='orestta/matura-small-track-recovery';REV='7c015a205cf7b45f0d8dc507430133ea447b3d44'
def main():
 p=argparse.ArgumentParser();p.add_argument('--quant',choices=['q4','q8'],default='q4');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve previous package')
 a.output.mkdir(parents=True);c=json.loads((ROOT/f'infra/small_track/configs/bielik15-{a.quant}-real-five-adapter-boundary-clean-v3.json').read_text());weights=[]
 for key,art in c['artifacts'].items():
  original=ROOT/art['filename'];name='weights/'+('base.gguf' if key=='model' else key+'.gguf')
  source={'repo':art['repo'],'revision':art['revision'],'filename':art['filename'],'private':False} if key=='model' else {'repo':RECOVERY,'revision':REV,'filename':f'models/bielik15/adapters-real-boundary-clean-v3-20260926/{key}/adapter-f16.gguf','private':True}
  weights.append({'path':name,'bytes':art['bytes'],'sha256':art['sha256'],'source':source});art['filename']=name
  if original.is_file():
   target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
 for art in c['auxiliary_artifacts']:
  original=ROOT/art['filename'];name='weights/router.json' if art['role']=='router' else 'weights/ocr/'+original.name
  remote='router/real-specialist-aligned-v1.json' if art['role']=='router' else 'ocr/weights/'+original.name
  weights.append({'path':name,'bytes':art['bytes'],'sha256':art['sha256'],'source':{'repo':RECOVERY,'revision':REV,'filename':remote,'private':True}});art['filename']=name;target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
 for r in c['routes'].values():r['base_url']='http://127.0.0.1:18935/v1'
 (a.output/'config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2));m={'name':c['name'],'logical_models':6,'shared_base_count':1,'trained_adapters':5,'classifier_count':1,'ocr_auxiliary_weights':2,'aggregate_weight_bytes':sum(x['bytes'] for x in weights),'weights':weights,'evaluation_status':'Below35percent target; no passing claim','caption_auxiliary':'Rejected; not included'};assert m['aggregate_weight_bytes']==c['aggregate_weight_bytes'];(a.output/'weights-manifest.json').write_text(json.dumps(m,indent=2))
 for name in ['package_run.py','harness.py','infer.py','classifier.py','train_router.py','official_format.py','ocr.py','voting.py']:
  shutil.copyfile(ROOT/'scripts/small_track'/name,a.output/('run.py' if name=='package_run.py' else name))
 shutil.copyfile(ROOT/'scripts/small_track/offline_server.py',a.output/'offline_server.py')
 (a.output/'restore.py').write_text("from pathlib import Path\nimport json,hashlib,shutil\nfrom huggingface_hub import hf_hub_download\np=Path(__file__).resolve().parent\nfor a in json.loads((p/'weights-manifest.json').read_text())['weights']:\n f=p/a['path'];f.parent.mkdir(parents=True,exist_ok=True)\n if not f.exists():\n  s=a['source'];q=hf_hub_download(s['repo'],s['filename'],revision=s['revision'],token=True if s['private'] else False);shutil.copyfile(q,f)\n with f.open('rb') as h:checksum=hashlib.file_digest(h,'sha256').hexdigest()\n assert f.stat().st_size==a['bytes'] and checksum==a['sha256']\nprint('All pinned weights restored and verified; no inference launched')\n")
 shutil.copyfile(ROOT/'docs/SMALL_TRACK_OFFLINE_PACKAGE.md',a.output/'README.md')
 code_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.glob('*.py')};(a.output/'code-manifest.json').write_text(json.dumps(code_hashes,indent=2))
 print(json.dumps({'package':str(a.output),'weight_bytes':m['aggregate_weight_bytes'],'missing_weights':[x['path'] for x in weights if not(a.output/x['path']).exists()]}))
if __name__=='__main__':main()
