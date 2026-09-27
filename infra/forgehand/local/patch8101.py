p='/scratch/essay_arms_8101.sh'
t=open(p).read()
old='s=$(date +%s); $C --subtypes essay --candidates rag_plan --out results/subtype/essay-ragplan'
assert t.count(old)==1
i=t.index(old); assert 'essay-bo3 rc' in t[:i]
t=t.replace(old,'s=$(date +%s); RAG_PATH=data/kb/factsheets.jsonl,data/kb/passages.jsonl $C --subtypes essay --candidates rag_plan --out results/subtype/essay-ragplan')
t=t.rstrip('\n')+'\n# E7 rag_plan over the era fact sheets only (harness thread 01:00 CEST)\ns=$(date +%s); RAG_PATH=data/kb/factsheets.jsonl THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers dev --only-papers none --all-essays --subtypes essay --candidates rag_plan --model gemma4-12b-think8k --concurrency 8 --out results/subtype/essay-ragplan-fs > /scratch/out/essay-ragplan-fs.console 2>&1; log "END essay-ragplan-fs rc=$? wall $(( $(date +%s)-s ))s"\n'
open(p,'w').write(t)
print(t[i-40:])
