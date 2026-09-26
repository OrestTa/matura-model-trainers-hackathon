#!/usr/bin/env python3
"""Grades every answer against the CKE key with an LLM, the way the organisers do.

The organisers grade answers.json with an LLM against the CKE key, so judge-free scores
(closed items + keywords) undercount open answers. This splits a run into grading batches
that any LLM grader (a Claude session, or a local judge) fills in, then merges the grades
into one score over ALL items and points.

    python scripts/grade_batches.py prep runs/x/answers.jsonl --out runs/x/grade --size 40
    # grader writes runs/x/grade/batch_NN.grades.json = {"<id>": points, ...} for each batch
    python scripts/grade_batches.py merge runs/x/answers.jsonl --out runs/x/grade

answers.jsonl rows need `id` and `answer` (run_baselines.py and run_exam.py output both work).
"""
import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RULES = """Jesteś egzaminatorem CKE. Oceniasz odpowiedzi z matury z historii (poziom rozszerzony).
Dla każdego zadania przyznaj liczbę punktów od 0 do max_points zgodnie z zasadami oceniania
(rubric) i przykładową odpowiedzią (gold). Uznawaj odpowiedzi merytorycznie poprawne, także
inaczej sformułowane niż w kluczu. Błędne rozstrzygnięcie = 0 pkt za zadanie typu „Rozstrzygnij…”.
Odpowiedź pusta, nie na temat lub nieczytelna = 0 pkt. Połówek nie ma: tylko liczby całkowite.
Zwróć JSON {"<id>": punkty, ...} dla wszystkich zadań w paczce."""


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def prep(args):
    rows = {r["id"]: r for r in load(args.eval)}
    ans = load(args.answers)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for a in ans:
        r = rows[a["id"]]
        items.append({"id": r["id"], "max_points": r.get("points", 1),
                      "question": r["question"], "source_text": (r.get("context") or "")[:2500],
                      "rubric": r.get("rubric", ""), "gold": r.get("gold", ""),
                      "answer": (a.get("answer") or "")[:6000]})
    for i in range(0, len(items), args.size):
        n = i // args.size
        (out / f"batch_{n:02d}.json").write_text(json.dumps(
            {"instructions": RULES, "items": items[i:i + args.size]}, ensure_ascii=False, indent=1))
    print(f"{len(items)} items -> {(len(items) - 1) // args.size + 1} batches in {out}")


def merge(args):
    rows = {r["id"]: r for r in load(args.eval)}
    ans = {a["id"]: a for a in load(args.answers)}
    grades = {}
    for f in sorted(Path(args.out).glob("batch_*.grades.json")):
        grades.update(json.loads(f.read_text()))
    tot = collections.Counter()
    by = collections.defaultdict(collections.Counter)
    missing = []
    for i in ans:
        r = rows[i]
        mx = float(r.get("points", 1))
        if i not in grades:
            missing.append(i)
            continue
        g = max(0.0, min(mx, float(grades[i])))
        for key in ("all", f"paper {r.get('paper')}", f"type {r.get('category')}",
                    "needs_image" if r.get("needs_image") else "text_only"):
            by[key]["earned"] += g
            by[key]["max"] += mx
    summary = {k: {"earned": v["earned"], "max": v["max"],
                   "pct": round(100 * v["earned"] / v["max"], 1) if v["max"] else None}
               for k, v in sorted(by.items())}
    summary["missing"] = missing
    (Path(args.out) / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["prep", "merge"])
    p.add_argument("answers")
    p.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"))
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=40)
    args = p.parse_args()
    prep(args) if args.cmd == "prep" else merge(args)
