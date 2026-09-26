import urllib.request,concurrent.futures,json,hashlib
from pathlib import Path
import pymupdf
root=Path.cwd();base=root/'data/small_track_legacy';urls=json.loads((base/'discovered_urls.json').read_text())
def one(y):
 d=base/f'{y}-05';d.mkdir(exist_ok=True);m={'year':int(y),'paper_id':f'{y}-05','session':'main','formula':'pre-2015','split':'training_eligible','download_host':'arkusze.pl mirror','official_origin':'CKE document; mirror provenance, not direct CKE hosting','license':'Copyright CKE; no open redistribution license verified','files':{}}
 for k,u in zip(('paper','rubric'),urls[y]):
  p=d/f'{k}.pdf';b=urllib.request.urlopen(u,timeout=60).read();assert b.startswith(b'%PDF');p.write_bytes(b)
  doc=pymupdf.open(p);pages=[{'page':i+1,'text':pg.get_text(sort=True)} for i,pg in enumerate(doc)]
  (d/f'{k}_pages.json').write_text(json.dumps(pages,ensure_ascii=False));m['files'][k]={'url':u,'path':str(p.relative_to(root)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'pages':len(doc),'cover_text':pages[0]['text'][:2500]}
 m['status']='PDFs downloaded; legacy task/key alignment not yet validated';(d/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(y,{k:v['pages'] for k,v in m['files'].items()},flush=True);return m
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as e:rows=list(e.map(one,urls))
(base/'manifest.json').write_text(json.dumps({'papers':rows},ensure_ascii=False,indent=2))
