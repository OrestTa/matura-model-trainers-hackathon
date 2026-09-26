#!/usr/bin/env python3
"""Create candidate-only visual QA packets; never declare guessed crops safe."""
import json,re,hashlib,collections
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[2]
def main():
 source=ROOT/'data/small_track_real_training';out=ROOT/'data/small_track_real_training_ocr_audit_v1';out.mkdir(exist_ok=True);ocr=json.loads((source/'real-ocr-progress.json').read_text())['images'];candidates={};docs={};packets=[];quarantine=[];counts=collections.Counter()
 for p in (ROOT/'data/small_track').glob('????-??/candidate.jsonl'):
  if int(p.parent.name[:4]) in (2015,2016,2023,2024):continue
  candidates.update({r['id']:r for r in map(json.loads,p.read_text().splitlines())})
 for route in ['closed_with_images','open_with_images']:
  for r in map(json.loads,(source/route/'train.jsonl').read_text().splitlines()):
   target=r['id'].split('-z')[-1];headers=set()
   for im in r['original_page_images']:headers|=set(re.findall(r'Zadanie\s+(\d+(?:\.\d+)?)',ocr[im['sha256']]['text']))
   state='only_exact_target' if headers=={target} else ('none' if not headers else ('same_major' if all(h.split('.')[0]==target.split('.')[0] for h in headers) else 'other_major'));counts[(route,state)]+=1
   if state!='only_exact_target':quarantine.append({'id':r['id'],'route':route,'ocr_header_status':state,'headers':sorted(headers),'boundary_status':'unverified_no_crop_or_trim_permitted'});continue
   c=candidates[r['id']];pdf=c['paper_pdf'];doc=docs.setdefault(pdf,pymupdf.open(ROOT/pdf));images=[]
   for im in r['original_page_images']:
    path=ROOT/im['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==im['sha256'];n=int(path.stem);native=doc[n-1].get_text(sort=True);nh=re.findall(r'Zadanie\.?\s+(\d+(?:\.\d+)?)',native)
    images.append({'path':im['path'],'sha256':im['sha256'],'paper_pdf':pdf,'pdf_page':n,'native_detected_headers':sorted(set(nh)),'actual_ocr_text':ocr[im['sha256']]['text']})
   packets.append({'id':r['id'],'route':route,'expected_task_id':target,'question':c['question'],'context':c.get('context',''),'images':images,'boundary_status':'PENDING visual QA; matching OCR header alone is not proof','qa_instruction':'Inspect original page images. Determine whether OCR includes neighboring task question/source material, whether required current-task visual source is complete, and whether task-page association is unambiguous. Do not answer or grade the history task. Return accept/reject/uncertain with evidence. No cropping has occurred.'})
 assert len(packets)==39;assert all(not {'answer','official_solution','rubric','messages'}&r.keys() for r in packets)
 (out/'candidate-only-packets.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in packets));(out/'quarantined.json').write_text(json.dumps(quarantine,ensure_ascii=False,indent=2));manifest={'candidate_rows':len(packets),'route_counts':dict(collections.Counter(r['route'] for r in packets)),'quarantined_rows':len(quarantine),'all_header_counts':{str(k):v for k,v in counts.items()},'status':'All39pendingimageboundaryQA; zeroacceptedtrainingrows','no_keys_or_answers_in_packets':True,'input_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()};(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
if __name__=='__main__':main()
