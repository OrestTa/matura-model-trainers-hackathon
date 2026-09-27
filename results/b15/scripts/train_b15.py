"""Isolated bounded real-only Bielik LoRA worker. No synthetic training targets."""
import json, time, hashlib, argparse, sys
from pathlib import Path
REPO='cpral/Bielik-1.5B-v3.0-Instruct-ungated'
REV='a3a660b10fdba3a7b03c3349567e54d8875f9ac9'
GUIDE_ID='cke-supplement20230111-essay-dictatorships'
GUIDE_PDF_SHA='0ba26d9d27cafea6c367693ffc5d8c0d157a7c4774a37f9a9ad4ac2a84981aff'
GUIDE_ROW_SHA='5e0c5ca110aa03571c4ba2579da6c443fc7cd1a4b8db621ed7c96c1d21ffee38'
CLEAN_MANIFEST_SHA='da25c2a0773f34cf5a7282de500304d4d6db4cabb0824d931051fcbfed5039ab'
def row_sha(row):
 return hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def validate_real_row(row,source_manifest_sha=None):
 if row.get('synthetic') is not False:raise ValueError('Only explicitly real official targets allowed')
 if any(b in str(row.get('id',''))+str(row.get('paper_id','')) for b in ('probny-2026-01','2023-05','2024-05','2025-05','2026-05')):
  allowed=(row.get('year')==2023 and row.get('id')==GUIDE_ID and row.get('category')=='essay' and row.get('paper_id')=='cke-supplement20230111' and row.get('source_pdf_sha256')==GUIDE_PDF_SHA and row_sha(row)==GUIDE_ROW_SHA and source_manifest_sha==CLEAN_MANIFEST_SHA)
  if not allowed:raise ValueError('Reserved/evaluation paper excluded; guide exception requires exact source and row hashes')
 if not isinstance(row.get('year'),int):raise ValueError('Explicit integer source year required')
def memory_preflight(torch,fraction):
 if fraction is None:return None
 if not 0<fraction<=0.5:raise ValueError('GPU memory fraction must be in (0,0.25]')
 free,total=torch.cuda.mem_get_info()
 # Allocator cap excludes CUDA context/non-PyTorch allocations; retain one GiB headroom.
 required=int(total*fraction)+(1<<30)
 if free<required:raise RuntimeError(f'Insufficient free GPU memory: {free} < {required} bytes')
 torch.cuda.set_per_process_memory_fraction(fraction,device=0)
 return {'fraction':fraction,'initial_free_bytes':free,'total_bytes':total,'required_free_bytes':required,'scope':'PyTorch allocator cap; CUDA context and non-PyTorch allocations excluded'}
class LocalPersistence:
 def reload(self): pass
 def commit(self): pass
vol=LocalPersistence()
def real_adapters(path,payload,run,steps=16,source_manifest_sha=None,gpu_memory_fraction=None):
 import torch,os,random,subprocess
 from transformers import AutoTokenizer,AutoModelForCausalLM
 from peft import LoraConfig,get_peft_model
 os.environ['HF_HUB_OFFLINE']='1';vol.reload();dest=Path(output_root)/run;dest.mkdir(exist_ok=False)
 tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True)
 tokenizer.save_pretrained(dest/'base-config');(dest/'base-config'/'config.json').write_text((Path(path)/'config.json').read_text());reports=[]
 for route,rows in payload.items():
  assert rows
  for row in rows:validate_real_row(row,source_manifest_sha)
  memory_gate=memory_preflight(torch,gpu_memory_fraction)
  torch.manual_seed(7291);torch.cuda.manual_seed_all(7291)
  model=AutoModelForCausalLM.from_pretrained(path,dtype=torch.bfloat16,device_map={'':'cuda'},local_files_only=True)
  target=dest/route;target.mkdir();(target/'training.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));random.Random(7291).shuffle(rows)
  targets=[n for n,m in model.named_modules() if n.endswith(('.mlp.gate_proj','.mlp.up_proj','.mlp.down_proj'))];assert targets
  model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,target_modules=targets,lora_dropout=0.0,task_type='CAUSAL_LM'));model.enable_input_require_grads();model.gradient_checkpointing_enable();model.train();opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=5e-5);losses=[];used=[];excluded=[]
  for row in rows:
   if steps>0 and len(losses)>=steps:break
   messages=row['messages'];assert messages[-1]['role']=='assistant' and isinstance(messages[-1]['content'],str)
   prompt=tokenizer.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True);a=tokenizer(prompt,return_tensors='pt',add_special_tokens=False)['input_ids'].to('cuda');b=tokenizer(messages[-1]['content']+'<|im_end|>',return_tensors='pt',add_special_tokens=False)['input_ids'].to('cuda');ids=torch.cat([a,b],dim=1)
   if ids.shape[1]>3072:
    excluded.append({'id':row.get('id'),'tokens':int(ids.shape[1]),'reason':'exceeds3072_no_truncation'});print(json.dumps({'route':route,'excluded':excluded[-1]}),flush=True);continue
   labels=ids.clone();labels[:,:a.shape[1]]=-100;loss=model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels).loss;assert torch.isfinite(loss);loss.backward();torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1);opt.step();opt.zero_grad();losses.append(float(loss.detach()));used.append(row.get('id'));print(json.dumps({'route':route,'step':len(losses),'loss':losses[-1]}),flush=True)
  assert losses;model.save_pretrained(target/'adapter');del opt;del model;torch.cuda.empty_cache();vol.commit()
  converter=converter_path
  with (target/'convert.log').open('w') as log:r=subprocess.run([sys.executable,converter,'--base',str(dest/'base-config'),'--outfile',str(target/'adapter-f16.gguf'),'--outtype','f16',str(target/'adapter')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
  assert r.returncode==0,'convert failed';f=target/'adapter-f16.gguf';report={'route':route,'steps':len(losses),'losses':losses,'used_ids':used,'excluded_length':excluded,'source_rows':len(rows),'seed':7291,'fresh_native_base_per_route':True,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((target/'training.jsonl').read_bytes()).hexdigest(),'repo':REPO,'revision':REV,'synthetic':False,'loss':'assistant_only','rank':8,'lr':5e-5,'target_modules':targets,'dataset_manifest_sha256':source_manifest_sha,'gpu_memory_gate':memory_gate};(target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report);vol.commit()
 return reports

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--data',required=True);p.add_argument('--output-root',required=True);p.add_argument('--converter',required=True);p.add_argument('--run',required=True);p.add_argument('--steps',type=int,default=16);p.add_argument('--routes',default='closed_with_images,open_with_images,essay');p.add_argument('--gpu-memory-fraction',type=float,default=None);p.add_argument('--expected-data-manifest-sha256');args=p.parse_args()
 output_root=args.output_root;converter_path=args.converter;Path(output_root).mkdir(parents=True,exist_ok=True)
 if args.gpu_memory_fraction is not None and not 0<args.gpu_memory_fraction<=0.5:p.error('--gpu-memory-fraction must be in (0,0.25]')
 manifest_path=Path(args.data)/'manifest.json';manifest_sha=hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.exists() else None
 if args.expected_data_manifest_sha256 and manifest_sha!=args.expected_data_manifest_sha256:raise ValueError('Dataset manifest hash mismatch')
 manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
 payload={}
 for route in args.routes.split(','):
  route_path=Path(args.data)/route/'train.jsonl'
  if manifest_sha==CLEAN_MANIFEST_SHA and hashlib.sha256(route_path.read_bytes()).hexdigest()!=manifest['files'][route]['sha256']:raise ValueError('Frozen route file hash mismatch')
  rows=[json.loads(l) for l in route_path.read_text().splitlines() if l.strip()]
  for row in rows:validate_real_row(row,manifest_sha)
  payload[route]=rows
 reports=real_adapters(args.model,payload,args.run,args.steps,manifest_sha,args.gpu_memory_fraction)
 (Path(output_root)/args.run/'manifests.json').write_text(json.dumps(reports,indent=2))
 print(json.dumps({'completed':args.run,'routes':len(reports),'bytes':sum(r['bytes'] for r in reports)}),flush=True)
