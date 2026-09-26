#!/bin/bash
# Kills llama-server processes that no longer own :8000 (left over after a rehearsal; SIGTERM doesn't stop them).
while true; do
  own=$(ss -ltnp | grep ':8000 ' | grep -o 'pid=[0-9]*' | cut -d= -f2)
  for p in $(pgrep -f /scratch/llama-build/bin/llama-server); do
    [ "$p" = "$own" ] && continue
    age=$(ps -o etimes= -p $p | tr -d ' '); [ "${age:-0}" -gt 90 ] && kill -9 $p && echo "$(date -u +%T) reaped $p" >> /scratch/reaper.log
  done; sleep 20
done
