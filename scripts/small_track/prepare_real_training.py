#!/usr/bin/env python3
"""Export real CKE answers only; no synthesized targets or essay rubrics."""
import json,hashlib,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/small_track_real_training'
LABELS=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=True)
 if (OUT/'manifest.json').exists():raise RuntimeError('Frozen real training snapshot exists; preserve it and use a new output version')
 groups={k:[] for k in LABELS};excluded=[];sources=[]
 for path in sorted((ROOT/'data/small_track').glob('*/candidate.jsonl')):
  if not re.fullmatch(r'\d{4}-\d{2}',path.parent.name):continue
  year=int(path.parent.name[:4])
  if year in {2015,2016,2023,2024}:continue
  judges={r['id']:r for r in map(json.loads,(path.parent/'judge.jsonl').read_text().splitlines())}
  sources.append({'year':year,'candidate_sha256':digest(path),'judge_sha256':digest(path.parent/'judge.jsonl')})
  for row in map(json.loads,path.read_text().splitlines()):
   label=row['subtype'];key=judges[row['id']];answer=key.get('official_solution','').strip()
   reason=None
   if label=='essay':reason='Official essay rubric is not an exemplar answer'
   elif not answer or key.get('solution_requires_pdf_review'):reason='No validated textual official answer'
   elif row.get('needs_image'):reason='Actual OCR pending; do not train image route as text-only'
   elif re.search(r'Załącznik nr|rozporządzenia Ministra|Dz\.\s*U\.',answer):reason='Extraction contains legal footer; needs PDF review'
   if reason:excluded.append({'id':row['id'],'category':label,'reason':reason});continue
   prompt=row.get('context','')+'\n\n'+row['question']
   groups[label].append({'id':row['id'],'paper_id':row['paper_id'],'year':year,'category':label,'synthetic':False,'source':'official CKE extracted solution','official_solution_sha256':hashlib.sha256(answer.encode()).hexdigest(),'source_paper_pdf':row['paper_pdf'],'source_rubric_pdf':key['rubric_pdf'],'original_page_images':row['page_images'],'images_encoded_by_model':False,'messages':[{'role':'system','content':'Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem.'},{'role':'user','content':prompt},{'role':'assistant','content':answer}]})
 files={}
 for label,rows in groups.items():
  d=OUT/label;d.mkdir(exist_ok=True);p=d/'train.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[label]={'rows':len(rows),'sha256':digest(p)}
 manifest={'synthetic':False,'sources':sources,'excluded_years':[2015,2016,2023,2024],'files':files,'excluded':excluded,'status':'First real text-only batch; image OCR and actual essay exemplars unavailable; extraction heuristic, not exhaustive manual validation','loss':'assistant-only, enforced by trainer'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps({'output':str(OUT),'counts':files,'excluded':len(excluded),'manifest_sha256':digest(OUT/'manifest.json')}))
if __name__=='__main__':main()
