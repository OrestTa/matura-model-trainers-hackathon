import hashlib,json,sys
from pathlib import Path
from transformers import AutoTokenizer
root=Path(sys.argv[1]);base=Path('/workspace/codex-small-track-clean-v3/model');m=root/'data/manifest.json';assert hashlib.sha256(m.read_bytes()).hexdigest()=='ef4bd556304c7a856622ca06dfa5cc3a410c5ac859452ef93a0e405774136c07';manifest=json.loads(m.read_text());assert manifest['training_scope']=='all_available_official_papers_no_holdouts' and manifest['synthetic'] is False
tokenizer=AutoTokenizer.from_pretrained(base,local_files_only=True);report={};bad=[]
for route in ['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']:
 p=root/'data'/route/'train.jsonl';assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files'][route]['sha256'];rows=list(map(json.loads,p.read_text().splitlines()));lengths=[]
 for r in rows:
  assert r['synthetic'] is False and isinstance(r['year'],int);msg=r['messages'];assert msg[-1]['role']=='assistant' and isinstance(msg[-1]['content'],str)
  prompt=tokenizer.apply_chat_template(msg[:-1],tokenize=False,add_generation_prompt=True);length=len(tokenizer(prompt,add_special_tokens=False)['input_ids'])+len(tokenizer(msg[-1]['content']+'<|im_end|>',add_special_tokens=False)['input_ids']);lengths.append(length)
  if length>3072:bad.append({'id':r['id'],'tokens':length})
 report[route]={'rows':len(rows),'max_tokens':max(lengths)}
(root/'preflight.json').write_text(json.dumps({'routes':report,'overlength':bad},indent=2));print(json.dumps({'preflight':report,'overlength':bad}),flush=True);assert not bad,'Repair overlength inputs; do not silently exclude real targets'
