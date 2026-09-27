"""Essay length guard: re-run only the essay item (2400 tokens), continue up to 3 rounds until >=350 words; splice into answers-guard.json."""
import json,sys,urllib.request,importlib.util
from pathlib import Path
pkg=Path(sys.argv[1]);arm=sys.argv[2];d=Path(sys.argv[3]);port=sys.argv[4]
spec=importlib.util.spec_from_file_location('ev','/scratch/b15eval.py')
SYSTEM="Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia."
CONT="Kontynuuj wypracowanie od miejsca, w którym skończyłeś. Rozwiń argumenty i dodaj zakończenie. Nie powtarzaj wcześniejszych zdań."
e=json.loads((pkg/'exam.json').read_text());x=[i for i in e['items'] if i['max_points']>=10][0]
n=5 if arm=='allpapers' else 10;on={'base':-1,'ours':4,'cleanv3':9,'allpapers':4}[arm]
lora=[{'id':i,'scale':1.0 if i==on else 0.0} for i in range(n)]
text='\n\n'.join(s for s in (x.get('source_text',''),x['question']) if s)
oc=Path('/scratch/claude-b15/ocr')
if x.get('images'):
    o='\n\n'.join((oc/(Path(i['path']).name+'.txt')).read_text() for i in x['images'] if (oc/(Path(i['path']).name+'.txt')).exists())
    if o:text='Tekst odczytany z ilustracji (OCR):\n'+o[:6000]+'\n\n'+text
def ask(msgs,temp):
    b={'messages':msgs,'temperature':temp,'seed':42,'max_tokens':2400,'chat_template_kwargs':{'enable_thinking':False},'lora':lora}
    r=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',json.dumps(b).encode(),{'Content-Type':'application/json'})
    return (json.loads(urllib.request.urlopen(r,timeout=900).read())['choices'][0]['message']['content'] or '').strip()
msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':text}]
essay=ask(msgs,0);log=[len(essay.split())]
for k in range(3):
    if len(essay.split())>=350:break
    more=ask(msgs+[{'role':'assistant','content':essay},{'role':'user','content':CONT}],0 if k==0 else 0.3)
    essay=essay+'\n\n'+more;log.append(len(essay.split()))
a=json.loads((d/'answers.json').read_text())
for r in a['answers']:
    if r['id']==x['id']:r['answer']=essay
(d/'answers-guard.json').write_text(json.dumps(a,ensure_ascii=False,indent=1))
print(f'{arm} guard: essay words by round {log}')
