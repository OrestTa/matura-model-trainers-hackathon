#!/bin/bash
# Every 60 s: copy each finished paper's answers.json from /scratch/out/<job>/ on the box to
# results/gemma4/<job>/, push to main, and Sol-grade it. Jobs: any /scratch/out/matura-infer-* dir.
S=/tmp/claude-0/-home-user-matura-model-trainers-hackathon/b6eb735e-2991-5c23-9f51-7520b5adb6ca/scratchpad
R=/home/user/matura-model-trainers-hackathon; cd $R
export SOL_BASE=${SOL_BASE:?set SOL_BASE to the Forgehand team LLM URL (secret: team id)}
export SOL_TOKEN=$(python3 -c "import json;print(json.load(open('/root/.config/forgehand/config.json'))['token'])")
while true; do
  list=$(python3 $S/fhx.py exec 'for d in /scratch/out/matura-infer-*/; do j=$(basename $d); for f in $d*/answers.json; do [ -f "$f" ] && echo "$j $(basename $(dirname $f))"; done; done' 2>/dev/null | grep '^matura-infer')
  new=""
  while read -r j p; do [ -z "$j" ] && continue; [ -f results/gemma4/$j/$p/answers.json ] && continue; new="$new $j/$p"; done <<< "$list"
  if [ -n "$new" ]; then
    python3 $S/fhx.py exec "cd /scratch/out && tar -czf /scratch/ship.tgz $(echo $new | sed 's#\([^ ]*\)#\1/answers.json#g') \$(ls -d $(echo $new | tr ' ' '\n' | cut -d/ -f1 | sort -u | sed 's#$#/timing.tsv#' | tr '\n' ' ') 2>/dev/null)" >/dev/null
    python3 $S/fhx.py get /scratch/ship.tgz $S/ship.tgz >/dev/null && mkdir -p results/gemma4 && tar -xzf $S/ship.tgz -C results/gemma4
    git pull -q --rebase origin main; git add results/gemma4
    git commit -qm "answers: $new

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LQKZyjhfdG5AWqu5uVv8PZ" && git push -q origin HEAD:main && echo "$(date -u +%T) pushed $new $(git log --oneline -1 | cut -c1-7)" >> $S/shipper.log
    for jp in $new; do j=${jp%/*}; p=${jp#*/}; D=results/judged/${j/infer/judge-claude}/$p; mkdir -p $D
      ( python3 scripts/sol_judge.py grade results/gemma4/$jp/answers.json --paper $p --model gpt-6-sol --out $D/sol_score.json > $S/sol_${j}_$p.log 2>&1
        echo "$(date -u +%T) sol $jp: $(grep '^sol' $S/sol_${j}_$p.log)" >> $S/shipper.log ) &
    done
  fi
  if [ -n "$(git status --porcelain results/judged | grep sol_score)" ]; then
    sed -i -E 's#https?://[^" ]+#<url>#g' results/judged/*/*/sol_score.json
    git pull -q --rebase origin main; git add results/judged/*/*/sol_score.json
    git commit -qm "Sol (gpt-6-sol) second-opinion grades

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LQKZyjhfdG5AWqu5uVv8PZ" && git push -q origin HEAD:main
  fi
  sleep 60
done
