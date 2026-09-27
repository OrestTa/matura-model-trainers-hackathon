#!/usr/bin/env python3
"""Gate a full fresh matched all-papers run and freeze blind Luna v5 packets."""
import argparse
import hashlib
import json
from pathlib import Path
from luna_confirmation_v5 import POLICY, PROTOCOL, policy_hash
from run_luna_confirmation_v5 import freeze, sha
ROOT=Path(__file__).resolve().parents[2]
ROUTES=['closed_without_images','open_without_images','closed_with_images','open_with_images','essay']

def rows(path):
    data=[json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]
    assert len(data)==len({x['id'] for x in data}), 'Duplicate IDs'
    return {x['id']:x for x in data}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run=a.evaluation.resolve();out=a.output.resolve();cfgpath=a.config.resolve()
    paper=ROOT/'results/small_track/canonical-judge-inputs/b0'
    c=rows(paper/'candidate.jsonl');keys=rows(paper/'judge.jsonl')
    source=run.parent/'candidate.jsonl';candidate=rows(source)
    mpath=run/'manifest.json';m=json.loads(mpath.read_text());cfg=json.loads(cfgpath.read_text())
    handpath=run/'verified_lora_handshake.json';hand=json.loads(handpath.read_text())
    reports_path=run.parent/'adapter-manifests.json'
    assert sha(reports_path)==m['adapter_manifests_sha256']
    reports={x['route']:x for x in json.loads(reports_path.read_text())}
    assert set(reports)==set(ROUTES)
    assert all(m[k]==v for k,v in cfg.items()), 'Frozen config differs from executed manifest'
    assert sum(x['steps'] for x in reports.values())==225
    infer=run.parent/'executed-source/infer.py'
    if not infer.exists(): infer=run.parent/'infer.py'
    assert sha(infer)==m['code_sha256']
    training=ROOT/'data/small_track_real_training_all_papers_v2/manifest.json'
    assert sha(training)==POLICY['training_manifest_sha256']==m['dataset_manifest_sha256']
    assert m['judge_policy_sha256']==policy_hash(), 'Policy must be bound before inference'
    assert sha(source)==m['candidate_sha256']
    assert len(c)==37 and set(c)==set(candidate)==set(keys) and sum(x['max_points'] for x in c.values())==60
    assert m['seed']==42 and m['temperature']==0 and m['caps']==[500,1600]
    assert m['network_proof']['outbound_tcp_denied'] and m['network_proof']['udp_socket_denied']
    assert hand['verified'] is True
    expected=hand['expected'];loaded=hand['loaded']
    assert expected==m['expected_adapters'] and loaded==m['loaded_adapters']
    assert len(expected)==len(loaded)==5 and {x['id'] for x in loaded}==set(range(5))
    for i,route in enumerate(ROUTES):
        e=next(x for x in expected if x['id']==i);l=next(x for x in loaded if x['id']==i);art=reports[route]
        assert e['scale']==l['scale']==0 and e['path']==l['path'] and Path(e['path']).parent.name==route
        assert e['sha256']==art['sha256'] and e['bytes']==art['bytes']
    answers={arm:rows(run/arm/'answers.jsonl') for arm in ['base','trained']}
    for arm,data in answers.items():
        assert set(data)==set(c) and len(data)==37
        assert not any(x.get('error') for x in data.values())
        assert all(isinstance(x['answer'],str) for x in data.values()), 'Preserve empty answers as strings'
    for key,row in candidate.items():
        assert not {'answer','answers','rubric','gold','solution','official_solution'}.intersection(row)
        for field in ('question','source_text','answer_format','page_images','images','max_points'):
            assert row[field]==c[key][field], f'Original field altered: {key}/{field}'
        assert row['context'].startswith(c[key]['context'])
        route=row['predicted_route'];assert route in ROUTES
        if route not in ('closed_with_images','open_with_images'):
            assert row['context']==c[key]['context'] and not row.get('ocr_refs')
        for arm in answers:
            payload={'messages':[{'role':'system','content':m['system']},{'role':'user','content':'\n\n'.join(str(row.get(k,'')) for k in ('context','question'))}],
                     'temperature':0,'seed':42,'chat_template_kwargs':{'enable_thinking':False},
                     'lora':[{'id':i,'scale':1.0 if arm=='trained' and ROUTES[i]==route else 0.0} for i in range(5)],
                     'max_tokens':1600 if row.get('points',0)>=10 else 500}
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            assert digest==answers[arm][key]['request_sha256'], f'Request mismatch: {arm}/{key}'
    bound=[source,mpath,cfgpath,handpath,training,reports_path,infer,run.parent/'runtime.txt']
    manifest={'protocol':PROTOCOL,'policy_sha256':policy_hash(),'measurement_kind':'training_set',
              'prior_grade_reuse':False,'final_score_allowed':True,'full_official_task_count':37,'full_official_max_points':60,
              'base_aggregate_bytes':m['base_aggregate_bytes'],'trained_aggregate_bytes':m['trained_aggregate_bytes'],
              'training_manifest_sha256':sha(training),'training_exposure':POLICY['training_exposure'],
              'inference_gate':{'passed':True,'matched_requests_reconstructed':74,'five_adapter_identity_zero_scale_gate':True,
                                'bound_files':[{'path':str(f),'sha256':sha(f)} for f in bound]},'runs':[]}
    for arm,data in answers.items():
        refs=[]
        for key,x in c.items():
            images=[]
            for path in x['page_images']:
                image=Path(path);image=image if image.is_absolute() else ROOT/image
                images.append({'path':str(image),'sha256':sha(image)})
            packet={'id':key,'paper_id':x['paper_id'],'max_points':x['max_points'],'category':x['subtype'],
                    'question':x['question'],'original_source_text':x.get('source_text'),'original_context':x['context'],
                    'answer_format':x['answer_format'],'candidate_answer':data[key]['answer'],
                    'official_solution':keys[key].get('official_solution'),'official_rubric':keys[key].get('rubric'),
                    'original_images':images,'official_rubric_pdf':str(paper/'rubric.pdf'),'official_rubric_pdf_sha256':sha(paper/'rubric.pdf'),
                    'candidate_file_sha256':sha(paper/'candidate.jsonl'),'judge_file_sha256':sha(paper/'judge.jsonl')}
            if not packet['official_solution'] and not packet['official_rubric']:
                packet['official_rubric_text_fallback']=json.loads((paper/'rubric_pages.json').read_text())
            dest=out/arm/f'{key}.json';freeze(dest,packet)
            refs.append({'id':key,'packet_path':str(dest),'packet_sha256':sha(dest)})
        manifest['runs'].append({'label':arm,'answers_file':str(run/arm/'answers.jsonl'),
                                'answers_file_sha256':sha(run/arm/'answers.jsonl'),'packets':refs})
    freeze(out/'manifest.json',manifest)
    print(json.dumps({'gate':'PASS','packets':str(out),'fresh_judgments':True,'tasks_per_arm':37,'calls_launched':0}))
if __name__=='__main__':main()
