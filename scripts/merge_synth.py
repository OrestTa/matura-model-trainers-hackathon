"""Merges hand-off synthetic training files (gen_synthetic schema) into one clean JSONL.

Checks each row's answer shape per question type, drops duplicates and anything too close to
the eval set (the same shingle filter as gen_synthetic.py), and reports counts:

    python scripts/merge_synth.py parts/*.jsonl --eval data/eval/matura.jsonl -o train_data/claude_synth.jsonl
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from gen_synthetic import shingles  # noqa: E402

SHAPES = {
    "closed_choice": re.compile(r"^[A-F](, ?[A-F])*$"),
    "true_false": re.compile(r"^(\d\. [PF]\n?)+$"),
    "matching": re.compile(r"^(\d – [A-F]\n?)+$"),
    "chronology": re.compile(r"^[A-F](, [A-F])+$"),
}


def ok(r: dict) -> str | None:
    cat = r.get("category")
    if cat not in ("closed_choice", "true_false", "matching", "chronology", "source_analysis",
                   "short_open", "essay"):
        return "category"
    if not str(r.get("question", "")).strip() or not str(r.get("answer", "")).strip():
        return "empty"
    a = r["answer"].strip()
    if cat in SHAPES and not SHAPES[cat].match(a):
        return f"{cat} shape"
    if "Rozstrzygnięcie: …" in r["question"] and not a.startswith("Rozstrzygnięcie:"):
        return "verdict template"
    if cat == "source_analysis" and not str(r.get("context", "")).strip():
        return "no source"
    if cat == "essay" and len(a.split()) < 200:
        return "short essay"
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("parts", nargs="+")
    p.add_argument("--eval", nargs="+", default=[str(ROOT / "data/eval/matura.jsonl")])
    p.add_argument("-o", "--out", required=True)
    args = p.parse_args()
    eval_parts = []
    for ev in args.eval:
        for line in open(ev, encoding="utf-8"):
            e = json.loads(line)
            for field in ("question", "context", "gold"):
                sh = shingles(str(e.get(field) or ""))
                if len(sh) >= 3:
                    eval_parts.append((e.get("id"), sh))
    # Exam boilerplate (the essay instruction "Zadanie zawiera trzy tematy…", command phrases) is in
    # every paper; a synthetic essay that copies it is not a leak. Drop shingles found in 3+ eval items.
    df = collections.Counter(s for i in {i for i, _ in eval_parts}
                             for s in set().union(*(sh for j, sh in eval_parts if j == i)))
    common = {s for s, n in df.items() if n >= 3}
    # Only long parts (essay prompts, source texts) lose the boilerplate; a short question keeps every
    # shingle, or a copied short item slips through (9ff1c3a: 2023-05-z16.2 did).
    eval_parts = [(i, sh - common if len(sh) >= 50 else sh) for i, sh in eval_parts]
    eval_parts = [(i, sh) for i, sh in eval_parts if len(sh) >= 3]
    seen, rows, bad, leaked = set(), [], collections.Counter(), 0
    for part in args.parts:
        for n, line in enumerate(open(part, encoding="utf-8"), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                bad["json"] += 1
                continue
            r = {k: (r.get(k) or "").strip() if isinstance(r.get(k), str) else r.get(k)
                 for k in ("category", "topic", "question", "context", "answer")}
            r["context"] = r["context"] or ""
            why = ok(r)
            if why:
                bad[why] += 1
                continue
            key = re.sub(r"\W+", " ", (r["context"][:200] + r["question"]).lower()).strip()
            if key in seen:
                bad["duplicate"] += 1
                continue
            mine = shingles(" ".join([r["question"], r["context"], r["answer"]]))
            if any(len(sh & mine) / len(sh) > 0.2 for _, sh in eval_parts):
                leaked += 1
                continue
            seen.add(key)
            rows.append(r)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"kept": len(rows), "by_category": collections.Counter(r["category"] for r in rows),
                      "dropped": dict(bad), "too_close_to_eval": leaked}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
