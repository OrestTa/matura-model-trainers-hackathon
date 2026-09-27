p='/scratch/essay_arms_8101.sh'; t=open(p).read()
a='# E7 rag_plan'
assert t.count(a)==1 and 'essay-ragbo3plan' not in t
E8='''# E8 rag_bo3plan on the dev essays (harness thread 01:42 CEST), after H1-H3, before E7
s=$(date +%s); RAG_PATH=data/kb/passages.jsonl,data/kb/factsheets.jsonl ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers dev --only-papers none --all-essays --subtypes essay --candidates rag_plan --model gemma4-12b-think8k --concurrency 8 --out results/subtype/essay-ragbo3plan > /scratch/out/essay-ragbo3plan.console 2>&1; log "END essay-ragbo3plan rc=$? wall $(( $(date +%s)-s ))s"
'''
open(p,'w').write(t.replace(a,E8+a)); print('ok')
