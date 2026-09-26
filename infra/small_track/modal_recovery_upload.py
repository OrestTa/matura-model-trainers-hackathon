"""Authorized private HF backup of three allowlisted model files; CPU only."""
import json,time,os
from pathlib import Path
import modal
app=modal.App('matura-private-recovery-upload')
image=modal.Image.debian_slim(python_version='3.12').pip_install('huggingface_hub')
text_volume=modal.Volume.from_name('matura-qwen-independent')
vision_volume=modal.Volume.from_name('matura-small-independent')
secret=modal.Secret.from_dict({'HF_TOKEN':Path('/private/tmp/matura-hf-recovery.token').read_text().strip() if modal.is_local() else os.environ.get('HF_TOKEN','')})
ITEMS=[{'volume':'/text','source':'hf_cache/models--unsloth--Qwen3-4B-Instruct-2507-GGUF/snapshots/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf','dest':'models/qwen3-4b/Qwen3-4B-Instruct-2507-Q4_K_M.gguf','bytes':2497281120,'sha256':'3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597','upstream_repo':'unsloth/Qwen3-4B-Instruct-2507-GGUF','revision':'a06e946bb6b655725eafa393f4a9745d460374c9','license':'apache-2.0'}, {'volume':'/vision','source':'hf_cache/models--unsloth--Qwen3.5-4B-GGUF/snapshots/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-Q4_K_M.gguf','dest':'models/qwen35-4b/Qwen3.5-4B-Q4_K_M.gguf','bytes':2740937888,'sha256':'00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4','upstream_repo':'unsloth/Qwen3.5-4B-GGUF','revision':'e87f176479d0855a907a41277aca2f8ee7a09523','license':'apache-2.0'}, {'volume':'/vision','source':'hf_cache/models--unsloth--Qwen3.5-4B-GGUF/snapshots/e87f176479d0855a907a41277aca2f8ee7a09523/mmproj-F16.gguf','dest':'models/qwen35-4b/mmproj-F16.gguf','bytes':672423616,'sha256':'cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864','upstream_repo':'unsloth/Qwen3.5-4B-GGUF','revision':'e87f176479d0855a907a41277aca2f8ee7a09523','license':'apache-2.0'}]
@app.function(image=image,cpu=2,memory=4096,timeout=1200,max_containers=1,retries=0,scaledown_window=2,volumes={'/text':text_volume,'/vision':vision_volume},secrets=[secret])
def upload():
 import os,hashlib,io
 from huggingface_hub import HfApi
 api=HfApi(token=os.environ['HF_TOKEN']);repo='orestta/matura-small-track-recovery';assert api.model_info(repo).private is True
 completed=[]
 for item in ITEMS:
  p=Path(item['volume'])/item['source'];assert p.is_file() and p.stat().st_size==item['bytes']
  with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
  assert sha==item['sha256'];assert api.model_info(repo).private is True
  commit=api.upload_file(path_or_fileobj=str(p),path_in_repo=item['dest'],repo_id=repo,commit_message='Back up pinned '+Path(item['dest']).name)
  info=api.model_info(repo,revision=commit.oid,files_metadata=True);assert info.private is True
  remote=next(f for f in info.siblings if f.rfilename==item['dest']);assert remote.size==item['bytes'] and remote.lfs.sha256==item['sha256']
  completed.append({k:v for k,v in item.items() if k not in ('volume','source')}|{'commit':commit.oid,'verified':True});print(json.dumps({'path':item['dest'],'bytes':item['bytes'],'commit':commit.oid,'verified':True}),flush=True)
 for folder in ('models/qwen3-4b','models/qwen35-4b'):
  manifest={'files':[x for x in completed if x['dest'].startswith(folder+'/')],'model_use':'offline local inference','private_recovery':True,'invalid_sft_included':False}
  api.upload_file(path_or_fileobj=json.dumps(manifest,indent=2).encode(),path_in_repo=folder+'/manifest.json',repo_id=repo,commit_message='Add verified '+folder+' recovery manifest')
 info=api.model_info(repo,files_metadata=True);assert info.private is True
 return {'repo':repo,'private':True,'commit':info.sha,'files':completed,'cpu_only':True}
@app.local_entrypoint()
def main():
 result=upload.remote();p=Path('artifacts/small_track/hf-recovery-models.json');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
