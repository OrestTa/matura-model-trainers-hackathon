#!/usr/bin/env python3
"""Freeze real-only repaired training after candidate-only OCR boundary review."""
import collections, hashlib, json
from pathlib import Path
from repair_real_training import SYSTEM
from luna_ocr_boundary_qa import validate_response
ROOT=Path(__file__).resolve().parents[2]
GUIDE_ID='cke-supplement20230111-essay-dictatorships'
GUIDE_SHA='0ba26d9d27cafea6c367693ffc5d8c0d157a7c4774a37f9a9ad4ac2a84981aff'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def eligible(r):
 if r.get('synthetic') is not False:raise ValueError('Only official real answers')
 if r['year'] in (2015,2016,2023,2024):
  if not(r['id']==GUIDE_ID and r['category']=='essay' and r['source_pdf_sha256']==GUIDE_SHA and r['paper_id']=='cke-supplement20230111'):
   raise ValueError('Reserved/evaluation paper excluded')
def main():
 source=ROOT/'data/small_track_real_training_runtime_v2';audit=ROOT/'data/small_track_real_training_ocr_audit_v1';reviews=audit/'luna-boundaries';dest=ROOT/'data/small_track_real_training_boundary_clean_v3'
 if dest.exists():raise RuntimeError('Frozen destination exists')
 packets=read(audit/'candidate-only-packets.jsonl');decisions={};excluded=[]
 for r in packets:
  directory=reviews/r['id'];state_path=directory/'state.json'
  if not state_path.exists():raise RuntimeError('Review not started '+r['id'])
  state=json.loads(state_path.read_text())
  if state['status']=='started':raise RuntimeError('Review still running '+r['id'])
  if state['status']=='completed':
   response=directory/'response.json';v=validate_response(json.loads(response.read_text()),r)
   if v['decision']=='accept':decisions[r['id']]={'response_sha256':sha(response),'state_sha256':sha(state_path),'image_sha256s':[i['sha256'] for i in r['images']]};continue
  excluded.append({'id':r['id'],'state':state})
 essays_path=ROOT/'data/small_track_essay_research/cke-20230111/official-five-essay-candidate.jsonl'
 groups={};excluded_other=[]
 for p in sorted(source.glob('*/train.jsonl')):
  route=p.parent.name
  if route=='essay':rows=read(essays_path)
  else:rows=read(p)
  kept=[]
  for r in rows:
   eligible(r)
   if route.endswith('with_images') and r['id'] not in decisions:
    excluded_other.append(r['id']);continue
   target=r['messages'][-1]['content'];r['messages'][0]={'role':'system','content':SYSTEM}
   if route.endswith('with_images'):r['boundary_review_provenance']=decisions[r['id']]
   if r['id']==GUIDE_ID:r['source_allowlist']={'id':GUIDE_ID,'pdf_sha256':GUIDE_SHA,'reason':'Official worked guide example, not evaluation examination; broad historical overlap disclosed','publication_year_retained':2023}
   assert r['messages'][-1]['content']==target
   kept.append(r)
  groups[route]=kept
 assert len(groups['closed_without_images'])+len(groups['open_without_images'])==101
 assert len(groups['essay'])==5
 assert sum(len(x) for k,x in groups.items() if k.endswith('with_images'))==len(decisions)
 dest.mkdir();files={}
 for route,rows in groups.items():
  out=dest/route/'train.jsonl';out.parent.mkdir();out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[route]={'rows':len(rows),'sha256':sha(out)}
 manifest={'status':'DATA ONLY; no training launched; accepted whole-page OCR is not cropped visual understanding','rows':sum(len(x) for x in groups.values()),'files':files,'source_manifest_sha256':sha(source/'manifest.json'),'packets_sha256':sha(audit/'candidate-only-packets.jsonl'),'essay_file_sha256':sha(essays_path),'accepted_image_ids':sorted(decisions),'review_exclusions':excluded,'all_excluded_image_ids':excluded_other,'excluded_exam_years':[2015,2016,2023,2024],'guide_allowlist':[{'id':GUIDE_ID,'pdf_sha256':GUIDE_SHA}],'no_generated_factual_targets':True,'targets_unchanged':True,'review_model':'gpt-6-luna','review_purpose':'candidate boundary only, not answer grading'}
 (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps({'rows':manifest['rows'],'files':files,'manifest_sha256':sha(dest/'manifest.json')}))
if __name__=='__main__':main()
