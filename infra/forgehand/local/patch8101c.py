p='/scratch/essay_arms_8101.sh'
t=open(p).read()
anchor='# E7 rag_plan'
assert t.count(anchor)==1 and 'H3 ragplan' not in t
H='''s=$(date +%s); for r in 1 2; do RAG_PATH=data/kb/factsheets.jsonl,data/kb/passages.jsonl THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers heldout --only-papers none --all-essays --subtypes essay --candidates rag_plan --model gemma4-12b-think --concurrency 8 --out results/subtype/heldout-essay/ragplan-r$r > /scratch/out/heldout-essay-ragplan-r$r.console 2>&1; done; log "END heldout-essay H3 ragplan rc=$? wall $(( $(date +%s)-s ))s"
'''
t=t.replace(anchor,H+anchor)
open(p,'w').write(t)
print(t[t.index('# H1/H2'):t.index('# E7')])
