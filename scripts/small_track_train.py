"""Bounded GPU LoRA SFT, answer-only labels, synthetic exam-level validation.
Run on a cloud GPU. --output must be a persistent-volume path. Official evaluation
papers never participate in train/validation, and overlength answers are rejected.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random
from pathlib import Path

def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''): digest.update(block)
    return digest.hexdigest()

def prepare_example(tokenizer,row,max_length):
    messages=row['messages']
    if len(messages)<2 or messages[-1]['role']!='assistant': raise ValueError('missing assistant completion')
    kwargs=dict(tokenize=True,add_generation_prompt=True)
    try: prefix=tokenizer.apply_chat_template(messages[:-1],enable_thinking=False,**kwargs)
    except TypeError: prefix=tokenizer.apply_chat_template(messages[:-1],**kwargs)
    kwargs['add_generation_prompt']=False
    try: full=tokenizer.apply_chat_template(messages,enable_thinking=False,**kwargs)
    except TypeError: full=tokenizer.apply_chat_template(messages,**kwargs)
    if full[:len(prefix)]!=prefix: raise ValueError('chat template prompt is not exact prefix')
    if len(full)>max_length: return None
    labels=[-100]*len(prefix)+full[len(prefix):]
    if not any(x!=-100 for x in labels): raise ValueError('no assistant labels')
    return {'input_ids':full,'attention_mask':[1]*len(full),'labels':labels}

def run_pair(args):
    """Paired dense-source/merged inference; same text, template and token budgets."""
    import gc,time,torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    if not args.pair_candidates or not args.pair_merged: raise ValueError('pair-only requires candidates and merged model')
    if not torch.cuda.is_available(): raise RuntimeError('Cloud GPU required')
    rows=[json.loads(x) for x in args.pair_candidates.read_text().splitlines() if x.strip()]
    forbidden={'gold','gold_keywords','rubric','official_solution','reference','solution','answer','answers'}
    for row in rows:
        if forbidden.intersection(row): raise ValueError('Answer-key data present in candidate inference')
    if len({r['id'] for r in rows})!=len(rows): raise ValueError('Duplicate candidate ids')
    system='Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia.'
    args.output.mkdir(parents=True,exist_ok=True)
    pair={'candidate_sha256':hashlib.sha256(args.pair_candidates.read_bytes()).hexdigest(),'ids':[r['id'] for r in rows],'system':system,'input_modality':'text_only_same_source_text_images_not_passed','base_repo':args.model,'base_gguf':args.gguf_file,'merged_path':str(args.pair_merged),'max_new_tokens':args.max_new_tokens,'essay_tokens':args.essay_tokens,'do_sample':False,'batch_size':args.pair_batch_size,'source_difference':'dense GGUF imported base compared with its merged LoRA; distinct from Q4 baseline','runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for label,model_path,extra in [('base',args.model,{'gguf_file':args.gguf_file,'revision':args.revision} if args.gguf_file else {'revision':args.revision}),('adapter',str(args.pair_merged),{})]:
        if args.pair_label not in ('both',label): continue
        output=args.output/(label+'_answers.jsonl')
        config_hash=hashlib.sha256(json.dumps({**pair,'label':label},sort_keys=True).encode()).hexdigest()
        done=set()
        if output.exists():
            for line in output.read_text().splitlines():
                old=json.loads(line)
                if old['config_sha256']!=config_hash: raise ValueError('Existing paired outputs use a different configuration')
                done.add(old['id'])
        tokenizer=AutoTokenizer.from_pretrained(model_path,**extra)
        if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
        tokenizer.padding_side='left'
        model=AutoModelForCausalLM.from_pretrained(model_path,torch_dtype=torch.bfloat16,device_map={'':torch.cuda.current_device()},**extra).eval()
        manifest={**pair,'label':label,'config_sha256':config_hash,'resolved_revision':getattr(model.config,'_commit_hash',None),'parameter_count':sum(p.numel() for p in model.parameters())}
        (args.output/(label+'_manifest.json')).write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
        pending=[r for r in rows if r['id'] not in done]
        buckets={False:[],True:[]}
        for row in pending: buckets[row.get('category')=='essay' or row.get('max_points',row.get('points',0))>=12].append(row)
        with output.open('a') as file:
            for essay,bucket in buckets.items():
                for offset in range(0,len(bucket),args.pair_batch_size):
                    batch=bucket[offset:offset+args.pair_batch_size]; prompts=[]
                    for row in batch:
                        text='\n\n'.join(str(row[k]) for k in ('context','question') if row.get(k))
                        messages=[{'role':'system','content':system},{'role':'user','content':text}]
                        prompts.append(tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False))
                    encoded=tokenizer(prompts,return_tensors='pt',padding=True,add_special_tokens=False).to(model.device)
                    limit=args.essay_tokens if essay else args.max_new_tokens; start=time.monotonic()
                    with torch.inference_mode(): generated=model.generate(**encoded,max_new_tokens=limit,do_sample=False,pad_token_id=tokenizer.pad_token_id)
                    eos=model.generation_config.eos_token_id
                    eos_ids=set(eos if isinstance(eos,list) else [eos])
                    for n,row in enumerate(batch):
                        completion=generated[n,encoded['input_ids'].shape[1]:].tolist()
                        for j,token in enumerate(completion):
                            if token in eos_ids: completion=completion[:j+1]; break
                        answer=tokenizer.decode(completion,skip_special_tokens=True)
                        result={'id':row['id'],'paper_id':row.get('paper_id'),'task_id':row.get('task_id'),'answer':answer,'error':None if answer.strip() else 'empty_answer','finish_reason':'length' if len(completion)>=limit else 'stop','usage':{'prompt_tokens':int(encoded['attention_mask'][n].sum()),'completion_tokens':len(completion)},'latency_s':round(time.monotonic()-start,3),'config_sha256':config_hash,'input_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),'label':label}
                        file.write(json.dumps(result,ensure_ascii=False)+'\n'); file.flush(); print(json.dumps({'pair':label,'id':row['id'],'tokens':len(completion)}),flush=True)
        del model,tokenizer; gc.collect(); torch.cuda.empty_cache()
    print(json.dumps({'paired_inference_complete':True,'output':str(args.output),'tasks_per_configuration':len(rows)}),flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--revision',default='main'); p.add_argument('--gguf-file'); p.add_argument('--save-merged',action='store_true'); p.add_argument('--data',type=Path); p.add_argument('--pair-only',action='store_true'); p.add_argument('--pair-label',choices=['base','adapter','both'],default='both'); p.add_argument('--pair-batch-size',type=int,default=8); p.add_argument('--pair-candidates',type=Path); p.add_argument('--pair-merged',type=Path); p.add_argument('--max-new-tokens',type=int,default=500); p.add_argument('--essay-tokens',type=int,default=1600); p.add_argument('--output',required=True,type=Path); p.add_argument('--category',default='all'); p.add_argument('--include-image-transcriptions',action='store_true'); p.add_argument('--steps',type=int,default=180); p.add_argument('--max-length',type=int,default=2048); p.add_argument('--rank',type=int,default=16); p.add_argument('--lr',type=float,default=1e-4); p.add_argument('--batch-size',type=int,default=1); p.add_argument('--gradient-accumulation',type=int,default=8); p.add_argument('--four-bit',action='store_true'); p.add_argument('--resume',action='store_true'); p.add_argument('--seed',type=int,default=7291); args=p.parse_args()
    if args.pair_only: return run_pair(args)
    if args.data is None: p.error('--data is required for training')
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,BitsAndBytesConfig
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    if not torch.cuda.is_available(): raise RuntimeError('GPU training required; do not train on laptop')
    if args.steps<=0 or args.steps>5000: raise ValueError('bounded steps must be1..5000')
    data=[json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    if any(not r.get('synthetic') or not r['paper_id'].startswith('exam-') for r in data): raise ValueError('Only generated synthetic exams accepted; no official/heldout training')
    data=[r for r in data if (args.category=='all' or r['category']==args.category) and (args.include_image_transcriptions or r.get('modality')!='diagram_transcription')]
    papers=sorted({r['paper_id'] for r in data}); random.Random(args.seed).shuffle(papers)
    if len(papers)<5: raise ValueError('Need at least5 QA accepted complete exams for paper-separated validation')
    validation=set(papers[:max(1,len(papers)//10)])
    if args.gguf_file and args.four_bit: raise ValueError('GGUF import and bitsandbytes quantization cannot be combined in this harness')
    if args.save_merged and args.four_bit: raise ValueError('Merge export requires a dense training base')
    load_kwargs={'gguf_file':args.gguf_file} if args.gguf_file else {}
    tokenizer=AutoTokenizer.from_pretrained(args.model,revision=args.revision,**load_kwargs)
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    train=[]; val=[]; rejected=[]
    for row in data:
        encoded=prepare_example(tokenizer,row,args.max_length)
        if encoded is None: rejected.append(row['id']); continue
        (val if row['paper_id'] in validation else train).append(encoded)
    if not train or not val: raise ValueError('Empty train/validation after token checks')
    if len(rejected)>0.2*len(data): raise ValueError('More than20% rows exceed max-length; increase length instead of truncating answers')
    args.output.mkdir(parents=True,exist_ok=True)
    manifest={'model':args.model,'revision_requested':args.revision,'source_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest(),'train_rows':len(train),'validation_rows':len(val),'validation_papers':sorted(validation),'dropped_overlength':rejected,'loss':'assistant_only_exact_chat_template_prefix','evaluation_policy':'synthetic exam validation only; official2015/16 external evaluation','parameters':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}}
    from importlib.metadata import version
    manifest['dependency_versions']={name:version(name) for name in ['torch','transformers','peft','datasets','accelerate','gguf','safetensors']}
    manifest['training_script_sha256']=file_sha256(Path(__file__))
    (args.output/'training_manifest.json').write_text(json.dumps(manifest,indent=2))
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True) if args.four_bit else None
    model=AutoModelForCausalLM.from_pretrained(args.model,revision=args.revision,torch_dtype=torch.bfloat16,quantization_config=quant,device_map={'':torch.cuda.current_device()},**load_kwargs)
    manifest['revision_resolved']=getattr(model.config,'_commit_hash',None)
    manifest['base_artifact']={'repo':args.model,'gguf_file':args.gguf_file,'import':'GGUF dense import; distinct from quantized baseline' if args.gguf_file else 'native Transformers'}
    if args.gguf_file:
        from huggingface_hub import hf_hub_download
        source_file=Path(hf_hub_download(args.model,args.gguf_file,revision=args.revision))
        manifest['base_artifact'].update(bytes=source_file.stat().st_size,sha256=file_sha256(source_file),resolved_snapshot=source_file.parts[source_file.parts.index('snapshots')+1] if 'snapshots' in source_file.parts else None)
    if args.four_bit: model=prepare_model_for_kbit_training(model)
    model=get_peft_model(model,LoraConfig(r=args.rank,lora_alpha=2*args.rank,lora_dropout=0.05,target_modules='all-linear',task_type='CAUSAL_LM'))
    model.enable_input_require_grads()
    model.config.use_cache=False
    def collate(examples):
        width=max(len(x['input_ids']) for x in examples)
        return {key:torch.tensor([x[key]+([(-100 if key=='labels' else tokenizer.pad_token_id if key=='input_ids' else 0)]*(width-len(x[key]))) for x in examples],dtype=torch.long) for key in ('input_ids','attention_mask','labels')}
    config=TrainingArguments(output_dir=str(args.output/'checkpoints'),max_steps=args.steps,per_device_train_batch_size=args.batch_size,per_device_eval_batch_size=1,gradient_accumulation_steps=args.gradient_accumulation,learning_rate=args.lr,bf16=True,gradient_checkpointing=True,logging_steps=5,save_steps=20,save_total_limit=2,eval_strategy='steps',eval_steps=40,report_to='none',seed=args.seed,warmup_ratio=0.05,lr_scheduler_type='cosine',remove_unused_columns=False)
    trainer=Trainer(model=model,args=config,train_dataset=Dataset.from_list(train),eval_dataset=Dataset.from_list(val),data_collator=collate)
    result=trainer.train(resume_from_checkpoint=True if args.resume else None); metrics=trainer.evaluate(); trainer.save_model(str(args.output/'adapter')); tokenizer.save_pretrained(str(args.output/'adapter'))
    if args.save_merged:
        merged=model.merge_and_unload(); merged.save_pretrained(str(args.output/'merged'),safe_serialization=True); tokenizer.save_pretrained(str(args.output/'merged'))
    manifest.update(train_metrics=result.metrics,validation_metrics=metrics,serialized_adapter_bytes=sum(f.stat().st_size for f in (args.output/'adapter').rglob('*') if f.is_file()))
    manifest['adapter_safetensors_bytes']=sum(f.stat().st_size for f in (args.output/'adapter').glob('adapter_model*.safetensors'))
    manifest['adapter_weight_artifacts']=[{'file':f.name,'bytes':f.stat().st_size,'sha256':file_sha256(f)} for f in sorted((args.output/'adapter').glob('adapter_model*.safetensors'))]
    (args.output/'training_manifest.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps({'output':str(args.output),'train_rows':len(train),'validation_rows':len(val),'metrics':metrics}),flush=True)
if __name__=='__main__': main()
