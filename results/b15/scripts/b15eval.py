"""Score Bielik 1.5B arms on an exam package, prompt format as Codex's infer.py (system prompt, temp 0, 500/1600 tokens), OCR for pictures."""
import json,re,sys,time,subprocess,urllib.request,concurrent.futures as cf
from pathlib import Path
pkg=Path(sys.argv[1]);arm=sys.argv[2];out=Path(sys.argv[3]);port=sys.argv[4] if len(sys.argv)>4 else '8091'
SYSTEM="Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia."
ROUTES=['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']
BASE={'ours':0,'cleanv3':5,'allpapers':0}
CLOSED=re.compile(r'(Zaznacz|Podkreśl|Wybierz|Przyporządkuj|Uporządkuj|Zakreśl|prawdziw|fałszyw|P\s*[–-]\s*jeśli)',re.I)
e=json.loads((pkg/'exam.json').read_text());items=e['items']
OC=Path('/scratch/claude-b15/ocr');OC.mkdir(parents=True,exist_ok=True)
def ocr(p):
    c=OC/(Path(p).name+'.txt')
    if c.exists():return c.read_text()
    try:s=subprocess.run(['tesseract',str(pkg/p),'-','-l','pol'],capture_output=True,text=True,timeout=120,env={**__import__('os').environ,'OMP_THREAD_LIMIT':'1'}).stdout.strip()
    except Exception as x:return ''
    c.write_text(s);return s
def route(x):
    if x['max_points']>=10:return 'essay'
    c='closed' if CLOSED.search(x['question']) else 'open'
    return c+('_with_images' if x.get('images') else '_without_images')
def one(x):
    r=route(x);text='\n\n'.join(s for s in (x.get('source_text',''),x['question']) if s)
    if x.get('images') and arm!='bare':
        o='\n\n'.join(t for t in (ocr(i['path']) for i in x['images']) if t)
        if o:text=o and ('Tekst odczytany z ilustracji (OCR):\n'+o[:6000]+'\n\n'+text)
    on=-1 if arm in ('base','bare','plain') else BASE[arm]+ROUTES.index(r)
    lora=[{'id':i,'scale':1.0 if i==on else 0.0} for i in range(5 if arm=='allpapers' else 10)]
    body={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':text}],'temperature':0,'seed':42,'max_tokens':1600 if r=='essay' else 500,'chat_template_kwargs':{'enable_thinking':False},**({} if arm=='plain' else {'lora':lora})}
    for k in range(3):
        try:
            req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
            a=json.loads(urllib.request.urlopen(req,timeout=900).read())['choices'][0]['message']['content'] or ''
            return x['id'],r,a.strip()
        except Exception as err:last=str(err);time.sleep(3)
    return x['id'],r,''
t=time.time()
with cf.ThreadPoolExecutor(6) as p:res=list(p.map(one,items))
out.mkdir(parents=True,exist_ok=True)
(out/'answers.json').write_text(json.dumps({'exam_id':e['exam_id'],'answers':[{'id':i,'answer':a} for i,_,a in res]},ensure_ascii=False,indent=1))
(out/'routes.json').write_text(json.dumps({i:r for i,r,_ in res},indent=1))
blank=[i for i,_,a in res if not a]
print(f'{arm}: {len(res)} answers, {len(blank)} blank {blank}, wall {time.time()-t:.0f}s')
(out/'summary.txt').write_text(f'{arm}: {len(res)} answers, {len(blank)} blank {blank}, wall {time.time()-t:.0f}s\n')
