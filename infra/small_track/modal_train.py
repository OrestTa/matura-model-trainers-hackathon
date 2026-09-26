"""Isolated, bounded synthetic-only SFT on Modal. No repository/keys uploaded."""
import json,time
from pathlib import Path
import modal
app=modal.App("matura-small-sft-independent")
volume=modal.Volume.from_name("matura-small-sft-independent",create_if_missing=True)
image=(modal.Image.debian_slim(python_version="3.12").pip_install("torch==2.8.0","transformers==4.56.2","peft==0.17.1","datasets==4.1.1","accelerate==1.10.1","bitsandbytes==0.47.0","gguf>=0.10.0","sentencepiece"))
if modal.is_local():
 image=image.add_local_file(Path(__file__).resolve().parents[2]/"scripts/small_track_train.py","/src/train.py")
@app.function(image=image,gpu="H100",cpu=4,memory=16384,timeout=1200,max_containers=1,retries=0,scaledown_window=2,volumes={"/outputs":volume})
def train(rows:list,model:str,run_id:str,steps:int,gguf_file:str=""):
 import subprocess,os
 dest=Path("/outputs")/run_id; dest.mkdir(parents=True,exist_ok=False)
 data=dest/"synthetic.jsonl"; data.write_text("".join(json.dumps(r,ensure_ascii=False)+chr(10) for r in rows))
 command=["python","/src/train.py","--model",model,"--data",str(data),"--output",str(dest),"--steps",str(steps),"--max-length","4096"]
 command += ["--gguf-file",gguf_file,"--save-merged"] if gguf_file else ["--four-bit"]
 with open(dest/"training.log","w") as log:
  proc=subprocess.Popen(command,stdout=log,stderr=log,env=dict(os.environ,HF_HOME="/outputs/hf_cache"))
  started=time.monotonic()
  while proc.poll() is None:
   if time.monotonic()-started>1100:
    proc.terminate(); proc.wait(timeout=20); volume.commit(); raise TimeoutError("bounded SFT deadline")
   time.sleep(10); volume.commit()
  volume.commit()
  if proc.returncode: raise RuntimeError("training failed; inspect persistent training.log")
 return json.loads((dest/"training_manifest.json").read_text())
@app.local_entrypoint()
def main(data:str,model:str,steps:int=80,gguf_file:str=""):
 rows=[json.loads(s) for s in Path(data).read_text().splitlines() if s.strip()]
 if not rows or any(not r.get("synthetic") for r in rows): raise ValueError("synthetic only")
 name=time.strftime("%Y%m%d-%H%M%S",time.gmtime())+"-"+model.split("/")[-1]
 print(json.dumps(train.remote(rows,model,name,steps,gguf_file),indent=2))

@app.local_entrypoint()
def prepare():
 print("Training image built; no GPU allocated.")

@app.function(image=image,gpu="H100",cpu=4,memory=16384,timeout=1200,max_containers=2,retries=0,scaledown_window=2,volumes={"/outputs":volume})
def paired(rows:list,source_run:str,label:str):
 import subprocess,os
 dest=Path("/outputs")/(source_run+"-paired-b8"); dest.mkdir(parents=True,exist_ok=True)
 candidates=dest/(label+"-candidate.jsonl"); candidates.write_text("".join(json.dumps(r,ensure_ascii=False)+chr(10) for r in rows))
 command=["python","/src/train.py","--pair-only","--pair-label",label,"--pair-batch-size","8","--model","second-state/Bielik-1.5B-v3.0-Instruct-GGUF","--gguf-file","Bielik-1.5B-v3.0-Instruct-f16.gguf","--pair-candidates",str(candidates),"--pair-merged",str(Path("/outputs")/source_run/"merged"),"--output",str(dest),"--max-new-tokens","500","--essay-tokens","1600"]
 with open(dest/(label+"-paired.log"),"w") as log:
  proc=subprocess.Popen(command,stdout=log,stderr=log,env=dict(os.environ,HF_HOME="/outputs/hf_cache"))
  started=time.monotonic()
  while proc.poll() is None:
   if time.monotonic()-started>1100:
    proc.terminate(); proc.wait(timeout=20); volume.commit(); raise TimeoutError("paired deadline")
   time.sleep(10); volume.commit()
  volume.commit()
  if proc.returncode: raise RuntimeError("pair failed; inspect paired.log")
 return {p.name:p.read_text() for p in dest.glob(label+"_*.json*")}
@app.local_entrypoint()
def evaluate_pair(candidate:str,source_run:str):
 rows=[json.loads(s) for s in Path(candidate).read_text().splitlines() if s.strip()]
 calls=[paired.spawn(rows,source_run,label) for label in ("adapter","base")]
 dest=Path("results/small_track")/(source_run+"-paired-b8");dest.mkdir(parents=True,exist_ok=True)
 for call in calls:
  results=call.get()
  for name,contents in results.items(): (dest/name).write_text(contents)
  print("Saved "+", ".join(results),flush=True)
 print(str(dest))
