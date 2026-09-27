p='/scratch/main_v9.sh'; t=open(p).read()
a='arm tb1k $NONESSAY ""\n'
assert t.count(a)==1 and 'sd1_go' not in t
open(p,'w').write(t.replace(a, a+'touch /scratch/sd1_go; while [ ! -f /scratch/sd1_done ]; do sleep 60; done  # SD1 train+eval before te24k/tb16k (03:40 CEST)\n'))
print('ok')
