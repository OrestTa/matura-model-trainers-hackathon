#!/usr/bin/env python3
"""Train candidate-only router against the exact real-specialist split labels."""
import collections,hashlib,json
from pathlib import Path
from train_router import fit,predict,LABELS
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 data=ROOT/'data/small_track_real_training';candidates={};train=[];valid=[];sources=[]
 for p in (ROOT/'data/small_track').glob('????-??/candidate.jsonl'):
  if int(p.parent.name[:4]) in [2015,2016,2023,2024]:continue
  for r in map(json.loads,p.read_text().splitlines()):candidates[r['id']]=r
 for route in LABELS:
  p=data/route/'train.jsonl';sources.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'label':route})
  for r in map(json.loads,p.read_text().splitlines()):
   assert r['synthetic'] is False and r['category']==route
   if r['id'] in candidates:
    c=candidates[r['id']];assert c['subtype']==route
    row={k:c[k] for k in ('question','max_points','points','needs_image') if k in c}
   else:
    assert route=='essay' and r.get('source_url','').startswith('https://bip.cke.gov.pl/')
    row={'question':r['messages'][1]['content'],'max_points':r['official_max_points'],'needs_image':False}
   assert not {'answer','answers','official_solution','rubric','messages'}&row.keys()
   (valid if r['year']==2026 else train).append((row,route))
 model=fit(train)
 for label in LABELS:model['weights'][label]={w:v for w,v in model['weights'][label].items() if v!=model['unknown'][label]}
 confusion={k:collections.Counter() for k in LABELS}
 for row,label in valid:confusion[label][predict(row,model)['subtype']]+=1
 correct=sum(confusion[k][k] for k in LABELS)
 model['provenance']={'source_files':sources,'source_manifest_sha256':sha(data/'manifest.json'),'training_labels':'Exact same category field as real specialist data; heuristic candidate answer-format labels, not human-verified','training_features':'Candidate question unigrams/bigrams, supplied image dependency and points ONLY; no answers, keys, rubric, grades','train_rows':len(train),'validation_rows':len(valid),'split':'Entire2026paperheldout;2015/16reserved and2023/24evaluated papers excluded; separateofficialguideessayexamples remaintraining','official_exam_years_used':[2017,2018,2019,2020,2021,2022,2025],'synthetic':False,'old_router_unchanged':True}
 model['validation']={'metric':'Agreement with specialist split weak labels on heldout2026 paper, not human route accuracy','correct':correct,'total':len(valid),'accuracy':correct/len(valid),'confusion':confusion,'essay_holdout_support':sum(label=='essay' for _,label in valid)}
 dest=ROOT/'artifacts/small_track/router-real-specialist-aligned-v1.json';dest.write_text(json.dumps(model,ensure_ascii=False));result={'path':str(dest.relative_to(ROOT)),'bytes':dest.stat().st_size,'sha256':sha(dest),'validation':model['validation'],'training_rows':len(train)};print(json.dumps(result,ensure_ascii=False));(dest.parent/'router-real-specialist-aligned-v1-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
