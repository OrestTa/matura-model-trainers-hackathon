"""Bounded, resumable generation of ORIGINAL Polish history exams using Forgehand.
Official 2015/16 never reach teacher; local overlap filter only. No secret logging.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, html, json, os, random, re, threading, time, textwrap
from pathlib import Path
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
TEAM='01a0d9f4-5e58-7440-875a-81dfcbccbabf'
BASE=f'https://app.forgehand.app/api/v1/teams/{TEAM}/llm'
CATS=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']
def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)); tmp.replace(path)
def shingles(text):
    words=re.findall(r'\w+',text.lower()); return {hashlib.sha256(' '.join(words[i:i+7]).encode()).hexdigest()[:16] for i in range(len(words)-6)}
def category(row):
    text=(row.get('question','')+' '+row.get('context','')).lower()
    if row.get('max_points',0)>=12 or 'wypracowanie' in text: return 'essay'
    image=bool(re.search(r'ilustrac|fotograf|mapa\b|mapie|wykres|rysun|karykatur|schemat|reprodukc',text))
    closed=bool(re.search(r'prawdziw|prawda|fałsz|wybierz|zaznacz|przyporząd|kolejność|chronologiczn|uzupełnij tabel',text)) and not re.search(r'uzasadnij|wyjaśnij',row.get('question','').lower())
    return ('closed' if closed else 'open')+('_with_images' if image else '_without_images')
def plan_for(index,corpus):
    # Current-format point allocation copied as structure ONLY; historical questions vary.
    candidates=rows(sorted(corpus.glob('202[3-6]-*/candidate.jsonl'))[index%4])
    return [{'id':str(i+1),'category':category(r),'max_points':r['max_points']} for i,r in enumerate(candidates)]
def sample_sources(index,corpus):
    paths=sorted(p for p in corpus.glob('*/candidate.jsonl') if 2017<=int(p.parent.name[:4])<=2026)
    path=paths[index%len(paths)]; rr=rows(path); keys={r['id']:r for r in rows(path.with_name('judge.jsonl'))}
    rng=random.Random(index+129); sample=rng.sample([r for r in rr if r['max_points']<12],min(5,len(rr)))
    return path.parent.name,[{'question':r['question'],'context':r.get('context','')[:900],'answer':keys[r['id']].get('official_solution','')[:600]} for r in sample]
def parse_teacher_json(text):
    """Remove only syntactic trailing commas outside JSON string literals."""
    try: return json.loads(text)
    except json.JSONDecodeError:
        out=[]; inside=False; escaped=False
        for i,char in enumerate(text):
            if inside:
                out.append(char)
                if escaped: escaped=False
                elif char=='\\': escaped=True
                elif char=='"': inside=False
            else:
                if char=='"': inside=True
                if char==',' and text[i+1:].lstrip().startswith(('}',']')): continue
                out.append(char)
        return json.loads(''.join(out))

class Teacher:
    def __init__(self,args):
        self.args=args; self.lock=threading.Lock(); self.calls=0; self.stop=False
        self.token=os.environ.get('FORGEHAND_TOKEN')
        if not self.token:
            self.token=re.search(r'fh_[A-Za-z0-9_-]+',Path(args.credentials).read_text()).group()
        self.initial=self.usage();
        baseline=args.output/'initial_usage.json'
        if baseline.exists(): self.initial=json.loads(baseline.read_text())
        else: dump(baseline,self.initial)
    def request(self,path,payload=None):
        data=json.dumps(payload).encode() if payload is not None else None
        req=Request(BASE+path,data=data,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        with urlopen(req,timeout=190) as response: return json.load(response)
    def usage(self): return self.request('/usage')
    def call(self,prompt,model,limit):
        with self.lock:
            if self.stop: raise RuntimeError('Budget or ambiguous API error stop')
            # Explicit outstanding reservation envelope; settled spend is checked between batches.
            self.calls+=1
        result=self.request('/v1/responses',{'model':model,'input':prompt,'max_output_tokens':limit,'reasoning':{'effort':'none'},'store':False})
        text=''.join(c.get('text','') for x in result.get('output',[]) for c in x.get('content',[]) if c.get('type')=='output_text')
        if result.get('status')=='incomplete': raise ValueError('truncated_teacher_output')
        match=re.search(r'\{.*\}',text,re.S)
        if not match: raise ValueError('teacher_json_missing')
        return parse_teacher_json(match.group()),result.get('usage',{})
def validate(exam,plan,reference_sets,accepted_sets):
    tasks=exam.get('tasks',[])
    if len(tasks)!=len(plan): raise ValueError('task_count')
    if sum(t.get('max_points',0) for t in tasks)!=60: raise ValueError('denominator_not60')
    for task,expected in zip(tasks,plan):
        for field in ('id','category','max_points'):
            if task.get(field)!=expected[field]: raise ValueError('plan_mismatch_'+field)
        for field in ('question','answer','rubric','context'):
            if not isinstance(task.get(field),str) or (field!='context' and not task[field].strip()): raise ValueError('missing_'+field)
        if task['category']=='essay' and len(task['answer'].split())<300: raise ValueError('short_essay')
        image='_with_images' in task['category']
        if image:
            diagram=task.get('diagram',{})
            if not isinstance(diagram,dict) or not diagram.get('title') or not 2<=len(diagram.get('rows',[]))<=12: raise ValueError('missing_original_diagram')
            if any(not isinstance(r,list) or len(r)!=2 or not all(isinstance(x,str) for x in r) for r in diagram['rows']): raise ValueError('bad_diagram_rows')
        elif task.get('diagram'): raise ValueError('unexpected_image')
        ss=shingles(task['question']+' '+task['context'])
        if len(ss)>=12:
            for old in reference_sets+accepted_sets:
                if old and len(ss&old)/min(len(ss),len(old))>=0.65: raise ValueError('near_copy')
        task['content_sha256']=hashlib.sha256((task['question']+task['context']).encode()).hexdigest()
def svg_diagram(diagram,path):
    # Preserve the complete teacher-authored content; wrap instead of clipping labels.
    rr=[(textwrap.wrap(a,58) or [''],textwrap.wrap(b,58) or ['']) for a,b in diagram['rows']]
    heights=[max(len(a),len(b))*23+24 for a,b in rr]; height=95+sum(heights)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}"><rect width="1200" height="{height}" fill="white"/>',f'<text x="30" y="35" font-family="sans-serif" font-size="20">{html.escape(diagram["title"])}</text>']
    y=65
    for (aa,bb),row_height in zip(rr,heights):
        out.append(f'<rect x="25" y="{y}" width="1150" height="{row_height}" fill="#eef3f7" stroke="#334155"/>')
        for x,lines in [(40,aa),(620,bb)]:
            for n,line in enumerate(lines): out.append(f'<text x="{x}" y="{y+25+n*23}" font-family="sans-serif" font-size="16">{html.escape(line)}</text>')
        y+=row_height
    out.append('</svg>'); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(''.join(out))

def publish(exam,directory):
    candidates=[]; judge=[]; training=[]
    for task in exam['tasks']:
        image='_with_images' in task['category']; assets=[]; transcription=''
        if image:
            asset=directory/'assets'/f'{task["id"]}.svg'; svg_diagram(task['diagram'],asset); assets=[str(asset.relative_to(ROOT))]
            transcription='\nAutorski schemat/tabela — transkrypcja:\n'+task['diagram']['title']+'\n'+'\n'.join(' | '.join(x) for x in task['diagram']['rows'])
        identity=f'{exam["paper_id"]}-z{task["id"]}'
        candidates.append({'id':identity,'paper_id':exam['paper_id'],'task_id':task['id'],'max_points':task['max_points'],'category':task['category'],'question':task['question'],'context':task['context'],'page_images':assets,'image_transcription':transcription,'split':'synthetic_train'})
        judge.append({'id':identity,'official_solution':task['answer'],'rubric':task['rubric'],'max_points':task['max_points'],'key_present':True,'synthetic':True})
        training.append({'id':identity,'paper_id':exam['paper_id'],'category':task['category'],'synthetic':True,'modality':'diagram_transcription' if image else 'text','messages':[{'role':'system','content':'Rozwiązuj zadania maturalne z historii po polsku. Podaj tylko odpowiedź, zgodnie z poleceniem.'},{'role':'user','content':task['context']+transcription+'\n\n'+task['question']},{'role':'assistant','content':task['answer']}]})
    for name,rr in [('candidate',candidates),('judge',judge),('sft',training)]:
        (directory/f'{name}.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rr))
    dump(directory/'exam.json',exam)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=ROOT/'data/small_track_synthetic'); ap.add_argument('--corpus',type=Path,default=ROOT/'data/small_track'); ap.add_argument('--credentials',default=str(ROOT/'COMPUTE_PLATFORMS_SECRETS 2.md')); ap.add_argument('--count',type=int,default=100); ap.add_argument('--workers',type=int,default=4); ap.add_argument('--budget-usd',type=float,default=35); ap.add_argument('--reserve-usd',type=float,default=10); ap.add_argument('--model',default='gpt-6-sol'); ap.add_argument('--review-model',default='gpt-6-sol'); ap.add_argument('--start',type=int,default=0); args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True); teacher=Teacher(args)
    reference_sets=[shingles(r.get('question','')+' '+r.get('context','')) for path in args.corpus.glob('*/candidate.jsonl') for r in rows(path)]
    accepted_sets=[]
    for path in args.output.glob('exam-*/exam.json'):
        accepted_sets.extend(shingles(t['question']+' '+t['context']) for t in json.loads(path.read_text())['tasks'])
    # Balance interpretation is provider-specific: persist ledger and require explicit known monetary field.
    def available(usage):
        balance=usage.get('credits',usage)
        for key in ('availableMicroUsd','availableMicrousd','available_micro_usd','availableCreditsMicroUsd','available'):
            if key in balance: return float(balance[key])/1e6
        raise RuntimeError('Unknown credits schema; inspect sanitized initial_usage.json before spending')
    initial_available=available(teacher.initial)
    def work(index):
        paper_id=f'exam-{index:03d}'; directory=args.output/paper_id
        if (directory/'exam.json').exists(): return {'paper_id':paper_id,'status':'existing'}
        directory.mkdir(exist_ok=True); plan=plan_for(index,args.corpus); source_id,examples=sample_sources(index,args.corpus)
        prompt='''Napisz NOWY kompletny autorski arkusz maturalny HISTORIA rozszerzona po polsku, 60 punktów, wypracowanie15punktów. Każde zadanie ma dokładnie kategorię i punkty PLAN. Nie kopiuj/parafrazuj przykładów, zmień fakty, epokę, źródło i rozumowanie. Zróżnicuj całą historię od starożytności do1989, Polska iświat. Źródła są jawnie autorskimi opracowaniami, nigdy zmyślonymi cytatami. Każde zadanie samowystarczalne. Zamknięte: prawda/fałsz, wybór, dopasowanie,chronologia; otwarte: uzasadnienie,wnioskowanie,identyfikacja. Nie nazywaj tabeli fotografią/mapą. Preferuj schematy jakościowe: nazwy, fakty, instytucje, daty. Nie wymyślaj statystyk prawdziwych państw lub wydarzeń (powierzchni,populacji,procentów,produkcji). Wszystkie with_images: oryginalny schemat/tabela danych w diagram {title,rows:[[etykieta,wartość],...]},2–12wierszy, każdy element max65znaków. Bez diagramów w innych kategoriach. Pytanie korzysta ze schematu;nie zdradzaj odpowiedzi w tytule. Dla każdego: question,context,answer (wzorcowe pełne rozwiązanie),rubric (jasne kryteria każdego punktu z dopuszczalnymi odpowiedziami i0pkt). Wypracowanie300–450słów,teza,fakty,analiza,wniosek, 15pkt rubryka. JSON {tasks:[{id,category,max_points,question,context,answer,rubric,diagram?}]}. Bez markdown. PLAN:\n'''+json.dumps(plan,ensure_ascii=False)+'\nPrzykłady stylu (NIEKOPIUJ):'+json.dumps(examples,ensure_ascii=False)+f'\nWariant {index+71831}. Unikatowe zainteresowania tego arkusza: '+['gospodarka i handel,życie miast,transport','religia,prawo,ideologie polityczne','kultura,edukacja,nauka i technika','wojsko,dyplomacja,konflikty graniczne','wieś,przemiany społeczne,prawa obywatelskie'][index%5]+'. Zachowaj przekrój epok. Dobieraj inne przykłady niż chrzest966,Grunwald1410,Konstytucja1791; unikaj zawsze tych samych najbardziej oczywistych faktów.'
        try:
            if (directory/'repaired.json').exists(): exam=json.loads((directory/'repaired.json').read_text())
            elif (directory/'raw.json').exists(): exam=json.loads((directory/'raw.json').read_text())
            else:
                exam,usage=teacher.call(prompt,args.model,24576); dump(directory/'raw.json',exam); dump(directory/'usage.json',usage)
            for task in exam.get('tasks',[]):
                if task.get('category')=='essay' and len(task.get('answer','').split())<300:
                    repair, repair_usage=teacher.call('Rozwiń poprawną historycznie odpowiedź na poniższy temat do 380–450 SŁÓW. Minimum300słów to wymóg formalny. Zachowaj tezę, argumenty, fakty, wniosek. Zwróć JSON {"answer":"pełne wypracowanie"}. Temat i poprzednia odpowiedź: '+json.dumps(task,ensure_ascii=False),args.model,4096)
                    task['answer']=repair['answer']; dump(directory/'essay_repair_usage.json',repair_usage)
            validate(exam,plan,reference_sets,accepted_sets)
            review_prompt='Oceniaj wyłącznie konkretne ISTOTNE błędy, nie możliwości stylistycznego dopracowania. Dopuszczaj poprawne skróty historyczne, standardowe wnioskowanie i rozsądne własne zasady częściowych punktów. Nie żądaj informacji ponad treść pytania. Nie odrzucaj za przekroczenie450słów (matura ma minimum300, nie maksimum). Zgłaszaj wszystkie istotne błędy naraz, maksymalnie8, zwięźle. Sprawdź jako niezależny nauczyciel historii ten AUTORSKI arkusz. Szukaj błędów historycznych, niejednoznacznych pytań, złych kluczy, źródeł niepozwalających rozwiązać zadania, niezgodnych rubryk punktowych. Schematy to autorskie tabele, nie reprodukcje. Czy modelowa odpowiedź zasługuje na pełne punkty? Zwróć JSON {"approved":true/false,"errors":[{"id":"...","reason":"..."}]}. Akceptuj tylko gdy brak istotnych błędów.\n'+json.dumps(exam,ensure_ascii=False)
            review,review_usage=teacher.call(review_prompt,args.review_model,4096); dump(directory/'review.json',review); dump(directory/'review_usage.json',review_usage)
            if review.get('approved') is not True or review.get('errors'):
                bad_ids={str(e.get('id')) for e in review.get('errors',[])}
                bad_tasks=[t for t in exam['tasks'] if t['id'] in bad_ids]
                if not bad_tasks: raise ValueError('teacher_review_rejected')
                repaired, repair_usage=teacher.call('Popraw poniższe zadania zgodnie z recenzją niezależnego historyka. Zachowaj id, category,max_points. Zwróć JSON {"tasks":[pełne poprawione zadania]}. Recenzja:'+json.dumps(review,ensure_ascii=False)+' Zadania:'+json.dumps(bad_tasks,ensure_ascii=False),args.model,8192)
                replacements={t['id']:t for t in repaired['tasks']}
                exam['tasks']=[replacements.get(t['id'],t) for t in exam['tasks']]; dump(directory/'repair_usage.json',repair_usage); dump(directory/'repaired.json',exam)
                review,review_usage=teacher.call(review_prompt.split('\n')[0]+'\n'+json.dumps(exam,ensure_ascii=False),args.review_model,4096); dump(directory/'review_after_repair.json',review); dump(directory/'rereview_usage.json',review_usage)
                if review.get('approved') is not True or review.get('errors'): raise ValueError('teacher_review_rejected_after_repair')
            exam.update(paper_id=paper_id,source_paper=source_id,split='synthetic_train',teacher=args.model,reviewer=args.review_model,synthetic=True,quality_label='synthetic_QA_not_official_CKE_grade')
            with teacher.lock:
                validate(exam,plan,reference_sets,accepted_sets); publish(exam,directory); accepted_sets.extend(shingles(t['question']+' '+t['context']) for t in exam['tasks'])
            return {'paper_id':paper_id,'status':'accepted','tasks':len(plan)}
        except Exception as error:
            # HTTP/transport failures can hold credits. Do not retry or expose payload/token.
            if not isinstance(error,ValueError): teacher.stop=True
            result={'paper_id':paper_id,'status':'quarantined','error_type':type(error).__name__,'reason':str(error)[:120] if isinstance(error,ValueError) else 'API_or_transport_error_no_retry','transport_cause_type':type(getattr(error,'reason',None)).__name__}; dump(directory/'failure.json',result); return result
    index=args.start
    def publish_progress(spent,inflight):
        all_rows=[]
        for path in sorted(args.output.glob('exam-*/sft.jsonl')):
            if path.with_name('exam.json').exists(): all_rows.extend(rows(path))
        combined_tmp=args.output/'sft.jsonl.tmp'
        combined_tmp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in all_rows)); combined_tmp.replace(args.output/'sft.jsonl')
        dump(args.output/'progress.json',{'accepted_exams':len(list(args.output.glob('exam-*/exam.json'))),'sft_rows':len(all_rows),'attempts':index,'shared_credit_delta_usd':spent,'teacher_calls_this_process':teacher.calls,'budget_usd':args.budget_usd,'remaining_credit_reserve_usd':args.reserve_usd,'inflight_exams':inflight,'workers':args.workers,'spend_scope':'all team credit change since initial run; includes judging'})
    futures=set(); budget_stopped=False
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        while True:
            usage=teacher.usage(); dump(args.output/'latest_usage.json',usage)
            spent=max(0,initial_available-available(usage)); accepted=len(list(args.output.glob('exam-*/exam.json')))
            # Bound the complete outstanding exam lifecycle, including repairs.
            affordable=min(args.workers,int((args.budget_usd-spent)/0.65),int((available(usage)-args.reserve_usd)/0.65))
            while not teacher.stop and len(futures)<affordable and accepted+len(futures)<args.count and index<args.count*3+args.start:
                if (args.output/f'exam-{index:03d}'/'exam.json').exists(): index+=1; continue
                futures.add(executor.submit(work,index)); index+=1
            if not futures:
                publish_progress(spent,0)
                if accepted<args.count: print(json.dumps({'status':'stopped','spent_usd':spent,'accepted':accepted,'transport_stop':teacher.stop}),flush=True)
                break
            complete,futures=concurrent.futures.wait(futures,timeout=15,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in complete: print(json.dumps(future.result()),flush=True)
            if complete: publish_progress(spent,len(futures))
if __name__=='__main__': main()
