#!/usr/bin/env python3
"""Train a tiny offline multinomial NB router from synthetic task-type labels only."""
import argparse, collections, hashlib, json, math, re
from pathlib import Path
LABELS=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']
def features(row):
    words=re.findall(r'\w+',row.get('question','').lower())
    tokens=words+['BI:'+a+'_'+b for a,b in zip(words,words[1:])]
    image=bool(row.get('images') or row.get('page_images') or row.get('diagram') or row.get('needs_image'))
    tokens += [('HAS_IMAGE' if image else 'NO_IMAGE')]*8
    tokens += ['POINTS:'+str(row.get('max_points',row.get('points',0)))]*3
    return collections.Counter(tokens)
def predict(row, model):
    f=features(row); scores={}
    for label in LABELS:
        scores[label]=model['priors'][label]+sum(count*model['weights'][label].get(word,model['unknown'][label]) for word,count in f.items())
    label=max(scores,key=scores.get)
    return {'subtype':label,'classifier':'trained-multinomial-nb-v1','router_scores':scores,'needs_image':bool(row.get('images') or row.get('page_images') or row.get('diagram') or row.get('needs_image'))}
def fit(rows):
    counts={k:collections.Counter() for k in LABELS};docs=collections.Counter();vocab=set()
    for row,label in rows:
        f=features(row);counts[label].update(f);docs[label]+=1;vocab.update(f)
    unknown={k:-math.log(sum(counts[k].values())+len(vocab)) for k in LABELS}
    return {'version':'trained-multinomial-nb-v1','priors':{k:math.log((docs[k]+1)/(len(rows)+len(LABELS))) for k in LABELS},'unknown':unknown,'weights':{k:{w:math.log(counts[k][w]+1)+unknown[k] for w in vocab} for k in LABELS},'training_features':'question unigrams/bigrams, supplied image flag, point allocation; no answers/rubrics'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='data/small_track_synthetic');p.add_argument('--output',default='artifacts/small_track/router.json');p.add_argument('--historical',action='store_true');a=p.parse_args();train=[];valid=[];sources=[]
    for i,path in enumerate(sorted(Path(a.source).glob('exam-*/exam.json'))):
        exam=json.loads(path.read_text());sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        for task in exam['tasks']:
            label=task['category'];row={k:task[k] for k in ('question','diagram','max_points') if k in task}
            if label in LABELS:(valid if i%5==0 else train).append((row,label))
    if a.historical:
        import classifier
        train=[];valid=[];sources=[]
        for path in sorted(Path('data/small_track').glob('*/candidate.jsonl')):
            rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
            eligible=[r for r in rows if r.get('year') in (2017,2018,2019,2020,2021,2022,2025,2026)]
            if not eligible:continue
            sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            for task in eligible:
                label=classifier.classify(task)['subtype'];row={k:task[k] for k in ('question','max_points','points','needs_image','images') if k in task}
                (valid if task['year']==2026 else train).append((row,label))
    model=fit(train);model['provenance']={'source_papers':sources,'official_papers_used':[],'exclusions':['no official task rows directly; synthetic source overlap2017-2026 exists'],'train_rows':len(train),'validation_rows':len(valid),'split':'every fifth synthetic paper held out'}
    confusion={k:collections.Counter() for k in LABELS}
    for row,label in valid:confusion[label][predict(row,model)['subtype']]+=1
    model['validation']={'accuracy':sum(confusion[k][k] for k in LABELS)/len(valid),'confusion':confusion}
    if a.historical:
        model['provenance'].update(official_papers_used=[2017,2018,2019,2020,2021,2022,2025],exclusions=[2023,2024],split='2026 candidate weak-label validation',label_source='rules-v1 weak labels, not human annotations')
        model['validation']['metric']='agreement with weak rule labels; not official classification accuracy'
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(model,ensure_ascii=False));print(json.dumps({'model':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'validation':model['validation']}))
if __name__=='__main__':main()
