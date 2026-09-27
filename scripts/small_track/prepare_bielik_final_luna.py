#!/usr/bin/env python3
"""Verify frozen final Bielik inference and prepare fresh own-Luna packets.
No grading calls. Requires all37 transport-error-free answers; blanks preserved.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 data=[json.loads(s)for s in p.read_text().splitlines()if s.strip()]
 assert len(data)==len({x['id']for x in data}), 'Duplicate task IDs'
 return {x['id']:x for x in data}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve();paper=ROOT/'results/small_track/canonical-judge-inputs/b0';out=run/'luna_fresh_v4/packets'
 c=rows(paper/'candidate.jsonl');key=rows(paper/'judge.jsonl');answers=rows(run/'answers.jsonl');candidate_file=run.parent/'candidate.jsonl';candidate=rows(candidate_file);m=json.loads((run/'manifest.json').read_text())
 assert len(answers)==37 and set(answers)==set(c)==set(key)==set(candidate)
 assert m['complete']is True and m['answers']==37 and m['errors']==0
 assert not any(x.get('error')for x in answers.values())
 assert sha(candidate_file)==m['candidate_sha256']=='636b9897885c0ec2d2e4d6cd6c955da63b0a4157b803cb3a2583f32f4ed09fa6'
 assert m['model_sha256']=='90c3ff5f451864151793476df8ad8364b8b23e2e6cd20de7a007eeeba10a8a3e'and m['model_bytes']==1699568096
 assert m['aggregate_deployed_bytes']==1708932059 and m['trained_adapters']==0
 assert m['classifier_sha256']=='f2a63e81376f1da0a7324323b997c972151a4f7e1af002c108b7a8fd53f66312'
 assert m['classifier_bytes']+m['ocr_bytes']+m['model_bytes']==m['aggregate_deployed_bytes']
 assert m['seed']==42 and m['temperature']==0 and m['short_tokens']==500 and m['essay_tokens']==1600
 assert m['network_proof']['outbound_tcp_denied']and m['network_proof']['udp_socket_denied']
 infer=run.parent/'executed-source/infer.py';assert sha(infer)==m['code_sha256']
 assert m['runtime_binary_sha256']=='efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf'
 assert m['router_audit']['source_hashes_match']and m['router_audit']['effective_refit_weights_match']
 for i,row in candidate.items():
  assert row['question']==c[i]['question']
  assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
  if row['predicted_route']not in('closed_with_images','open_with_images'):assert not row.get('ocr_refs')
  payload={'messages':[{'role':'system','content':m['system']},{'role':'user','content':'\n\n'.join(str(row.get(k,''))for k in('context','question'))}],'temperature':0,'seed':42,'max_tokens':1600 if row.get('points',0)>=10 else 500,'chat_template_kwargs':{'enable_thinking':False},'lora':[]}
  assert hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==answers[i]['request_sha256']
 refs=[]
 for i,x in c.items():
  images=[]
  for path in x['page_images']:
   image=Path(path);image=image if image.is_absolute()else ROOT/image;images.append({'path':str(image),'sha256':sha(image)})
  task={'id':i,'paper_id':x['paper_id'],'max_points':x.get('max_points',x['points']),'category':x.get('subtype'),'question':x['question'],'original_source_text':x.get('source_text'),'original_context':x.get('context'),'answer_format':x.get('answer_format'),'candidate_answer':answers[i]['answer'],'official_solution':key[i].get('official_solution'),'official_rubric':key[i].get('rubric'),'original_images':images,'official_rubric_pdf':str(paper/'rubric.pdf'),'official_rubric_pdf_sha256':sha(paper/'rubric.pdf'),'candidate_file_sha256':sha(paper/'candidate.jsonl'),'judge_file_sha256':sha(paper/'judge.jsonl')}
  if not task['official_solution']and not task['official_rubric']:task['official_rubric_text_fallback']=json.loads((paper/'rubric_pages.json').read_text())
  dest=out/'bielik15-final'/f'{i}.json';text=json.dumps(task,ensure_ascii=False,indent=2)+'\n'
  if dest.exists():assert dest.read_text()==text, 'Frozen packet changed'
  else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
  refs.append({'id':i,'packet_path':str(dest),'packet_sha256':sha(dest)})
 manifest={'proposed_protocol':'local-luna-official-v4-imagegroups','fresh_judgments':True,'prior_marks_included':False,'prior_grade_reuse':False,'final_score_allowed':True,'full_official_task_count':37,'full_official_max_points':60,'aggregate_bytes':1708932059,'inference_gate':{'passed':True,'candidate_sha256':sha(candidate_file),'request_hashes_reconstructed':37,'model_sha256':m['model_sha256'],'runtime_change_disclosed':m['runtime_change_disclosed'],'bound_files':[{'path':str(f),'sha256':sha(f)}for f in[candidate_file,run/'manifest.json',infer,run.parent/'runtime.txt']]},'runs':[{'label':'bielik15-final','task_count':37,'original_run':str(run),'answers_file':str(run/'answers.jsonl'),'answers_file_sha256':sha(run/'answers.jsonl'),'packets':refs}]}
 dest=out/'manifest.json';dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'gate':'PASS','packets':str(out),'tasks':37,'max_points':60,'new_judge_calls':0}))
if __name__=='__main__':main()
