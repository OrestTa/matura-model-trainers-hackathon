import json,hashlib,re,collections,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/small_track'))
from repair_real_training import SYSTEM,normalize_target,repaired_prompt
from train_router import LABELS,fit,predict
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def main():
 dest=ROOT/'data/small_track_real_training_all_papers_v2'
 if dest.exists():raise RuntimeError('Frozen output exists')
 groups={k:[] for k in LABELS};known={};sources=[];excluded=[];router=[]
 for p in (ROOT/'data/small_track_real_training_boundary_clean_v3').glob('*/train.jsonl'):
  for r in read(p):known[r['id']]=r
 for p in sorted((ROOT/'data/small_track').glob('????-??/candidate.jsonl')):
  keys={r['id']:r for r in read(p.parent/'judge.jsonl')};m=json.loads((p.parent/'manifest.json').read_text());sources.append({'paper_id':p.parent.name,'candidate_sha256':sha(p),'judge_sha256':sha(p.parent/'judge.jsonl'),'official_files':m['files']})
  for c in read(p):
   label=c['subtype'];key=keys[c['id']];answer=key.get('official_solution','').strip();reason=None
   features={k:c[k] for k in ('question','max_points','needs_image') if k in c};router.append((features,label))
   if c['id'] in known:groups[label].append(known[c['id']]);continue
   if label=='essay':reason='Rubric is not a model essay; official exemplars added separately'
   elif label.endswith('with_images'):reason='No accepted candidate-only OCR boundary review; not trained text-only'
   elif not answer or key.get('solution_requires_pdf_review'):reason='No validated official answer extraction'
   elif re.search(r'Załącznik nr|rozporządzenia Ministra|Dz\.\s*U\.',answer):reason='Contaminated legal footer in answer extraction'
   if reason:excluded.append({'id':c['id'],'category':label,'reason':reason});continue
   target,changes=normalize_target(answer,c['question'])
   groups[label].append({'id':c['id'],'paper_id':c['paper_id'],'year':c['year'],'category':label,'synthetic':False,'source':'official CKE extracted solution','source_paper_pdf':c['paper_pdf'],'source_rubric_pdf':key['rubric_pdf'],'official_solution_sha256':hashlib.sha256(answer.encode()).hexdigest(),'target_changes':changes,'original_page_images':[],'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':repaired_prompt(c)},{'role':'assistant','content':target}]})
 # Canonical 2023 organizer inputs replace duplicated raw-PDF text rows.
 canonical=ROOT/'data/small_track/official_mock_v1/canonical-real-router-ocr-candidate.jsonl'
 ckeys={r['id']:r for r in read(ROOT/'results/small_track/canonical-judge-inputs/b0/judge.jsonl')}
 for route in groups:groups[route]=[r for r in groups[route] if r['paper_id']!='2023-05']
 excluded=[r for r in excluded if not r['id'].startswith('2023-05-z')]
 for c in read(canonical):
  k=ckeys[c['id']];label=c['subtype'];answer=k.get('official_solution','').strip()
  if label=='essay' or not answer or k.get('solution_requires_pdf_review'):
   excluded.append({'id':k['original_official_id'],'category':label,'reason':'No official exemplar answer or unresolved official extraction'});continue
  images=[]
  for image in c.get('images',[]):
   path=ROOT/'data/small_track/official_mock_v1'/image['path'];assert sha(path)==image['sha256'];images.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
  target,changes=normalize_target(answer,c['question'])
  groups[label].append({'id':k['original_official_id'],'paper_id':'2023-05','year':2023,'category':label,'synthetic':False,'source':'official CKE key paired to organizer canonical inputs','canonical_input_sha256':sha(canonical),'source_paper_pdf':'data/small_track/2023-05/paper.pdf','source_rubric_pdf':k['rubric_pdf'],'original_page_images':images,'ocr_provenance':'Existing offline original task-crop OCR; original image hashes verified; no generated visual descriptions','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':repaired_prompt(c)},{'role':'assistant','content':target}]})
 for r in known.values():
  if r['category']=='essay':groups['essay'].append(r);router.append(({'question':r['messages'][1]['content'],'max_points':r.get('official_max_points',15),'needs_image':False},'essay'))
 legacy=ROOT/'data/small_track_legacy_audit_20260927/optional-text-training.jsonl'
 for r in read(legacy):groups[r['category']].append(r);router.append(({'question':r['messages'][1]['content'],'max_points':1,'needs_image':False},r['category']))
 dest.mkdir();files={}
 for route,rows in groups.items():
  assert len({r['id'] for r in rows})==len(rows)
  for r in rows:assert r['synthetic'] is False and [m['role'] for m in r['messages']]==['system','user','assistant'] and r['messages'][-1]['content'].strip()
  p=dest/route/'train.jsonl';p.parent.mkdir();p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[route]={'rows':len(rows),'sha256':sha(p)}
 model=fit(router)
 for label in LABELS:model['weights'][label]={k:v for k,v in model['weights'][label].items() if v!=model['unknown'][label]}
 model['provenance']={'training_scope':'all_available_official_papers_no_holdouts','synthetic':False,'train_rows':len(router),'validation_rows':0,'label_source':'candidate-only heuristic weak labels; not human accuracy','answer_keys_used_as_features':False}
 p=dest/'router.json';p.write_text(json.dumps(model,ensure_ascii=False));routermeta={'sha256':sha(p),'bytes':p.stat().st_size,'rows':len(router),'training_agreement':sum(predict(r,model)['subtype']==k for r,k in router)/len(router)}
 manifest={'training_scope':'all_available_official_papers_no_holdouts','synthetic':False,'rows':sum(len(r) for r in groups.values()),'files':files,'excluded_years':[],'source_papers':sources,'included_years':sorted({r['year'] for rows in groups.values() for r in rows}),'rows_by_year':dict(sorted(collections.Counter(str(r['year']) for rows in groups.values() for r in rows).items())),'excluded_rows':excluded,'legacy_reviewed_file':{'path':str(legacy.relative_to(ROOT)),'sha256':sha(legacy)},'legacy_missing_or_unreviewed_years':[2007,2008,2009,2010,2011,2013],'coverage_note':'All available approved rows, no year holdouts. Not all downloaded papers/tasks usable: legacy extraction and image OCR review gaps remain. 2023/2024 future scores are training-set performance. Existing clean-v3 image boundaries preserved. No synthesized targets or rubric essays.','router':routermeta,'loss':'assistant-only'}
 (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps({'path':str(dest),'sha256':sha(dest/'manifest.json'),'rows':manifest['rows'],'files':files,'years':manifest['included_years'],'router':routermeta}))
if __name__=='__main__':main()
