# main_v9: hold the remaining sweep arms until the stage rehearsal is done; essay queue: drop E7 (deferred).
p='/scratch/main_v9.sh'; t=open(p).read()
a='arm te16k essay --all-essays\n'
assert t.count(a)==1 and 'rehearsal_done' not in t
open(p,'w').write(t.replace(a,'while [ ! -f /scratch/rehearsal_done ]; do sleep 30; done  # stage rehearsal first (harness 02:59 CEST)\n'+a))
p='/scratch/essay_arms_8101.sh'; t=open(p).read()
i=t.index('# E7 rag_plan'); open(p,'w').write(t[:i]+'# E7 deferred: the stage rehearsal needs this VRAM (02:59 CEST)\n')
print('ok')
