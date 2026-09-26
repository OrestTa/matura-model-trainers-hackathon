from pathlib import Path
import json
from huggingface_hub import HfApi,CommitOperationCopy
api=HfApi(token=Path('/private/tmp/matura-hf-recovery.token').read_text().strip());repo='orestta/matura-small-track-recovery';assert api.model_info(repo).private
items=[('unsloth/Qwen3.5-4B-GGUF','e87f176479d0855a907a41277aca2f8ee7a09523','Qwen3.5-4B-Q3_K_M.gguf','models/qwen35-4b/Qwen3.5-4B-Q3_K_M.gguf',2293388448,'d6981ab4d77ba712b48ef69d69042d75b5e39b9dce5fb5a5b054fd08e06afb95'),('second-state/Bielik-1.5B-v3.0-Instruct-GGUF','6c316d2be07dee472901150c3f3e9d4f725a4706','Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf','models/bielik15/Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf',972797408,'ea9cc250a6c65718c290fd963d8e3237b924ccfc7632f20a6127bba5904a50d9')]
ops=[]
for src,rev,name,dest,b,sha in items:
 info=api.model_info(src,revision=rev,files_metadata=True);f=next(x for x in info.siblings if x.rfilename==name);assert f.size==b and f.lfs.sha256==sha
 ops.append(CommitOperationCopy(src_path_in_repo=name,path_in_repo=dest,src_revision=rev,src_repo_id=src,src_repo_type='model'))
ops.append(CommitOperationCopy(src_path_in_repo='README.md',path_in_repo='licenses/Bielik-1.5B-upstream-README.md',src_revision=items[1][1],src_repo_id=items[1][0],src_repo_type='model'))
c=api.create_commit(repo_id=repo,operations=ops,commit_message='Private recovery of pinned Qwen Q3 and Bielik Q4 via server-side copy')
info=api.model_info(repo,revision=c.oid,files_metadata=True);assert info.private
path=Path('artifacts/small_track/hf-recovery-current.json');m=json.loads(path.read_text())
for src,rev,name,dest,b,sha in items:
 f=next(x for x in info.siblings if x.rfilename==dest);assert f.size==b and f.lfs.sha256==sha;m['files'].append({'path':dest,'bytes':b,'sha256':sha,'commit':c.oid,'verified':True,'upstream_repo':src,'revision':rev,'license':'apache-2.0','transfer':'HF server-side cross-repository copy'})
m['commit']=c.oid;path.write_text(json.dumps(m,indent=2));print(json.dumps({'commit':c.oid,'private':True,'new_weights_verified':2}))
