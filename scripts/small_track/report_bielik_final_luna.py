#!/usr/bin/env python3
"""Mechanical report of saved fresh Luna judgments; never calls a model."""
from pathlib import Path
import json,hashlib
import argparse
parser=argparse.ArgumentParser(description='Aggregate saved fresh Luna verdicts without adjudication.')
parser.add_argument('--packets',type=Path,required=True);parser.add_argument('--grades',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[2];r=root/'results/small_track';packets=args.packets.resolve();source=args.grades.resolve();manifest=json.loads((packets/'manifest.json').read_text());categories=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']

def rows(p):return {x['id']:x for x in map(json.loads,p.read_text().splitlines())}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=rows(r/'canonical-judge-inputs/b0/candidate.jsonl'); reports=[]
for arm in manifest['runs']:
 refs={p['id']:p for p in arm['packets']}; label=arm['label']; d=r/arm['original_run']; answers=rows(d/'answers.jsonl'); grades={}; raw={}; failures=[]
 for state_path in (source/label/'calls').glob('*.state.json'):
  state=json.loads(state_path.read_text())
  if state.get('status')!='failed_no_retry':continue
  failures.append({'path':str(state_path),'error_type':state.get('error_type')}); response=state_path.with_name(state_path.name.replace('.state.json','.response.json'))
  if not response.exists():continue
  try:obj=json.loads(response.read_text())
  except ValueError:continue
  for g in obj.get('grades',[obj]):
   i=g.get('id')
   if i not in refs or state.get('input_packet_hashes',{}).get(i)!=refs[i]['packet_sha256']:continue
   if i=='26' and not state.get('name','').endswith('-r1'):continue
   if type(g.get('earned_points'))is int and 0<=g['earned_points']<=c[i]['max_points']:raw[i]={'grade':g,'source':str(response)}
 for i,ref in refs.items():
  packet=json.loads(Path(ref['packet_path']).read_text());assert sha(Path(ref['packet_path']))==ref['packet_sha256'];assert answers[i]['answer']==packet['candidate_answer']
  p=source/label/'items'/f'{i}.json'
  if i=='26':
   paths=[source/label/'essay_repeats'/f'26-r{n}.json'for n in (1,2,3)]
   if not all(q.exists()for q in paths):continue
   triple=[json.loads(q.read_text())for q in paths]
   assert all(x['packet_sha256']==ref['packet_sha256']for x in triple)
   marks=[(x['grade']['earned_points'],x['grade']['uncertain'])for x in triple]; record=triple[0]; record['grade']={**record['grade'],'uncertain':record['grade']['uncertain']or len(set(marks))>1}; record['repeat_policy']={'points':[m[0]for m in marks],'uncertainty_flags':[m[1]for m in marks],'disagreement':len(set(marks))>1,'first_mark_retained':True,'sources':[str(q)for q in paths]}
  elif p.exists():record=json.loads(p.read_text())
  else:continue
  assert record['packet_sha256']==ref['packet_sha256']; assert record['protocol']=='local-luna-official-v4-imagegroups' and record['model_requested']=='gpt-6-luna'
  grades[i]=record
 full=len(answers)==37 and set(answers)==set(c) and all(not a.get('error')for a in answers.values())
 uncertain=[i for i in c if i not in grades or grades[i]['grade']['uncertain']]; lower=sum(g['grade']['earned_points']for i,g in grades.items()if i not in uncertain); upper=lower+sum(c[i]['max_points']for i in uncertain)
 available=all(i in grades or i in raw for i in c); primary=sum(grades[i]['grade']['earned_points']if i in grades else raw.get(i,{}).get('grade',{}).get('earned_points',0)for i in c)if available else None
 cats=[]
 for category in categories:
  ids=[i for i in c if c[i]['subtype']==category]; maximum=sum(c[i]['max_points']for i in ids); lo=sum(grades[i]['grade']['earned_points']for i in ids if i in grades and i not in uncertain); hi=lo+sum(c[i]['max_points']for i in ids if i in uncertain); covered=all(i in grades or i in raw for i in ids); score=sum(grades[i]['grade']['earned_points']if i in grades else raw[i]['grade']['earned_points']for i in ids)if covered else None
  cats.append({'category':category,'max_points':maximum,'primary_provisional_points':score,'primary_provisional_percent':100*score/maximum if score is not None else None,'settled_lower_points':lo,'unresolved_upper_points':hi,'exact_points':lo if lo==hi else None,'uncertain_or_missing_ids':[i for i in ids if i in uncertain]})
 report={'label':label,'run':str(d),'candidate_inference_complete':full,'answer_count':len(answers),'aggregate_bytes':1708932059,'caps':[500,1600],'answers_sha256':sha(d/'answers.jsonl'),'validated_tasks':len(grades),'missing_ids':[i for i in c if i not in grades],'uncertain_ids':[i for i in grades if grades[i]['grade']['uncertain']],'official_max_points':60,'primary_provisional_points':primary if full else None,'settled_lower_points':lower if full else None,'unresolved_upper_points':upper if full else None,'exact_points':lower if full and lower==upper else None,'five_categories':cats,'essay_repeats':grades.get('26',{}).get('repeat_policy'),'failed_calls':failures,'raw_invalid_metadata_marks':raw,'threshold_at_least35_proved_by_lower_bound':full and lower>=21,'threshold_above35_proved_by_lower_bound':full and lower>=22}
 dest=d/'luna_fresh_v4';dest.mkdir(exist_ok=True);(dest/'grades.luna.jsonl').write_text(''.join(json.dumps({'id':i,**g},ensure_ascii=False)+'\n'for i,g in grades.items()));(dest/'summary.luna.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');reports.append(report)
x=reports[0]
report={'model':'Bielik-1.5B-v3.0-Instruct','quantization':'Q8_0','aggregate_bytes':1708932059,'recipe':'Zero adapters, frozen eligible real-only router and image-route OCR','pipeline_boundary':'Fresh answer inference on a frozen previously computed OCR/router candidate; OCR and routing were not re-executed.','protocol':'local-luna-official-v4-imagegroups','fresh_judgments':True,'prior_grade_reuse':False,'judge':'Own ChatGPT Codex gpt-6-luna only','model_identity_evidence':'Explicit --model gpt-6-luna, no fallback; CLI does not echo resolved model identity.','run':x,'inference_gate':manifest['inference_gate'],'historical_reference':{'run':'20260926-2115-bielik15-q8-full-epoch-offline/paired-baseline','primary_points':16,'settled_bounds':[16,19],'max_points':60,'five_categories':[{'category':c,'primary_points':n,'max_points':d}for c,n,d in zip(categories,[2,4,5,5,0],[4,7,11,23,15])],'caveat':'Same selected recipe, but server runtime changed from f805c57a2 to81bc6b8. This is a fresh development verification, not a controlled optimization or untouched holdout.'},'base_vs_optimized_delta':'Not measured: this fresh run verifies the selected base+OCR/router recipe; no new optimization arm. Historical score change cannot be attributed to model improvement.','ania_reference':'Ania Bielik1.5 reference15/55=27.27%,closed5/11,open9/29,essay1/15. Adapted inputs and55point subset differ; five-way reference unavailable; no comparable numeric delta.','interpretation':'Only saved Luna verdicts aggregated. First essay mark retained, repeat disagreement unresolved. Missing/image-metadata-invalid items retain full-point uncertainty bounds. No assistant adjudication or averaging.','cost':'Own Codex plan; monetary cost unknown. No Forgehand judging API.'}
historical_answers=rows(r/'20260926-2115-bielik15-q8-full-epoch-offline/paired-baseline/answers.jsonl');fresh_answers=rows(Path(x['run'])/'answers.jsonl');report['historical_answer_identity']={'identical':sum(fresh_answers[i]['answer']==historical_answers[i]['answer']for i in fresh_answers),'total':37,'interpretation':'Changed outputs on the same request inputs demonstrate that this is not an exact historical replay; runtime differs.'}
p=args.report.resolve();p.parent.mkdir(parents=True,exist_ok=True);p.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
lines=['# Fresh Bielik1.5 Q8_0 verification','',f"Package:1,708,932,059bytes. Answers:{x['answer_count']}/37; validated grading:{x['validated_tasks']}/37. Fresh own-Codex Luna v4; no reused verdicts.",'','| Category | Primary/provisional | Settled lower | Unresolved upper |','|---|---:|---:|---:|']
for c in x['five_categories']:
 score='pending'if c['primary_provisional_points']is None else f"{c['primary_provisional_points']}/{c['max_points']} ({c['primary_provisional_percent']:.2f}%)"
 lines.append(f"| {c['category']} | {score} | {c['settled_lower_points']} | {c['unresolved_upper_points']} |")
lines+=['',f"Primary/provisional:{x['primary_provisional_points']}/60. Settled lower:{x['settled_lower_points']}/60; unresolved upper:{x['unresolved_upper_points']}/60. Exact:{x['exact_points']}. Essay checks:{x['essay_repeats']}. Missing:{x['missing_ids']}; uncertain:{x['uncertain_ids']}.",'',report['pipeline_boundary'],'',str(report['historical_answer_identity']),'',report['base_vs_optimized_delta'],'','Historical selected recipe:primary16/60,bounds16–19; five2/4,4/7,5/11,5/23,0/15. Runtime changed; no controlled causal delta.','',report['ania_reference'],'',report['interpretation'],'',report['cost']];p.with_suffix('.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:x[k]for k in['answer_count','validated_tasks','primary_provisional_points','settled_lower_points','unresolved_upper_points','exact_points','essay_repeats']},indent=2))
