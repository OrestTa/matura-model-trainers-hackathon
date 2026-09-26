#!/usr/bin/env python3
"""Five-route, candidate-only full-paper inference using our own model endpoints."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import infer
import classifier
from official_format import validate_exam

LABELS = {'closed_without_images', 'closed_with_images', 'open_without_images', 'open_with_images', 'essay'}


def artifact_summary(config):
    artifacts = config.get('artifacts', {})
    used = {key for route in config['routes'].values() for key in route.get('artifacts', [])}
    unique = {}
    model_totals = {}
    for key in used:
        artifact = artifacts[key]
        digest, size = artifact['sha256'], artifact['bytes']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest) or not isinstance(size, int) or size <= 0:
            raise ValueError('Artifacts need measured SHA256 and positive integer bytes')
        if digest in unique and unique[digest]['bytes'] != size:
            raise ValueError('Inconsistent bytes for identical artifact hash')
        unique[digest] = artifact
    for route in config['routes'].values():
        components = {artifacts[k]['sha256']: artifacts[k] for k in route.get('artifacts', [])}
        model_totals.setdefault(route.get('base_model', route['model']), {})
        model_totals[route.get('base_model', route['model'])].update({h:a for h,a in components.items() if a.get('role') != 'adapter'})
    for artifact in config.get('auxiliary_artifacts',[]):
        if len(artifact.get('sha256',''))!=64 or not isinstance(artifact.get('bytes'),int) or artifact['bytes']<=0:raise ValueError('Auxiliary artifact must be measured')
        unique[artifact['sha256']]=artifact
    complete = all(route.get('artifacts') for route in config['routes'].values())
    return {'measurement_complete': complete,
            'sum_unique_artifact_bytes': sum(a['bytes'] for a in unique.values()) if complete else None,
            'sum_unique_weights_and_vision_bytes': sum(a['bytes'] for a in unique.values() if a.get('role') != 'adapter') if complete else None,
            'max_individual_model_bytes': max((sum(a['bytes'] for a in m.values()) for m in model_totals.values()), default=0) if complete else None,
            'note': 'Vision components included; adapters reported in total artifacts. Unmeasured configurations cannot establish smallest-model eligibility.'}


def validate_config(config):
    if set(config['routes']) != LABELS:
        raise ValueError('Exactly the five task routes are required')
    for label, route in config['routes'].items():
        if route.get('own_model_endpoint') is not True:
            raise ValueError('Each route must explicitly target our own model endpoint')
        if not route.get('model') or not route.get('base_url', '').startswith(('http://', 'https://')):
            raise ValueError('Route requires model and base_url')
        if route.get('mode', 'grounded') not in {'bare','grounded'}:
            raise ValueError('Unsupported prompt mode')
        if 'system_prompt' in route and (not isinstance(route['system_prompt'], str) or not route['system_prompt'].strip()):
            raise ValueError('Custom route prompt must be nonempty text')
        if route.get('adapter') and not route.get('adapter_model'):
            raise ValueError('Adapter requires adapter_model server alias; silent adapter omission forbidden')
    return artifact_summary(config)


def run_row(row, config, config_hash, image_root):
    route = config['routes'][row['subtype']]
    vision = route.get('vision', False)
    args = SimpleNamespace(model=route.get('adapter_model') or route['model'],
        base_url=route['base_url'], mode=route.get('mode', 'grounded'), images=vision,
        image_root=image_root, timeout=route.get('timeout', 180),
        max_tokens=route.get('max_tokens', 768), essay_tokens=route.get('essay_tokens', 2400),
        system_prompt=route.get('system_prompt'), user_suffix=route.get('user_suffix'),
        temperature=config.get('temperature',0), seed=config.get('seed',42), offline=config.get('offline',False))
    vote_count=config.get('vote_samples',1)
    if vote_count not in (1,3):raise ValueError('vote_samples must be1or3')
    samples=[]
    for i in range(vote_count):
        args.seed=config.get('seed',42)+i
        if vote_count==3:args.temperature=0.7
        samples.append(infer.answer(row,args,config_hash))
    result=dict(samples[0])
    if vote_count==3:
        from voting import choose_vote
        vote=choose_vote([s['answer'] for s in samples]);result=dict(samples[vote['chosen_index'] if vote['chosen_index'] is not None else 0]);result.update(vote=vote,samples=samples,baseline_first_sample=samples[0]['answer'])
    result.update(task_id=row.get('task_id', row['id']), subtype=row['subtype'],
        adapter=route.get('adapter'), base_model=route.get('base_model', route['model']),
        visual_input_delivered=vision, visual_input_missing=bool(row.get('needs_image') and not vision))
    return result


def load_rows(path):
    path = Path(path)
    raw = path.read_text(encoding='utf-8')
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        document = None
    if isinstance(document, dict) and 'items' in document:
        validate_exam(document, path.parent)
        rows = []
        for item in document['items']:
            row = dict(item)
            row.update(paper_id=document['exam_id'], task_id=item['id'], points=item['max_points'],
                context='\n\n'.join([document.get('instructions', ''), item['source_text'],
                    'Wymagany format odpowiedzi (przykłady składni, nie rozwiązania): ' + item['answer_format']]),
                page_images=[str((path.parent / im['path']).resolve()) for im in item['images']])
            row.update(classifier.classify(row))
            rows.append(row)
        return rows
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    for row in rows:
        if not row.get('subtype'):
            row.update(classifier.classify(row))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--image-root', default='.')
    ap.add_argument('--concurrency', type=int, default=4)
    ap.add_argument('--router-model', help='Offline trained router JSON; omitted uses rules')
    ap.add_argument('--vote-samples', type=int, choices=[1,3])
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--ocr', action='store_true', help='Append offline OCR to an immutable derived input')
    args = ap.parse_args()
    if not 1 <= args.concurrency <= 32:
        ap.error('concurrency must be 1..32')
    config = json.loads(Path(args.config).read_text())
    if args.vote_samples is not None:config['vote_samples']=args.vote_samples
    if args.offline:config['offline']=True
    sizes = validate_config(config)
    rows = load_rows(args.input)
    if args.ocr:
        import subprocess,sys
        derived=Path(args.output).with_suffix('.ocr-input.jsonl');raw=derived.with_suffix('.original.jsonl')
        raw.parent.mkdir(parents=True,exist_ok=True);raw.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        subprocess.run([sys.executable,str(Path(__file__).with_name('ocr.py')),'--input',str(raw),'--output',str(derived),'--artifact-dir',str(derived)+'.artifacts','--image-root',args.image_root],check=True)
        rows=load_rows(derived);config['ocr_derived_input_sha256']=hashlib.sha256(derived.read_bytes()).hexdigest()
        for weight in (Path(str(derived)+'.artifacts')/'weights').glob('*'):
            if weight.is_file():config.setdefault('auxiliary_artifacts',[]).append({'sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'bytes':weight.stat().st_size,'role':'ocr'})
    if args.router_model:
        import train_router
        router_model=json.loads(Path(args.router_model).read_text())
        for row in rows:row.update(train_router.predict(row,router_model))
        config['trained_router_sha256']=hashlib.sha256(Path(args.router_model).read_bytes()).hexdigest()
        config.setdefault('auxiliary_artifacts',[]).append({'sha256':config['trained_router_sha256'],'bytes':Path(args.router_model).stat().st_size,'role':'router'})
    if len({r['id'] for r in rows}) != len(rows):
        ap.error('duplicate task IDs')
    for row in rows:
        infer.messages(row)  # Reject gold before making any network request.
        if row.get('subtype') not in LABELS:
            ap.error('Every candidate requires an explicit five-way subtype')
    sizes=validate_config(config)
    manifest = {'config':config, 'artifact_sizes':sizes,
        'router_code_sha256':hashlib.sha256(Path(__file__).with_name('train_router.py').read_bytes()).hexdigest(),
        'voting_code_sha256':hashlib.sha256(Path(__file__).with_name('voting.py').read_bytes()).hexdigest(),
        'input_sha256':hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'classifier_sha256':hashlib.sha256(Path(classifier.__file__).read_bytes()).hexdigest(),
        'infer_sha256':hashlib.sha256(Path(infer.__file__).read_bytes()).hexdigest()}
    digest = infer.sha(manifest)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    by_id = {r['id']:r for r in rows}
    if output.exists():
        for line in output.read_text().splitlines():
            old = json.loads(line)
            if old['config_sha256'] != digest or old['id'] not in by_id or old['input_sha256'] != infer.sha(by_id[old['id']]):
                ap.error('refusing to mix configurations or candidate inputs')
            done.add(old['id'])
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2))
    with output.open('a') as handle, ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        jobs = [pool.submit(run_row,r,config,digest,args.image_root) for r in rows if r['id'] not in done]
        for job in as_completed(jobs):
            result = job.result()
            handle.write(json.dumps(result, ensure_ascii=False)+'\n'); handle.flush()
            print(json.dumps({'id':result['id'],'subtype':result['subtype'],'error':result['error']}), flush=True)

if __name__ == '__main__':
    main()
