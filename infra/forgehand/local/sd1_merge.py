# SD1 training set: 101 L40S rows + Nebius shards a/b (why-lose thread), image paths made absolute for /scratch/repo4.
import json, os
ex = {l.strip() for l in open('/scratch/work/sd/exclude_sources.txt') if l.strip()}
rows = [json.loads(l) for l in open('/scratch/work/sd/sd1_l40s.jsonl')]
n_l40s = len(rows)
for f in ('a', 'b'):
    for l in open(f'/scratch/sd1-shards/selfdistill-{f}.jsonl'):
        r = json.loads(l)
        r['images'] = [p if p.startswith('/') else '/scratch/repo4/' + p for p in r['images']]
        rows.append(r)
bad_img = [p for r in rows for p in r['images'] if not os.path.exists(p)]
excl = [r for r in rows if r['source'] in ex]
kept = [r for r in rows if r['source'] not in ex]
os.makedirs('/scratch/work/sd1m', exist_ok=True)
with open('/scratch/work/sd1m/selfdistill.jsonl', 'w') as o:
    for r in kept: o.write(json.dumps(r, ensure_ascii=False) + '\n')
dups = len(kept) - len({(r['source'], json.dumps(r['messages'][-1], ensure_ascii=False)) for r in kept})
print(f'l40s {n_l40s} + nebius {len(rows)-n_l40s} = {len(rows)}; excluded {len(excl)} rows; kept {len(kept)}; missing images {len(bad_img)} {bad_img[:3]}; exact dups {dups}')
