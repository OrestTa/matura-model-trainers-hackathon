"""Essay-only experiments for Bielik 1.5B Q8_0 (no adapters), item 27 of the January 2026 mock.
E1 (essay-dry): one call with anti-repetition sampling. E2 (essay-parts): intro, four argument paragraphs, conclusion.
Writes <out>/essay-dry/answers.json and <out>/essay-parts/answers.json = the bare arm's answers with item 27 replaced."""
import json,re,sys,urllib.request
from pathlib import Path
pkg,bare,out,port=Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4]
SYSTEM="Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia."
SAMP=dict(temperature=0.3,repeat_penalty=1.15,dry_multiplier=0.8,dry_base=1.75,dry_allowed_length=2,seed=42)
e=json.loads((pkg/'exam.json').read_text());x=[i for i in e['items'] if i['max_points']>=10][0]
task='\n\n'.join(s for s in (x.get('source_text',''),x['question']) if s)
def ask(user,max_tokens):
    b={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':user}],'max_tokens':max_tokens,'chat_template_kwargs':{'enable_thinking':False},**SAMP}
    r=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',json.dumps(b).encode(),{'Content-Type':'application/json'})
    return (json.loads(urllib.request.urlopen(r,timeout=900).read())['choices'][0]['message']['content'] or '').strip()
def stats(t):
    s=[y.strip() for y in re.split(r'[.!?]',t) if y.strip()];return len(t.split()),len(s),len(set(s))
dry=ask(task+'\n\nNapisz wypracowanie o długości około 550 słów: wstęp z tezą, rozwinięcie z konkretnymi faktami, zakończenie. Nie powtarzaj zdań.',2400)
parts=[ask(task+'\n\nNapisz tylko wstęp wypracowania: wybierz jeden temat, podaj jego numer i sformułuj tezę (3-4 zdania).',400)]
for asp in ('polityka wewnętrzna','polityka zagraniczna i wojny','gospodarka i społeczeństwo','kultura i religia'):
    parts.append(ask(task+'\n\nDotychczas napisane części wypracowania:\n'+'\n\n'.join(parts)+f'\n\nNapisz kolejny akapit argumentacyjny o aspekcie: {asp}. Tylko nowe fakty, nie powtarzaj wcześniejszych zdań. Jeden akapit, 90-120 słów.',400))
parts.append(ask(task+'\n\nDotychczas napisane części wypracowania:\n'+'\n\n'.join(parts)+'\n\nNapisz tylko zakończenie wypracowania (3-4 zdania), które potwierdza tezę. Nie powtarzaj wcześniejszych zdań.',300))
res={'essay-dry':dry,'essay-parts':'\n\n'.join(parts)}
a0=json.loads(bare.read_text())
for k,t in res.items():
    a=json.loads(json.dumps(a0))
    for r in a['answers']:
        if r['id']==x['id']:r['answer']=t
    (out/k).mkdir(parents=True,exist_ok=True);(out/k/'answers.json').write_text(json.dumps(a,ensure_ascii=False,indent=1))
    w,n,u=stats(t);print(f'{k}: words {w}, sentences {n}, unique {u}')
