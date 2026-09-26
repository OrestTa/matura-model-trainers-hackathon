#!/usr/bin/env bash
# Smoke-tests our own keys for the extra compute venues and Tavily. Prints OK/FAIL per venue, never a secret.
#   SOLARI_API_KEY                    Solari (console.getsolari.com), CPU sandboxes: infra/solari/sol_job.py
#   NEBIUS_API_KEY                    Nebius Token Factory (OpenAI-compatible): base_url below
#   NEBIUS_SERVICE_ACCOUNT_ID, NEBIUS_PUBLIC_KEY_ID, NEBIUS_PRIVATE_KEY_B64, NEBIUS_PROJECT_ID
#                                     Nebius Console GPU jobs: infra/nebius/nb_job.py
#   TAVILY_API_KEY                    Tavily web search, only for building the offline RAG corpus (no web in the exam)
# Env vars live in Project settings > environment; a session sees them only if it started after they were set.
set -u
TF_BASE=${TF_BASE:-https://api.tokenfactory.nebius.com/v1}

echo "== Solari"
if [ -n "${SOLARI_API_KEY:-}" ]; then
  code=$(curl -sS -o /tmp/sol.json -w '%{http_code}' -H "Authorization: Bearer $SOLARI_API_KEY" https://api.getsolari.com/sandboxes)
  echo "HTTP $code; sandboxes listed: $(python3 -c 'import json;d=json.load(open("/tmp/sol.json"));d=d.get("data",d) if isinstance(d,dict) else d;print(len(d))' 2>/dev/null || echo '?')"
else echo "FAIL: SOLARI_API_KEY not set"; fi

echo "== Nebius Token Factory"
if [ -n "${NEBIUS_API_KEY:-}" ]; then
  curl -sS -H "Authorization: Bearer $NEBIUS_API_KEY" "$TF_BASE/models" \
    | python3 -c 'import json,sys;m=[x["id"] for x in json.load(sys.stdin)["data"]];print(len(m),"models;",", ".join(x for x in m if "gemma" in x.lower() or "bielik" in x.lower() or "qwen" in x.lower())[:400])' \
    || echo "FAIL: /models"
  curl -sS "$TF_BASE/chat/completions" -H "Authorization: Bearer $NEBIUS_API_KEY" -H 'Content-Type: application/json' \
    -d '{"model":"google/gemma-3-27b-it","max_tokens":20,"messages":[{"role":"user","content":"W którym roku była bitwa pod Grunwaldem? Odpowiedz liczbą."}]}' \
    | python3 -c 'import json,sys;d=json.load(sys.stdin);print("chat:",d["choices"][0]["message"]["content"].strip())' || echo "FAIL: chat"
else echo "FAIL: NEBIUS_API_KEY not set"; fi

echo "== Nebius Console"
if [ -n "${NEBIUS_SERVICE_ACCOUNT_ID:-}" ] && [ -n "${NEBIUS_PRIVATE_KEY_B64:-}" ]; then
  python3 "$(dirname "$0")/nebius/nb_job.py" setup && ~/.nebius/bin/nebius ai job list --parent-id "$NEBIUS_PROJECT_ID" --format json \
    | python3 -c 'import json,sys;d=json.load(sys.stdin).get("items",[]);print(len(d),"AI jobs visible:");[print(" ",j["metadata"].get("name"),j.get("status",{}).get("state")) for j in d]'
else echo "FAIL: NEBIUS_SERVICE_ACCOUNT_ID / NEBIUS_PRIVATE_KEY_B64 not set"; fi

echo "== Tavily"
if [ -n "${TAVILY_API_KEY:-}" ]; then
  curl -sS https://api.tavily.com/search -H "Authorization: Bearer $TAVILY_API_KEY" -H 'Content-Type: application/json' \
    -d '{"query":"bitwa pod Grunwaldem 1410","max_results":2}' \
    | python3 -c 'import json,sys;r=json.load(sys.stdin)["results"];print(len(r),"results:",", ".join(x["url"] for x in r))' || echo "FAIL: search"
else echo "FAIL: TAVILY_API_KEY not set"; fi
