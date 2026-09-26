#!/usr/bin/env python3
"""Claude as "master judge" for an organisers-format answers.json (BOT_CHANNEL G-016).

    python scripts/claude_judge_official.py dump results/grok/<run>/answers.json --paper 2023-05 > review.txt
    # Claude reads review.txt and grades every item against the CKE key -> grades.json {"<item id>": points}
    python scripts/claude_judge_official.py score results/grok/<run>/answers.json --paper 2023-05 \
        --grades grades.json --out results/judged/<run>/claude_score.json --model "<model>"

All items are graded against the CKE key (zasady oceniania), the way the organisers' LLM grader does.
The score file also carries scoring.py's auto score for the closed items, for comparison.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from matura_router.scoring import score_row  # noqa: E402

EVALS = [ROOT / "data/eval/matura_all.jsonl", Path("/mnt/project-files/data/eval/matura_all.jsonl")]


def rows_for(paper):
    for p in EVALS:
        if p.exists():
            rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
            return {r["id"].split("-z", 1)[1]: r for r in rows if r.get("paper") == paper}
    sys.exit("no eval set")


def answers(path):
    return {a["id"]: a.get("answer") or "" for a in json.load(open(path, encoding="utf-8"))["answers"]}


def dump(a):
    rows, ans = rows_for(a.paper), answers(a.answers)
    for i, r in rows.items():
        print(f"\n===== {i} [{r['category']}] max {r['points']} auto={score_row(r, ans.get(i, ''))} decision={r.get('decision')}")
        print(f"Q: {r['question'][:900]}\nCTX: {r.get('context', '')[:1500]}")
        print(f"RUBRIC: {r.get('rubric', '')[:1500]}\nGOLD: {r.get('gold', '')[:1200]}")
        print(f"--- ANSWER: {ans.get(i, '')[:6000 if r['category'] == 'essay' else 1800]}")


def score(a):
    rows, ans = rows_for(a.paper), answers(a.answers)
    g = json.load(open(a.grades))
    items, tot, mx = [], 0.0, 0.0
    for i, r in rows.items():
        m = float(r["points"])
        p = max(0.0, min(m, float(g[i])))
        items.append({"id": i, "max_points": m, "claude_points": p, "auto_points": score_row(r, ans.get(i, ""))})
        tot += p
        mx += m
    out = {"answers": a.answers, "paper": a.paper, "model": a.model, "total": tot, "max": mx,
           "pct": round(100 * tot / mx, 1), "judge": "claude (master judge, all items vs CKE zasady oceniania)",
           "judge_kind": "claude", "klucz": a.klucz, "note": a.note, "items": items}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{a.model}: {tot:g}/{mx:g} = {out['pct']}%")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["dump", "score"])
    p.add_argument("answers")
    p.add_argument("--paper", required=True, help="e.g. 2023-05")
    p.add_argument("--grades")
    p.add_argument("--out")
    p.add_argument("--model", default="")
    p.add_argument("--klucz", default="")
    p.add_argument("--note", default="")
    a = p.parse_args()
    dump(a) if a.cmd == "dump" else score(a)
