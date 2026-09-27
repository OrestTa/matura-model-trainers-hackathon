p='/scratch/essay_arms_8101.sh'
t=open(p).read()
anchor='# E7 rag_plan'
assert t.count(anchor)==1
H='''# H1/H2 held-out essay confirmation (harness thread 01:16 CEST), ahead of E7
s=$(date +%s); for r in 1 2; do THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers heldout --only-papers none --all-essays --subtypes essay --candidates none --raw --model gemma4-12b-think --concurrency 8 --out results/subtype/heldout-essay/base-r$r > /scratch/out/heldout-essay-base-r$r.console 2>&1; done; log "END heldout-essay H1 base rc=$? wall $(( $(date +%s)-s ))s"
s=$(date +%s); for r in 1 2; do ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=0 THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers heldout --only-papers none --all-essays --subtypes essay --candidates plan --model gemma4-12b-think --concurrency 8 --out results/subtype/heldout-essay/bo3plan-r$r > /scratch/out/heldout-essay-bo3plan-r$r.console 2>&1; done; log "END heldout-essay H2 bo3plan rc=$? wall $(( $(date +%s)-s ))s"
'''
t=t.replace(anchor,H+anchor)
open(p,'w').write(t)
print(t[t.index('essay-bo3plan rc'):])
