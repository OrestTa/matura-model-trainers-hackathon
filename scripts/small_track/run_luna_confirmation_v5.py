#!/usr/bin/env python3
"""Fresh, bounded Luna judging followed by one blind clarification per flagged item."""
import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from luna_confirmation_v5 import (POLICY, PROTOCOL, SCHEMA, BATCH_SCHEMA,
                                  INSTRUCTION, CLARIFICATION, policy_hash,
                                  validation_issues, choose_verdict)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)

def freeze(path, data):
    if path.exists():
        assert json.loads(path.read_text())==data, f'Frozen file changed: {path}'
    else: write(path,data)

def load_grade(out,label,name,key):
    p=out/label/'calls'/f'{name}.state.json'
    if not p.exists(): return None
    state=json.loads(p.read_text())
    if state.get('returncode')!=0: return None
    response=p.with_name(f'{name}.response.json')
    try:
        raw=json.loads(response.read_text())
        grades=raw['grades'] if 'grades' in raw else [raw]
        matches=[g for g in grades if isinstance(g,dict) and g.get('id')==key]
        return matches[0] if len(matches)==1 else None
    except (OSError,ValueError,TypeError,KeyError): return None

def make_jobs(manifest):
    jobs=[]; items=[]
    for run in manifest['runs']:
        groups={}; texts=[]
        for ref in run['packets']:
            assert sha(ref['packet_path'])==ref['packet_sha256']
            packet=json.loads(Path(ref['packet_path']).read_text())
            assert packet['id']==ref['id']
            for image in packet['original_images']: assert sha(image['path'])==image['sha256']
            spec={**ref,'packet':packet,'label':run['label']}
            items.append(spec)
            if packet['original_images']:
                group=tuple((x['path'],x['sha256']) for x in packet['original_images'])
                groups.setdefault(group,[]).append(spec)
            elif packet['category']=='essay':
                spec['initial_name']=f"{packet['id']}-essay-r1"
                for repeat in (1,2,3): jobs.append({'label':run['label'],'name':f"{packet['id']}-essay-r{repeat}",'specs':[spec],'batch':False})
            else: texts.append(spec)
        for specs in groups.values():
            name='visual-'+'-'.join(s['id'] for s in specs)
            for s in specs:s['initial_name']=name
            jobs.append({'label':run['label'],'name':name,'specs':specs,'batch':True})
        for s in texts:s['initial_name']='text-batch'
        jobs.append({'label':run['label'],'name':'text-batch','specs':texts,'batch':True})
    return jobs,items

def decision(out,spec):
    label=spec['label'];key=spec['id'];packet=spec['packet']
    primary=load_grade(out,label,spec['initial_name'],key)
    repeats=[load_grade(out,label,f'{key}-essay-r{r}',key) for r in (1,2,3)] if packet['category']=='essay' else None
    clarification=load_grade(out,label,f'clarify-{key}',key)
    result=choose_verdict(primary,packet,repeats,clarification)
    return {**result,'id':key,'category':packet['category'],'max_points':packet['max_points'],
            'packet_sha256':spec['packet_sha256'],'initial_grade':primary,
            'essay_repeats':repeats,'clarification_grade':clarification}

def report(out,items,manifest):
    result={'protocol':PROTOCOL,'policy_sha256':policy_hash(),'measurement_kind':'training_set',
            'candidate_model':'Bielik-1.5B-v3.0-Instruct','quantization':'Q8_0',
            'training_exposure':POLICY['training_exposure'],
            'base_aggregate_bytes':manifest.get('base_aggregate_bytes'),'trained_aggregate_bytes':manifest.get('trained_aggregate_bytes'),
            'model_requested':'gpt-6-luna',
            'cost':'Own Codex plan; monetary cost unknown; no Forgehand requests',
            'confirmed_means':'Complete internally consistent rubric decisions under the frozen protocol; not infallibility or generalization',
            'runs':[], 'ania_reference':{'model':'Bielik1.5','earned':15,'max':55,'percent':100*15/55,
            'closed':'5/11','open':'9/29','essay':'1/15','five_categories':'unavailable',
            'comparison':'Noncomparable adapted inputs and denominator; no numerical delta'}}
    for arm in manifest['runs']:
        verdicts=[decision(out,s) for s in items if s['label']==arm['label']]
        categories={}
        for v in verdicts:
            c=categories.setdefault(v['category'],{'max_points':0,'lower':0,'upper':0,'provisional_points':0,'resolved_items':0,'items':0})
            for k in ('max_points','lower','upper'): c[k]+=v[k]
            c['provisional_points']+=v['provisional_points'] or 0
            c['resolved_items']+=v['resolved']; c['items']+=1
        resolved=all(v['resolved'] for v in verdicts)
        for c in categories.values():
            c['confirmed_points']=c['lower'] if c['resolved_items']==c['items'] else None
            c['confirmed_percent']=100*c['confirmed_points']/c['max_points'] if c['confirmed_points'] is not None else None
            c['lower_percent']=100*c['lower']/c['max_points'];c['upper_percent']=100*c['upper']/c['max_points']
        lower=sum(v['lower'] for v in verdicts);upper=sum(v['upper'] for v in verdicts)
        result['runs'].append({'label':arm['label'],'max_points':60,'confirmed':resolved,
             'confirmed_points':lower if resolved else None,'confirmed_percent':100*lower/60 if resolved else None,
             'provisional_points':sum(v['provisional_points'] or 0 for v in verdicts),
             'lower':lower,'upper':upper,'lower_percent':100*lower/60,'upper_percent':100*upper/60,'resolved_items':sum(v['resolved'] for v in verdicts),
             'threshold_at_least35':('confirmed_pass' if lower>=21 else 'confirmed_fail') if resolved else ('bound_proves_pass_not_exact' if lower>=21 else 'bound_proves_fail_not_exact' if upper<21 else 'unresolved'),
             'categories':categories,'items':verdicts})
    if len(result['runs'])==2:
        base,trained=result['runs']
        result['paired_delta_points']=trained['confirmed_points']-base['confirmed_points'] if base['confirmed'] and trained['confirmed'] else None
        result['paired_delta_bounds']=[trained['lower']-base['upper'],trained['upper']-base['lower']]
    write(out/'report.json',result)
    lines=['# Fresh matched Luna v5 evaluation','', 'Training-set measurement: all36 canonical nonessay tasks were exposed in training. Five other official essay exemplars were used. No claim of held-out generalization.','', '| Arm | Exact points | Bounds /60 | Bounds % | Resolved items |','|---|---:|---:|---:|---:|']
    for run in result['runs']:lines.append(f"| {run['label']} | {run['confirmed_points']} | {run['lower']}–{run['upper']} | {run['lower_percent']:.2f}–{run['upper_percent']:.2f}% | {run['resolved_items']}/37 |")
    lines+=['','| Arm/category | Exact | Bounds | Maximum | Bounds % |','|---|---:|---:|---:|---:|']
    for run in result['runs']:
        for name,c in run['categories'].items():lines.append(f"| {run['label']} / {name} | {c['confirmed_points']} | {c['lower']}–{c['upper']} | {c['max_points']} | {c['lower_percent']:.2f}–{c['upper_percent']:.2f}% |")
    lines+=['',f"Matched exact delta: {result.get('paired_delta_points')} points; bounds {result.get('paired_delta_bounds')}.",'','Ania reference: Bielik1.5 15/55 (27.27%), closed5/11, open9/29, essay1/15. Five-way split unavailable; different adapted inputs/denominator, so no comparable delta.','', 'Confirmed means complete rubric decisions under this protocol, not proof of judge infallibility. Unresolved marks remain unresolved after the single predeclared clarification.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--report-only',action='store_true');a=p.parse_args()
    inp=a.packets.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    lock=(out/'runner.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=json.loads((inp/'manifest.json').read_text())
    assert manifest['protocol']==PROTOCOL and manifest['policy_sha256']==policy_hash()
    assert manifest['final_score_allowed'] is True and manifest['inference_gate']['passed'] is True
    assert [r['label'] for r in manifest['runs']]==['base','trained']
    for f in manifest['inference_gate']['bound_files']: assert sha(f['path'])==f['sha256']
    for r in manifest['runs']:
        assert len(r['packets'])==37 and len({s['id'] for s in r['packets']})==37
        assert sha(r['answers_file'])==r['answers_file_sha256']
    jobs,items=make_jobs(manifest)
    assert len(jobs)==40
    plan={'protocol':PROTOCOL,'policy_sha256':policy_hash(),'input_manifest_sha256':sha(inp/'manifest.json'),
          'model_requested':'gpt-6-luna','provider':POLICY['provider'],'reads_prior_grades':False,
          'workers':4,'initial_calls':len(jobs),'clarification_limit_per_item':1,
          'runner_sha256':sha(Path(__file__)),'validator_sha256':sha(Path(__file__).with_name('luna_confirmation_v5.py')),
          'created_before_calls':True,'cost':'Own Codex plan, unknown monetary cost'}
    freeze(out/'manifest.json',plan)
    sandbox=Path('/private/tmp/local-luna-confirmation-v5-readonly');sandbox.mkdir(exist_ok=True)
    for name,schema in [('item',SCHEMA),('batch',BATCH_SCHEMA)]:freeze(sandbox/f'{name}.schema.json',schema)
    def call(j):
        dest=out/j['label']/'calls';dest.mkdir(parents=True,exist_ok=True)
        state=dest/f"{j['name']}.state.json";hashes={s['id']:s['packet_sha256'] for s in j['specs']}
        if state.exists():
            old=json.loads(state.read_text());assert old['input_packet_hashes']==hashes and old['protocol']==PROTOCOL and old['policy_sha256']==policy_hash();return
        if (out/'STOP').exists():return
        payload=[s['packet'] for s in j['specs']] if j['batch'] else j['specs'][0]['packet']
        prompt=(CLARIFICATION if j.get('clarification') else '')+INSTRUCTION+json.dumps(payload,ensure_ascii=False)
        images=list(dict.fromkeys(i['path'] for s in j['specs'] for i in s['packet']['original_images']))
        cmd=['/opt/homebrew/bin/codex','exec','--model','gpt-6-luna','--sandbox','read-only','--ephemeral','--skip-git-repo-check','--cd',str(sandbox),'--config','model_reasoning_effort="medium"','--output-schema',str(sandbox/('batch.schema.json' if j['batch'] else 'item.schema.json')),'--output-last-message',str(dest/f"{j['name']}.response.json"),'--json']
        for image in images:cmd+=['--image',image]
        cmd+=['-']
        record={**plan,'input_packet_hashes':hashes,'status':'started','started_at_unix':time.time(),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'command':cmd,'clarification':bool(j.get('clarification'))}
        write(state,record)
        env={k:v for k,v in os.environ.items() if k in {'HOME','USER','LOGNAME','PATH','TMPDIR','CODEX_HOME','SSL_CERT_FILE','LANG','LC_ALL'}}
        try:
            r=subprocess.run(cmd,input=prompt,text=True,capture_output=True,timeout=180,env=env)
            (dest/f"{j['name']}.events.jsonl").write_text(r.stdout);(dest/f"{j['name']}.stderr.txt").write_text(r.stderr)
            record['returncode']=r.returncode
            if r.returncode:raise RuntimeError('codex_cli_nonzero')
            raw=json.loads((dest/f"{j['name']}.response.json").read_text());grades=raw['grades'] if j['batch'] else [raw]
            assert len(grades)==len(j['specs']) and {g['id'] for g in grades}==set(hashes)
            record['item_validation']={s['id']:validation_issues(next(g for g in grades if g['id']==s['id']),s['packet']) for s in j['specs']}
            record['status']='received'
        except Exception as error:record.update(status='failed_no_retry',error_type=type(error).__name__)
        record['finished_at_unix']=time.time();write(state,record)
        print(j['label'],j['name'],record['status'],flush=True)
    print(json.dumps({'initial_calls':40,'workers':4,'execute':a.execute,'protocol':PROTOCOL}),flush=True)
    if a.execute and not a.report_only:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(call,jobs))
        clarifications=[]
        for spec in items:
            if decision(out,spec)['initial_flags']:
                clarifications.append({'label':spec['label'],'name':f"clarify-{spec['id']}",'specs':[spec],'batch':False,'clarification':True})
        freeze(out/'clarification-plan.json',{'policy_sha256':policy_hash(),'items':[{'label':j['label'],'id':j['specs'][0]['id'],'packet_sha256':j['specs'][0]['packet_sha256']} for j in clarifications]})
        print(json.dumps({'blinded_clarifications':len(clarifications)}),flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(call,clarifications))
    if a.execute or a.report_only:
        result=report(out,items,manifest)
        print(json.dumps([{'arm':r['label'],'confirmed_points':r['confirmed_points'],'bounds':[r['lower'],r['upper']],'resolved':r['resolved_items']} for r in result['runs']]),flush=True)
if __name__=='__main__':main()
