import concurrent.futures as cf,hashlib,json,pathlib,time,urllib.request
ROOT=pathlib.Path('/opt/codex-small-track');SYSTEM='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
def worker(size,port):
 for attempt in range(120):
  try:
   with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=2) as response:
    if response.status==200:break
  except Exception:time.sleep(2)
 else:raise RuntimeError("server not healthy")
 for source in sorted((ROOT/'additional').glob('*.jsonl')):
  rows=[json.loads(x) for x in source.read_text().splitlines()];out=ROOT/f'bielik{size}-{source.stem}-concise-routes';out.mkdir(exist_ok=True)
  manifest=json.loads((ROOT/f'bielik{size}-2024-baseline/manifest.json').read_text());manifest.update(worker_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(), routes=['closed_with_images','essay'] if size=='4.5' else ['closed_without_images','essay'], input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),variant=f'concise_routes_text_{source.stem}_development');(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
  def answer(row):
   assert not {'answer','answers','rubric','official_solution','gold','solution'}.intersection(row)
   prompt='\n\n'.join(str(row[k]) for k in ('context','question') if row.get(k))
   hints={'closed_with_images':'Sprawdź zgodność każdej opcji z podanymi źródłami. Podaj tylko jednoznaczny wybór dla każdego podpunktu w żądanym formacie.','closed_without_images':'Zwróć dokładnie wymagane oznaczenia w kolejności podpunktów. Zachowaj rozróżnienie P/F, liter i numerów. Nie dopisuj alternatywnych odpowiedzi.','essay':'Wybierz dokładnie JEDEN temat i podaj jego numer. Napisz 450–550 słów ciągłego tekstu: teza, argumenty historyczne z konkretnymi faktami dla każdego wymaganego aspektu oraz wniosek. Omów wyłącznie wybrany temat. Nie przedstawiaj pozostałych tematów ani alternatywnych wypracowań.'}
   routes={'closed_with_images','essay'} if size=='4.5' else {'closed_without_images','essay'}
   if row['subtype'] in routes:prompt+='\n\n'+hints[row['subtype']]
   payload={'model':manifest['weight_file'],'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':1600 if row['points']>=10 else 500};result={'id':row['id'],'paper_id':row['paper_id'],'answer':'','error':None,'request_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()};start=time.monotonic()
   try:
    with urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=240) as response:r=json.load(response)
    result.update(answer=r['choices'][0]['message']['content'],finish_reason=r['choices'][0].get('finish_reason'),usage=r.get('usage'))
   except Exception as e:result['error']=type(e).__name__
   result['latency_s']=time.monotonic()-start;return result
  with cf.ThreadPoolExecutor(max_workers=8) as pool,(out/'answers.jsonl').open('w') as f:
   for future in cf.as_completed([pool.submit(answer,row) for row in rows]):f.write(json.dumps(future.result(),ensure_ascii=False)+'\n');f.flush()
  print(json.dumps({'model':size,'paper':source.stem,'rows':len(rows),'state':'complete'}),flush=True)
with cf.ThreadPoolExecutor(max_workers=2) as pool:
 for future in cf.as_completed([pool.submit(worker,'1.5',18101),pool.submit(worker,'4.5',18102)]):future.result()
