"""Bounded private GGUF inference. Uploads candidate JSONL only, never keys/repo.

modal run infra/small_track/modal_infer.py --candidate data/.../candidate.jsonl
"""
import json
import time
from pathlib import Path
import modal

app = modal.App("matura-small-independent")
image = (modal.Image.from_registry("ghcr.io/ggml-org/llama.cpp:server-cuda", add_python="3.12")
         .entrypoint([]).pip_install("huggingface_hub", "requests"))
if modal.is_local():
    image=image.add_local_file("scripts/small_track/voting.py","/app/voting.py")
volume = modal.Volume.from_name("matura-small-independent", create_if_missing=True)

@app.function(image=image, gpu="L4", cpu=2, memory=8192, timeout=1800,
              max_containers=2, scaledown_window=2, retries=0, volumes={"/outputs": volume})
def infer(config: dict, rows: list, run_id: str):
    import hashlib
    import os
    import subprocess
    import requests
    from concurrent.futures import ThreadPoolExecutor
    from huggingface_hub import HfApi, hf_hub_download
    os.environ["HF_HOME"]="/outputs/hf_cache"
    started = time.time()
    dest = Path("/outputs") / run_id
    dest.mkdir(parents=True, exist_ok=False)
    revision = config.get("revision") or HfApi().model_info(config["repo"]).sha
    model = hf_hub_download(config["repo"], config["file"], revision=revision, cache_dir="/outputs/hf_cache")
    model_bytes = Path(model).stat().st_size
    manifest = dict(config=config, revision=revision, run_id=run_id,
                    serialized_weight_bytes=model_bytes, started=started,
                    modality="text_from_candidate", timeout_seconds=1800, seed=42,
                    candidate_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))
    binary = next((p for p in ["/app/llama-server", "/llama-server", "/usr/local/bin/llama-server"] if Path(p).exists()), "llama-server")
    log = open(dest / "server.log", "w")
    util_log = open(dest / "gpu-util.csv", "w")
    monitor = subprocess.Popen(["nvidia-smi","--query-gpu=timestamp,utilization.gpu,memory.used,power.draw","--format=csv","-l","5"],stdout=util_log)
    manifest["server_version"]=subprocess.run([binary,"--version"],capture_output=True,text=True).stdout.strip()
    proc = subprocess.Popen([binary,"-m",model,"--host","127.0.0.1","--port","8080","-ngl","99",
                             "-c","65536","-np","8","--jinja"], stdout=log, stderr=log)
    try:
        for _ in range(180):
            if proc.poll() is not None:
                raise RuntimeError("llama-server failed; inspect server.log")
            try:
                if requests.get("http://127.0.0.1:8080/health",timeout=2).ok: break
            except requests.RequestException: pass
            time.sleep(1)
        else: raise TimeoutError("model startup")
        (dest / "tokenizer-smoke.json").write_text(json.dumps(requests.post("http://127.0.0.1:8080/tokenize",json={"content":"Polska odzyskała niepodległość w 1918 roku.","add_special":False},timeout=5).json()))
        (dest / "server-props.json").write_text(json.dumps(requests.get("http://127.0.0.1:8080/props",timeout=5).json(),indent=2))
        base_config=config
        def one(row):
            config=dict(base_config)
            if config.get("route_configs"):
                config.update(config["route_configs"][row["subtype"]])
                config["route"]=row["subtype"]
            out = {"id":row["id"], "run_id":run_id, "answer":""}
            if time.time()-started > 1600:
                out["error"]="worker deadline"; return out
            question=row.get("question","")
            if config.get("essay_topic_index"):
                import re
                topics=re.findall(r"(?:^|\n)([1-3])\.\s*(.*?)(?=\n[1-3]\.\s|$)",question,re.S)
                selected=next(((n,t) for n,t in topics if int(n)==config["essay_topic_index"]),None)
                if selected:
                    question="Opracuj wyłącznie temat "+selected[0]+". Minimum 300 wyrazów.\n"+selected[0]+". "+selected[1]
                    out["essay_topic_projection"]=selected[0]
            prompt = "\n\n".join((str(row.get("context","")),question))
            if config.get("route_trial") == "concise":
                hints={"closed_without_images":"Zwróć dokładnie wymagane oznaczenia w kolejności podpunktów. Zachowaj rozróżnienie P/F, liter i numerów. Nie dopisuj alternatywnych odpowiedzi.","closed_with_images":"Sprawdź zgodność każdej opcji z podanymi źródłami. Podaj tylko jednoznaczny wybór dla każdego podpunktu w żądanym formacie.","open_without_images":"Najpierw podaj bezpośrednią odpowiedź. Następnie, tylko jeśli wymagane, uzasadnij ją jednym konkretnym faktem ze źródła. Uwzględnij każdy czasownik polecenia.","open_with_images":"Podaj rozstrzygnięcie oraz oddzielne uzasadnienie, jeżeli polecenie tego wymaga. Oprzyj odpowiedź na dostępnych źródłach i wiedzy historycznej. Nie mieszaj kilku sprzecznych identyfikacji.","essay":"Wybierz jeden temat. Napisz około 400 słów w czterech akapitach: teza, argumentacja pierwszego aspektu z faktami, argumentacja pozostałych aspektów z faktami, wniosek. Każdy wymagany aspekt musi zostać omówiony."}
                prompt += "\n\n"+hints[config["route"]]
            if config.get("essay_rescue"):
                prompt += "\n\nNapisz jedno kompletne wypracowanie o długości 450–550 słów. Wybierz temat, dla którego znasz najwięcej faktów. Zacznij od numeru tematu i tezy. Każdy akapit ma rozwijać wymagany aspekt, wskazywać konkretne wydarzenia, postacie i daty oraz wyjaśniać związki przyczynowe. Zakończ oceną zgodną z tezą. Nie pisz planu ani komentarzy do zadania. Nie powtarzaj tych instrukcji."
            if config.get("essay_only") and row.get("points",0)>=10:
                prompt += "\n\nWybierz dokładnie jeden temat. Napisz kompletną wypowiedź liczącą co najmniej 350 słów: teza, konkretne argumenty historyczne dla wszystkich wymaganych aspektów i końcowy wniosek. Nie przepisuj poleceń ani pozostałych tematów."
            if config.get("closed_only") and str(row.get("subtype","")).startswith("closed_"):
                prompt += "\n\nPodaj wyłącznie końcowe odpowiedzi w wymaganym formacie: litery, numery, dopasowania albo P/F. Dla każdego podpunktu podaj dokładnie jedną odpowiedź. Nie dodawaj komentarza ani nie powtarzaj pytania."
            if config.get("optimized"):
                if row.get("points",0)>=10:
                    hint="Wybierz dokładnie JEDEN temat, który najlepiej znasz. Napisz spójne wypracowanie co najmniej 350 słów. Sformułuj tezę, rozwiń wszystkie wymagane aspekty z konkretnymi prawidłowymi faktami i zakończ wnioskiem. Nie przepisuj polecenia, nie omawiaj innych tematów."
                else:
                    hint="Przeczytaj każde źródło uważnie. Odpowiedz wyłącznie na konkretne polecenie, zwięźle. Jeśli wymagane jest rozstrzygnięcie i uzasadnienie, napisz oba i wskaż konkretną przesłankę ze źródła. Jeśli trzeba wybrać lub przyporządkować odpowiedzi, podaj jednoznaczne oznaczenia. Nie przepisuj polecenia. Nie wymyślaj szczegółów niewidocznych ilustracji."
                prompt += "\n\nWskazówka wykonania: " + hint
            try:
                response = requests.post("http://127.0.0.1:8080/v1/chat/completions",json={
                    "messages":[{"role":"system","content":"Rozwiąż zadanie maturalne z historii. Odpowiedz po polsku, konkretnie i zgodnie z poleceniem. Jeśli polecenie wymaga rozstrzygnięcia i uzasadnienia, podaj oba. Dla wypracowania napisz pełną argumentację. Nie opisuj procesu myślenia."},
                                {"role":"user","content":prompt}],
                    "temperature":config.get("temperature",0),"max_tokens":config.get("max_tokens_essay",1600) if row.get("points",0)>=10 else 500,
                    "seed":42}, timeout=180)
                response.raise_for_status()
                body=response.json(); out["answer"]=body["choices"][0]["message"].get("content") or ""
                if config.get("vote_samples",1)==3:
                    import sys
                    sys.path.insert(0,"/app")
                    from voting import choose_vote
                    payload=json.loads(response.request.body); samples=[out["answer"]]; usages=[body.get("usage",{})]
                    for extra in (1,2):
                        payload["seed"]=42+extra;payload["temperature"]=0.7
                        rr=requests.post("http://127.0.0.1:8080/v1/chat/completions",json=payload,timeout=120);rr.raise_for_status();bb=rr.json();samples.append(bb["choices"][0]["message"].get("content") or "");usages.append(bb.get("usage",{}))
                    vote=choose_vote(samples);out.update(answer=vote["answer"],samples=samples,vote=vote,baseline_first_sample=samples[0],sample_usages=usages)
                if config.get("route_trial") == "review":
                    out["draft_answer"]=out["answer"]
                    out["draft_usage"]=body.get("usage")
                    revision=requests.post("http://127.0.0.1:8080/v1/chat/completions",json={"messages":[{"role":"user","content":prompt},{"role":"assistant","content":out["answer"]},{"role":"user","content":"Sprawdź powyższą odpowiedź: czy odpowiada na każdy podpunkt i ma wszystkie wymagane elementy, czy nie zawiera sprzeczności, błędnych dat, nazw lub pomylonych źródeł? Popraw konkretne wykryte błędy. Zwróć tylko ostateczną kompletną odpowiedź, bez opisu sprawdzania."}],"temperature":0,"seed":42,"max_tokens":1600 if row.get("points",0)>=10 else 500},timeout=120)
                    revision.raise_for_status();body=revision.json();out["answer"]=body["choices"][0]["message"].get("content") or ""
                out["finish_reason"]=body["choices"][0].get("finish_reason")
                out["usage"]=body.get("usage")
            except Exception as exc: out["error"]=type(exc).__name__
            return out
        answers=[]
        with ThreadPoolExecutor(max_workers=8) as pool, open(dest/"answers.jsonl","w") as f:
            for answer in pool.map(one,rows):
                answers.append(answer); f.write(json.dumps(answer,ensure_ascii=False)+"\n"); f.flush()
                if len(answers)%10==0: volume.commit()
        manifest.update(concurrency=8, context_per_slot=8192, total_completion_tokens=sum((x.get("usage") or {}).get("completion_tokens",0)+(x.get("draft_usage") or {}).get("completion_tokens",0) for x in answers), elapsed_seconds=time.time()-started, answered=sum(bool(x["answer"]) for x in answers), items=len(rows))
        (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)); volume.commit()
        return {"manifest":manifest,"answers":answers}
    finally:
        proc.terminate(); monitor.terminate(); log.close(); util_log.close(); volume.commit()

@app.local_entrypoint()
def main(candidate: str, output: str="results/small_track", wave: str="bielik"):
    rows=[json.loads(x) for x in Path(candidate).read_text().splitlines() if x.strip()]
    allowed={"id","paper_id","task_id","paper","year","formula","task","points","context","question","page_images","needs_image","type","subtype"}
    rows=[{k:v for k,v in row.items() if k in allowed} for row in rows]
    if not rows or not all(r.get("id") and r.get("question") for r in rows): raise ValueError("Invalid candidate inputs")
    configs=[{"repo":"second-state/Bielik-1.5B-v3.0-Instruct-GGUF","file":"Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf","name":"bielik15-q4"},
             {"repo":"second-state/Bielik-4.5B-v3.0-Instruct-GGUF","file":"Bielik-4.5B-v3.0-Instruct-Q3_K_M.gguf","name":"bielik45-q3"},
             {"repo":"second-state/Bielik-4.5B-v3.0-Instruct-GGUF","file":"Bielik-4.5B-v3.0-Instruct-Q4_K_M.gguf","name":"bielik45-q4"}]
    if wave == "canonical":
        configs=[dict(configs[0], name="bielik15-q4-canonical-b0"),dict(configs[2], name="bielik45-q4-canonical-b0")]
    if wave == "essay-only":
        configs=[dict(configs[0],name="bielik15-q4-canonical-p2-essay",essay_only=True),dict(configs[2],name="bielik45-q4-canonical-p2-essay",essay_only=True)]
    if wave == "closed-only":
        configs=[dict(configs[0],name="bielik15-q4-canonical-p3-closed",closed_only=True),dict(configs[2],name="bielik45-q4-canonical-p3-closed",closed_only=True)]
    if wave == "canonical-v1":
        configs=[dict(configs[0], name="bielik15-q4-canonical-v1",vision_preprocessor="qwen35-2b-q4-f16-projector"),dict(configs[2], name="bielik45-q4-canonical-v1",vision_preprocessor="qwen35-2b-q4-f16-projector")]
    if wave == "f16-smoke":
        configs=[dict(configs[0],file="Bielik-1.5B-v3.0-Instruct-f16.gguf",name="bielik15-f16-native-smoke")]
        rows=rows[:3]
    if wave == "optimized":
        configs=[dict(configs[0], name="bielik15-q4-optimized", optimized=True)]
    if wave == "precision":
        configs=[{"repo":"second-state/Bielik-1.5B-v3.0-Instruct-GGUF","file":"Bielik-1.5B-v3.0-Instruct-Q8_0.gguf","name":"bielik15-q8"},
                 {"repo":"second-state/Bielik-4.5B-v3.0-Instruct-GGUF","file":"Bielik-4.5B-v3.0-Instruct-Q5_K_M.gguf","name":"bielik45-q5"}]
    stamp=time.strftime("%Y%m%d-%H%M%S",time.gmtime())
    calls=[(c,infer.spawn(c,rows,stamp+"-"+c["name"])) for c in configs]
    for config,call in calls:
        result=call.get(); dest=Path(output)/result["manifest"]["run_id"]; dest.mkdir(parents=True,exist_ok=True)
        (dest/"manifest.json").write_text(json.dumps(result["manifest"],indent=2))
        (dest/"answers.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in result["answers"]))
        print(json.dumps(result["manifest"]))

@app.function(image=image,cpu=2,memory=1024,timeout=300,max_containers=1,retries=0,scaledown_window=2,volumes={"/outputs":volume})
def audit_weights():
    import hashlib
    from huggingface_hub import HfApi,hf_hub_download
    artifacts=[]
    for repo,name in [('second-state/Bielik-1.5B-v3.0-Instruct-GGUF','Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf'),('second-state/Bielik-4.5B-v3.0-Instruct-GGUF','Bielik-4.5B-v3.0-Instruct-Q4_K_M.gguf'),('unsloth/Qwen3.5-2B-GGUF','Qwen3.5-2B-Q4_K_M.gguf'),('unsloth/Qwen3.5-2B-GGUF','mmproj-F16.gguf')]:
        revision=HfApi().model_info(repo).sha
        path=Path(hf_hub_download(repo,name,revision=revision,cache_dir='/outputs/hf_cache'))
        digest=hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(8*1024*1024),b''):digest.update(chunk)
        artifacts.append({'repo':repo,'revision':revision,'filename':name,'bytes':path.stat().st_size,'sha256':digest.hexdigest()})
    return artifacts

@app.local_entrypoint()
def export_artifacts():
    artifacts=audit_weights.remote()
    path=Path('results/small_track/artifact_manifest.json');path.write_text(json.dumps(artifacts,indent=2));print(json.dumps(artifacts))

@app.local_entrypoint()
def matrix(candidate:str="data/small_track/official_mock_v1/canonical-b0-candidate.jsonl"):
    from concurrent.futures import ThreadPoolExecutor,as_completed
    import hashlib
    rows=[json.loads(s) for s in Path(candidate).read_text().splitlines() if s.strip()]
    forbidden={"gold","gold_keywords","rubric","official_solution","reference","solution","answer","answers"}
    if any(forbidden.intersection(r) for r in rows):raise ValueError("candidate key leak")
    models=[("bielik15", "second-state/Bielik-1.5B-v3.0-Instruct-GGUF","Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf"),("bielik45","second-state/Bielik-4.5B-v3.0-Instruct-GGUF","Bielik-4.5B-v3.0-Instruct-Q4_K_M.gguf")]
    routes=["closed_without_images","closed_with_images","open_without_images","open_with_images","essay"]
    stamp=time.strftime("%Y%m%d-%H%M%S",time.gmtime());jobs=[]
    for short,repo,file in models:
        baseline_path=Path("results/small_track")/("20260926-183916-"+short+"-q4-canonical-b0")/"answers.jsonl"
        baseline={r["id"]:r for r in map(json.loads,baseline_path.read_text().splitlines())}
        for route in routes:
            subset=[r for r in rows if r["subtype"]==route]
            if not subset:continue
            for technique in ("concise","review"):
                name=stamp+"-"+short+"-"+route+"-"+technique
                config={"repo":repo,"file":file,"name":name,"route":route,"route_trial":technique,"seed":42,"max_tokens_short":500,"max_tokens_essay":1600,"passes":2 if technique=="review" else 1}
                call=infer.with_options(timeout=300).spawn(config,subset,name)
                jobs.append((call,name,baseline,subset,baseline_path))
    print("Submitted "+str(len(jobs))+" distinct route trials; each <=300s",flush=True)
    def collect(job):
        call,name,baseline,subset,baseline_path=job;result=call.get()
        changed={r["id"]:r for r in result["answers"]};composed=[]
        for row in rows:
            source=changed.get(row["id"],baseline[row["id"]]);answer=dict(source)
            answer["answer_origin"]="trial" if row["id"] in changed else "frozen_baseline"
            answer["composed_run_id"]=name;composed.append(answer)
        manifest=result["manifest"]
        manifest.update(composed=True,target_ids=list(changed),unchanged_ids=[r["id"] for r in rows if r["id"] not in changed],baseline_answers_sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest(),baseline_path=str(baseline_path),full_candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),timeout_seconds=300,classification_source="root rules-v1")
        dest=Path("results/small_track")/name;dest.mkdir(parents=True,exist_ok=True)
        (dest/"manifest.json").write_text(json.dumps(manifest,indent=2))
        (dest/"target_answers.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in result["answers"]))
        (dest/"answers.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in composed))
        return name,len(changed)
    with ThreadPoolExecutor(max_workers=20) as pool:
        for future in as_completed([pool.submit(collect,j) for j in jobs]):
            print(json.dumps({"completed":future.result()}),flush=True)


@app.local_entrypoint()
def essay_rescue():
    import hashlib
    rows=[json.loads(s) for s in Path("data/small_track/official_mock_v1/canonical-b0-candidate.jsonl").read_text().splitlines()]
    subset=[r for r in rows if r["subtype"]=="essay"]
    stamp=time.strftime("%Y%m%d-%H%M%S",time.gmtime()); calls=[]
    for quant in ("Q4_K_M","Q8_0"):
        name=stamp+"-bielik15-"+quant+"-essay-rescue"
        cfg={"repo":"second-state/Bielik-1.5B-v3.0-Instruct-GGUF","file":"Bielik-1.5B-v3.0-Instruct-"+quant+".gguf","name":name,"essay_rescue":True,"max_tokens_essay":3200,"seed":42}
        calls.append(infer.with_options(timeout=300,max_containers=2).spawn(cfg,subset,name))
    for call in calls:
        result=call.get();dest=Path("results/small_track")/result["manifest"]["run_id"];dest.mkdir(parents=True,exist_ok=True)
        (dest/"target_answers.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in result["answers"]))
        (dest/"manifest.json").write_text(json.dumps(result["manifest"],indent=2));print(json.dumps(result["manifest"]),flush=True)


@app.local_entrypoint()
def frozen(candidate:str="data/small_track/official_mock_v1/canonical-b0-candidate.jsonl", model:str="both", config_suffix:str="frozen", router_model:str="", vote_samples:int=1):
    import importlib.util,hashlib
    spec=importlib.util.spec_from_file_location("router","scripts/small_track/classifier.py");router=importlib.util.module_from_spec(spec);spec.loader.exec_module(router)
    rows=[json.loads(s) for s in Path(candidate).read_text().splitlines() if s.strip()]
    for row in rows:
        if {"answer","answers","gold","rubric","solution"}.intersection(row):raise ValueError("candidate key leak")
        row.update(router.classify(row))
    if router_model:
        spec2=importlib.util.spec_from_file_location("trained_router","scripts/small_track/train_router.py");trained=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(trained);rm=json.loads(Path(router_model).read_text())
        for row in rows:row.update(trained.predict(row,rm))
    stamp=time.strftime("%Y%m%d-%H%M%S",time.gmtime());calls=[]
    for short in (("bielik15","bielik45") if model=="both" else (model,)):
        config=json.loads(Path("infra/small_track/configs/"+short+"-"+config_suffix+".json").read_text());config.update(vote_samples=vote_samples,temperature=0.7,router_model_sha256=hashlib.sha256(Path(router_model).read_bytes()).hexdigest() if router_model else None);run=stamp+"-"+short+"-"+config_suffix+"-e2e"
        calls.append(infer.with_options(timeout=300,max_containers=2).spawn(config,rows,run))
    for call in calls:
        result=call.get();result["manifest"].update(timeout_seconds=300,composed=False,classifier=router.VERSION,harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        dest=Path("results/small_track")/result["manifest"]["run_id"];dest.mkdir(parents=True,exist_ok=True)
        (dest/"answers.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in result["answers"]));(dest/"manifest.json").write_text(json.dumps(result["manifest"],indent=2));print(json.dumps(result["manifest"]),flush=True)
