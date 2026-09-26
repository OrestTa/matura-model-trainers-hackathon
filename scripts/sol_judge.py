#!/usr/bin/env python3
"""Second-opinion grade from Forgehand's hosted LLM (OpenAI-compatible), same klucz as the Claude grade.

    export SOL_BASE=https://<forgehand host>/api/v1/teams/<team id>/llm/v1   # never commit these
    export SOL_TOKEN=...                                                   # Forgehand token
    python scripts/sol_judge.py models                                     # list model ids
    python scripts/sol_judge.py grade <answers.json|answers.jsonl> --paper 2023-05 \
        --model <id> --out results/judged/<run>/<paper>/sol_score.json [--claude <claude_score.json>]

Every item (closed ones too) is graded with matura_router.scoring.JUDGE_PROMPT: the question with its
sources, the CKE zasady oceniania and the klucz's model answer. The output has the same shape as
claude_score.json (points under "sol_points"), so scripts/deck_breakdown.py reads it. With --claude it
also prints the items where the two judges differ by 2 or more points.
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from matura_router.scoring import JUDGE_PROMPT  # noqa: E402
from claude_judge_official import answers, rows_for  # noqa: E402


def api(path, **kw):
    base, tok = os.environ["SOL_BASE"].rstrip("/"), os.environ["SOL_TOKEN"]
    h = {"Authorization": f"Bearer {tok}"}
    if kw:
        r = requests.post(base + path, headers=h, json=kw, timeout=600)
    else:
        r = requests.get(base + path, headers=h, timeout=60)
    r.raise_for_status()
    return r.json()


def grade_one(model, row, answer):
    pts = int(float(row["points"]))
    if not answer.strip():
        return 0, "empty"
    q = row["question"]
    if row.get("context"):
        q = f"{row['context'][:4000]}\n\n{q}"
    prompt = JUDGE_PROMPT.format(question=q, rubric=row.get("rubric") or "", gold=row.get("gold") or "",
                                 answer=answer[:8000], points=pts)
    for attempt in range(3):
        try:
            out = api("/chat/completions", model=model, max_completion_tokens=4000,  # gpt-6 on Azure: no temperature/max_tokens
                      messages=[{"role": "user", "content": prompt}])
            text = out["choices"][0]["message"]["content"] or ""
            nums = re.findall(r"\d+", text.strip().splitlines()[-1] if text.strip() else "")
            if nums:
                return max(0, min(pts, int(nums[-1]))), text[-200:]
        except Exception as e:  # noqa: BLE001
            text = re.sub(r"https?://\S+", "<url>", str(e))  # never write the team id
        time.sleep(2 * (attempt + 1))
    return None, text[-200:]


def grade(a):
    rows, ans = rows_for(a.paper), answers(a.answers, a.paper)
    with ThreadPoolExecutor(a.workers) as ex:
        res = dict(zip(rows, ex.map(lambda i: grade_one(a.model, rows[i], ans.get(i, "")), rows)))
    items, tot, mx, failed = [], 0.0, 0.0, []
    for i, r in rows.items():
        p, raw = res[i]
        if p is None:
            failed.append(i)
            p = 0
        items.append({"id": i, "max_points": float(r["points"]), "sol_points": float(p), "points": float(p),
                      "raw": raw})
        tot += p
        mx += float(r["points"])
    out = {"answers": a.answers, "paper": a.paper, "judge": f"forgehand {a.model}", "judge_kind": "sol",
           "total": tot, "max": mx, "pct": round(100 * tot / mx, 1), "failed": failed, "items": items}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"sol {a.model} {a.paper}: {tot:g}/{mx:g} = {out['pct']}%" + (f" ({len(failed)} failed)" if failed else ""))
    if a.claude:
        c = {it["id"]: it["claude_points"] for it in json.load(open(a.claude))["items"]}
        for it in items:
            if abs(it["sol_points"] - c.get(it["id"], 0)) >= 2:
                print(f"  disagree {it['id']}: claude {c.get(it['id']):g} vs sol {it['sol_points']:g}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["models", "grade"])
    ap.add_argument("answers", nargs="?")
    ap.add_argument("--paper")
    ap.add_argument("--model")
    ap.add_argument("--out")
    ap.add_argument("--claude")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "models":
        print(json.dumps([m["id"] for m in api("/models").get("data", [])], indent=1))
    else:
        grade(a)
