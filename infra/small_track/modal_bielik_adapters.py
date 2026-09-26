"""Native Bielik access/generation preflight. Training only real official data later."""
import modal,json,time,hashlib
from pathlib import Path
app=modal.App('matura-bielik-native-independent');vol=modal.Volume.from_name('matura-small-independent')
REPO='cpral/Bielik-1.5B-v3.0-Instruct-ungated';REV='a3a660b10fdba3a7b03c3349567e54d8875f9ac9';WEIGHT_SHA='3c337d1d0d3f8cafb27f617b97a9a0cf70a2067648cb3946311e2fe370c28978'
image=modal.Image.debian_slim(python_version='3.12').pip_install('torch==2.8.0','transformers>=5.3,<6','peft>=0.18','accelerate','huggingface_hub','sentencepiece','gguf','numpy').pip_install('pillow','torchvision==0.23.0')
@app.function(image=image,cpu=2,memory=4096,timeout=600,max_containers=1,retries=0,volumes={'/outputs':vol})
def preload():
 from huggingface_hub import snapshot_download
 path=snapshot_download(REPO,revision=REV,cache_dir='/outputs/hf_cache',allow_patterns=['*.json','*.safetensors','*.jinja','*.txt'])
 with (Path(path)/'model.safetensors').open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 assert sha==WEIGHT_SHA;vol.commit();return path
@app.function(image=image,gpu='L4',cpu=4,memory=16384,timeout=240,max_containers=1,retries=0,scaledown_window=2,block_network=True,volumes={'/outputs':vol})
def generation(path,run):
 import torch,os
 from transformers import AutoTokenizer,AutoModelForCausalLM
 os.environ['HF_HUB_OFFLINE']='1';vol.reload();dest=Path('/outputs')/run;dest.mkdir(exist_ok=False)
 tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True);model=AutoModelForCausalLM.from_pretrained(path,dtype=torch.bfloat16,device_map={'':'cuda'},local_files_only=True).eval();out=[]
 for prompt in ['W którym roku Polska odzyskała niepodległość? Odpowiedz krótko.','Podaj stolicę Polski. Odpowiedz jednym słowem.','Napisz jedno zdanie po polsku o konstytucji.']:
  text=tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True);x=tokenizer(text,return_tensors='pt',add_special_tokens=False).to('cuda')
  with torch.no_grad():y=model.generate(**x,max_new_tokens=80,do_sample=False)
  answer=tokenizer.decode(y[0,x.input_ids.shape[1]:],skip_special_tokens=True);out.append({'prompt':prompt,'answer':answer})
 result={'run':run,'repo':REPO,'revision':REV,'native_weight_sha256':WEIGHT_SHA,'native_weight_bytes':3193073112,'tokenizer_eos':tokenizer.eos_token,'tokenizer_eos_id':tokenizer.eos_token_id,'model_eos_id':model.config.eos_token_id,'outputs':out,'training_performed':False,'offline':True,'provenance':'public Apache-2.0 mirror; config/tokenizer/model LFS pointer Git blob IDs match official repository'}
 (dest/'preflight.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));vol.commit();return result
@app.local_entrypoint()
def main():
 path=preload.remote();run=time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-bielik15-native-preflight';r=generation.remote(path,run);dest=Path('results/small_track')/run;dest.mkdir(parents=True);(dest/'preflight.json').write_text(json.dumps(r,indent=2,ensure_ascii=False));print(json.dumps(r,ensure_ascii=False),flush=True)

@app.function(image=image,gpu='L4',cpu=4,memory=16384,timeout=600,max_containers=1,retries=0,scaledown_window=2,block_network=True,volumes={'/outputs':vol})
def real_adapters(path,payload,run,steps=16):
 import torch,os,random,subprocess
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import LoraConfig,get_peft_model
 os.environ['HF_HUB_OFFLINE']='1';vol.reload();dest=Path('/outputs')/run;dest.mkdir(exist_ok=False)
 tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True);model=AutoModelForCausalLM.from_pretrained(path,dtype=torch.bfloat16,device_map={'':'cuda'},local_files_only=True)
 tokenizer.save_pretrained(dest/'base-config');(dest/'base-config'/'config.json').write_text((Path(path)/'config.json').read_text());reports=[]
 for route,rows in payload.items():
  assert rows and all(not r.get('synthetic',False) for r in rows)
  assert all(str(r.get('year','')) not in ('2023','2024') for r in rows)
  target=dest/route;target.mkdir();(target/'training.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));random.Random(7291).shuffle(rows)
  targets=[n for n,m in model.named_modules() if n.endswith(('.mlp.gate_proj','.mlp.up_proj','.mlp.down_proj'))];assert targets
  model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,target_modules=targets,lora_dropout=0.0,task_type='CAUSAL_LM'));model.enable_input_require_grads();model.gradient_checkpointing_enable();model.train();opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=5e-5);losses=[];used=[]
  for row in rows:
   if len(losses)>=steps:break
   messages=row['messages'];assert messages[-1]['role']=='assistant' and isinstance(messages[-1]['content'],str)
   prompt=tokenizer.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True);a=tokenizer(prompt,return_tensors='pt',add_special_tokens=False)['input_ids'].to('cuda');b=tokenizer(messages[-1]['content']+'<|im_end|>',return_tensors='pt',add_special_tokens=False)['input_ids'].to('cuda');ids=torch.cat([a,b],dim=1)
   if ids.shape[1]>3072:continue
   labels=ids.clone();labels[:,:a.shape[1]]=-100;loss=model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels).loss;assert torch.isfinite(loss);loss.backward();torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1);opt.step();opt.zero_grad();losses.append(float(loss.detach()));used.append(row.get('id'));print(json.dumps({'route':route,'step':len(losses),'loss':losses[-1]}),flush=True)
  assert losses;model.save_pretrained(target/'adapter');del opt;model=model.unload();torch.cuda.empty_cache();vol.commit()
  converter='/outputs/llama-694ec235484b3b0bf827ab7992a512d285f0e66b/convert_lora_to_gguf.py'
  with (target/'convert.log').open('w') as log:r=subprocess.run(['python',converter,'--base',str(dest/'base-config'),'--outfile',str(target/'adapter-f16.gguf'),'--outtype','f16',str(target/'adapter')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
  assert r.returncode==0,'convert failed';f=target/'adapter-f16.gguf';report={'route':route,'steps':len(losses),'losses':losses,'used_ids':used,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((target/'training.jsonl').read_bytes()).hexdigest(),'repo':REPO,'revision':REV,'synthetic':False,'loss':'assistant_only','rank':8,'lr':5e-5,'target_modules':targets};(target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report);vol.commit()
 return reports

@app.local_entrypoint()
def train_real(data:str,steps:int=16):
 root=Path(data);payload={}
 for p in sorted(root.glob('*/train.jsonl')):
  rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
  if rows:payload[p.parent.name]=rows
 assert payload,'no real training rows'
 for rows in payload.values():
  for r in rows:
   assert r.get('synthetic') is False and r.get('year') is not None and str(r['year']) not in ('2023','2024'),'explicit real source and excluded eval years required'
 path=preload.remote();run=time.strftime('%Y%m%d-%H%M%S',time.gmtime())+'-bielik15-real-route-adapters';result=real_adapters.remote(path,payload,run,steps);dest=Path('results/small_track')/run;dest.mkdir(parents=True);(dest/'manifests.json').write_text(json.dumps(result,indent=2));print(json.dumps({'run':run,'routes':len(result),'bytes':sum(r['bytes'] for r in result)}),flush=True)
