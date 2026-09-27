# 1) essay queue: keep the no-guard H2 as bo3plan-noguard-r*, then run the guarded H2 (harness 01:41 CEST), before H3.
p='/scratch/essay_arms_8101.sh'; t=open(p).read()
a='s=$(date +%s); for r in 1 2; do RAG_PATH=data/kb/factsheets.jsonl,data/kb/passages.jsonl'
assert t.count(a)==1 and 'bo3plan-noguard' not in t
H='''for r in 1 2; do rm -rf results/subtype/heldout-essay/bo3plan-noguard-r$r; mv results/subtype/heldout-essay/bo3plan-r$r results/subtype/heldout-essay/bo3plan-noguard-r$r; done
s=$(date +%s); for r in 1 2; do ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1 python scripts/subtype_sweep.py --base-url http://127.0.0.1:8101/v1 --papers heldout --only-papers none --all-essays --subtypes essay --candidates plan --model gemma4-12b-think --concurrency 8 --out results/subtype/heldout-essay/bo3plan-r$r > /scratch/out/heldout-essay-bo3plan-guard-r$r.console 2>&1; done; log "END heldout-essay H2 bo3plan-guard rc=$? wall $(( $(date +%s)-s ))s"
'''
open(p,'w').write(t.replace(a,H+a))
# 2) practice arms: P1-P3 all hit OOM restarts; rerun all three once :8100 runs with --cache-ram 0.
p='/scratch/p_arms_inline.sh'; t=open(p).read()
assert 'cache-ram' not in t
t=t.rstrip('\n')+'''
# 01:50 CEST: the OOM came from llama-server's 8 GiB host prompt cache (x2 servers). :8100 now runs --cache-ram 0; rerun P2, P3, P1 (c4).
w8100; rm -rf results/subtype/practice-describe; s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rerun2 rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3-describe; s=$(date +%s); OPEN_BEST_OF=3 PICTURE_DESCRIBE=1 $C --out results/subtype/practice-openbo3-describe > /scratch/out/practice-openbo3-describe.console 2>&1; log "END practice-openbo3-describe rerun2 rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3; s=$(date +%s); OPEN_BEST_OF=3 ${C/--concurrency 8/--concurrency 4} --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rerun2-c4 rc=$? wall $(( $(date +%s)-s ))s"
'''
open(p,'w').write(t)
print('patched')
