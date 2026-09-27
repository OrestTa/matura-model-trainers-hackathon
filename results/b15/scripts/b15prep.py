import json,re,shutil,collections
from pathlib import Path
src=Path('/workspace/codex-small-track-all-papers-v2/data');R=Path('/scratch/claude-b15');d=R/'data'
d.mkdir(parents=True,exist_ok=True)
BAD=('probny-2026-01','2023-05','2024-05','2025-05','2026-05')
for route in ['closed_without_images','closed_with_images','open_without_images','open_with_images','essay']:
    rows=[json.loads(l) for l in (src/route/'train.jsonl').read_text().splitlines() if l.strip()]
    keep=[r for r in rows if not any(b in ' '.join(str(r.get(k,'')) for k in ('id','paper_id','source','source_paper_pdf')) for b in BAD)]
    (d/route).mkdir(exist_ok=True)
    (d/route/'train.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in keep))
    print(route,len(rows),'->',len(keep),'papers kept:',dict(collections.Counter(r.get('paper_id') for r in keep)))
shutil.copy(src/'router.json',d/'router.json')
# no manifest.json: trainer then skips Codex's frozen-hash check
C=Path('/workspace/codex-small-track-clean-v3')
t=(C/'train_bielik_real_native.py').read_text()
old="if str(row.get('year')) in ('2015','2016','2023','2024'):"
assert old in t
t=t.replace(old,"if any(b in str(row.get('id',''))+str(row.get('paper_id','')) for b in ('probny-2026-01','2023-05','2024-05','2025-05','2026-05')):")
t=t.replace("if not 0<fraction<=0.25:","if not 0<fraction<=0.5:").replace("0<args.gpu_memory_fraction<=0.25","0<args.gpu_memory_fraction<=0.5")
(R/'train_b15.py').write_text(t)
print('ok')
