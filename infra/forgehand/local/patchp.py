p='/scratch/p_arms_inline.sh'
t=open(p).read()
a='log "END practice-describe rc=$? wall $(( $(date +%s)-s ))s"\n'
assert t.count(a)==1
head=t[:t.index(a)+len(a)]
rest='''# 01:25 CEST: :8100 was OOM-killed at 23:03Z during P1; P1/P2 results are void. Wait for the watchdog restart, rerun P2, P3, then P1 at concurrency 4 (harness thread).
w8100() { for i in $(seq 180); do curl -sf http://127.0.0.1:8100/v1/models >/dev/null && return 0; sleep 5; done; return 1; }
w8100; rm -rf results/subtype/practice-describe
s=$(date +%s); PICTURE_DESCRIBE=1 $C --out results/subtype/practice-describe > /scratch/out/practice-describe.console 2>&1; log "END practice-describe rerun rc=$? wall $(( $(date +%s)-s ))s"
w8100; s=$(date +%s); OPEN_BEST_OF=3 PICTURE_DESCRIBE=1 $C --out results/subtype/practice-openbo3-describe > /scratch/out/practice-openbo3-describe.console 2>&1; log "END practice-openbo3-describe rc=$? wall $(( $(date +%s)-s ))s"
w8100; rm -rf results/subtype/practice-openbo3
s=$(date +%s); OPEN_BEST_OF=3 ${C/--concurrency 8/--concurrency 4} --out results/subtype/practice-openbo3 > /scratch/out/practice-openbo3.console 2>&1; log "END practice-openbo3 rerun-c4 rc=$? wall $(( $(date +%s)-s ))s"
'''
open(p,'w').write(head+rest)
print(open(p).read()[-900:])
