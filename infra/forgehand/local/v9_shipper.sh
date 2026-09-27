#!/bin/bash
# Pushes each finished V9 results dir (heldout-v5, think-sweep/<key>, essay-*) from the box to main.
S=/tmp/claude-0/-home-user-matura-model-trainers-hackathon/b6eb735e-2991-5c23-9f51-7520b5adb6ca/scratchpad
R=/home/user/matura-model-trainers-hackathon; touch $S/v9_shipped.txt
while true; do
  timeout 60 python3 $S/fhx.py exec 'grep -E "V9 END (heldout-v5|sweep|essay|practice-)" /scratch/master_chain.log' 2>/dev/null > $S/v9_ends.txt
  while read -r line; do
    grep -qxF "$line" $S/v9_shipped.txt && continue
    name=$(echo "$line" | awk '{print $4}'); [ "$name" = sweep ] && d=think-sweep/$(echo "$line" | awk '{print $5}') || d=$name; [ "$name" = essay-e4 ] && d=practice-raw8k
    timeout 120 python3 $S/fhx.py exec "cd /scratch/repo4 && tar czf /scratch/ship.tgz results/subtype/$d && ls -la /scratch/ship.tgz" >/dev/null 2>&1
    timeout 300 python3 $S/fhx.py get /scratch/ship.tgz $S/ship.tgz >/dev/null 2>&1 || continue
    rm -rf $S/shipchk && mkdir -p $S/shipchk && tar xzf $S/ship.tgz -C $S/shipchk
    # Fail fast (harness thread 01:20 CEST): never commit a run with >10% blank or error answers.
    if ! python3 -c "
import json,glob,sys
rows=[json.loads(l) for f in glob.glob('$S/shipchk/**/answers.jsonl',recursive=True) for l in open(f) if l.strip()]
bad=sum(1 for r in rows if r.get('error') or not (r.get('answer') or '').strip())
print(f'{bad}/{len(rows)} blank or error'); sys.exit(0 if rows and bad<=0.1*len(rows) else 1)" >> $S/v9_shipper.log 2>&1; then
      echo "$line" >> $S/v9_shipped.txt; echo "$(date -u +%T) NOT SHIPPED (>10% blank/error) $d" >> $S/v9_shipper.log; continue; fi
    cd $R && tar xzf $S/ship.tgz && git add results/subtype/$d && git commit -qm "L40S results: $d ($(echo "$line" | cut -d' ' -f5-))

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LQKZyjhfdG5AWqu5uVv8PZ" && ok=0; for i in 1 2 3; do git pull -q --rebase origin main && git push -q origin HEAD:main && ok=1 && break; sleep 5; done; [ $ok = 1 ] || { echo "$(date -u +%T) FAILED $d" >> $S/v9_shipper.log; continue; }
    echo "$line" >> $S/v9_shipped.txt; echo "$(date -u +%T) shipped $d $(git -C $R log --oneline -1 | cut -c1-8)" >> $S/v9_shipper.log
  done < $S/v9_ends.txt
  sleep 60
done
