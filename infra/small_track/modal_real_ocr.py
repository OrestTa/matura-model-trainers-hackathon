"""Actual CPU OCR for eligible REAL official image tasks; no keys sent to OCR."""
import json,hashlib,base64,concurrent.futures,re
from pathlib import Path
from modal_specialists_ocr import app,recognize
@app.local_entrypoint(name='real')
def main():
 root=Path('data/small_track_real_training');rows=[];paths={}
 for p in sorted(Path('data/small_track').glob('*/candidate.jsonl')):
  if not re.fullmatch(r'\d{4}-\d{2}',p.parent.name) or int(p.parent.name[:4]) in {2015,2016,2023,2024}:continue
  keys={x['id']:x for x in map(json.loads,(p.parent/'judge.jsonl').read_text().splitlines())}
  for r in map(json.loads,p.read_text().splitlines()):
   k=keys[r['id']];a=k.get('official_solution','').strip()
   if r['subtype'] not in ['closed_with_images','open_with_images'] or not a or k.get('solution_requires_pdf_review') or re.search(r'Załącznik nr|rozporządzenia Ministra|Dz\.\s*U\.',a):continue
   r['_key']=k;r['_images']=[]
   for path in r['page_images']:
    b=Path(path).read_bytes();sha=hashlib.sha256(b).hexdigest();paths[sha]=path;r['_images'].append({'path':path,'sha256':sha})
   rows.append(r)
 items=[{'sha256':sha,'bytes':base64.b64encode(Path(p).read_bytes()).decode()} for sha,p in paths.items()];chunks=[items[i:i+20] for i in range(0,len(items),20)];done={};model=None
 print(json.dumps({'eligible_real_image_rows':len(rows),'unique_page_images':len(items)}),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  for result in ex.map(lambda chunk:recognize.remote(chunk),chunks):
   done.update(result['images']);model=result['model'];(root/'real-ocr-progress.json').write_text(json.dumps({'images':done,'model':model},ensure_ascii=False));print(json.dumps({'ocr_complete':len(done),'total':len(items)}),flush=True)
 groups={x:[] for x in ['closed_with_images','open_with_images']}
 for r in rows:
  ocr='\n\n'.join(done[x['sha256']]['text'] for x in r['_images']);a=r['_key']['official_solution'].strip();prompt=r.get('context','')+'\n\n'+r['question']+'\n\n[Automatyczny OCR oryginalnych stron: odczyt napisów, nie interpretacja map ani ilustracji.]\n'+ocr
  groups[r['subtype']].append({'id':r['id'],'paper_id':r['paper_id'],'year':r['year'],'category':r['subtype'],'synthetic':False,'source':'official CKE solution','source_paper_pdf':r['paper_pdf'],'source_rubric_pdf':r['_key']['rubric_pdf'],'original_page_images':r['_images'],'images_encoded_by_model':False,'actual_ocr':True,'ocr_source_hashes':[x['sha256'] for x in r['_images']],'messages':[{'role':'system','content':'Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem.'},{'role':'user','content':prompt},{'role':'assistant','content':a}]})
 m=json.loads((root/'manifest.json').read_text())
 for route,data in groups.items():
  p=root/route/'train.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data));m['files'][route]={'rows':len(data),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 m['real_image_ocr']={'model':model,'images':len(done),'rows':len(rows),'nonempty_images':sum(bool(x['text']) for x in done.values()),'no_keys_sent_to_ocr':True};(root/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(json.dumps({'ready_image_routes':m['files'],'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()}),flush=True)
