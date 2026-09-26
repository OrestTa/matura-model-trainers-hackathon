#!/usr/bin/env python3
"""Picks each subtype's setup from graded sweep runs, and prints per-subtype score tables.

    python scripts/subtype_select.py select results/subtype/subtype-dev-*   # -> configs/subtypes.yaml
    python scripts/subtype_select.py table  results/subtype/subtype-heldout-*

Reads <run>/<group>/<candidate>/answers.claude.jsonl (scripts/claude_grade.py merge), else
answers.jsonl, from every run dir given (shards of one sweep are pooled). A candidate's score
is its earned points over the max points of its subtype's items; unscored rows count as 0 and are
reported, so grade everything first. `select` keeps a candidate only when it was scored on every
item of its subtype and beats `base` by more than --margin points (%-points of the subtype's max),
so noise on a small subtype (the essay has 12 dev items) doesn't flip the setup; ties keep `base`.
`table` compares raw, base (routed) and the chosen setups (group "selected") per subtype.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from matura_router.subtypes import SUBTYPES  # noqa: E402


def collect(run_dirs):
    """{(group, candidate): {item id: row}}; graded files win over ungraded ones."""
    out = defaultdict(dict)
    for d in run_dirs:
        for f in sorted(Path(d).rglob("answers.jsonl")):
            graded = f.with_name("answers.claude.jsonl")
            src = graded if graded.exists() else f
            key = (f.parent.parent.name, f.parent.name)
            for line in open(src, encoding="utf-8"):
                if line.strip():
                    r = json.loads(line)
                    out[key][str(r["id"])] = r
    return out


def score(rows):
    earned = sum(r["score"] or 0 for r in rows)
    mx = sum(r["points"] for r in rows)
    unscored = sum(1 for r in rows if r["score"] is None)
    return earned, mx, unscored


def by_subtype(rows):
    d = defaultdict(list)
    for r in rows.values():
        d[r["subtype"]].append(r)
    return d


def lat(rows):
    """Median and max seconds per answer (on the sweep's GPU, all slots busy: an upper bound for stage)."""
    xs = sorted(r.get("latency_s") or 0 for r in rows)
    return (xs[len(xs) // 2], xs[-1]) if xs else (0, 0)


def fmt(e, m, u=0):
    s = f"{e:g}/{m:g} = {100 * e / m:.1f}%" if m else "–"
    return s + (f" ({u} ungraded)" if u else "")


def select(args):
    runs = collect(args.runs)
    grid = yaml.safe_load(Path(args.grid).read_text())
    chosen, lines = {}, []
    for st in SUBTYPES:
        cands = {name: rows for (g, name), rows in runs.items() if g == st}
        if "base" not in cands:
            print(f"{st}: no base run, keeping base")
            chosen[st] = {"name": "base"}
            continue
        n_items = len(cands["base"])
        res = {}
        for name, rows in cands.items():
            e, m, u = score(list(rows.values()))
            res[name] = (e, m, u, len(rows))
        be, bm, _, _ = res["base"]
        best = "base"
        for name, (e, m, u, n) in sorted(res.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1)):
            if name == "base" or u or n < n_items:
                continue
            if 100 * (e / m - be / bm) > args.margin and (best == "base" or e / m > res[best][0] / res[best][1]):
                best = name
        chosen[st] = {"name": best, **(grid.get(st, {}).get(best) or {})}
        lines.append(f"## {st} ({n_items} dev items)")
        for name, (e, m, u, n) in sorted(res.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1)):
            p50, mx = lat(list(cands[name].values()))
            lines.append(f"- {name}{' **chosen**' if name == best else ''}: {fmt(e, m, u)}, {p50:.0f}s median / {mx:.0f}s max per answer"
                         + (f", only {n}/{n_items} items" if n < n_items else ""))
    report = "\n".join(lines)
    print(report)
    if args.write:
        head = ("# Per-subtype setups for `--mode subtype` (matura_router/subtypes.py), chosen on the dev\n"
                "# papers (not the held-out May 2023-2026) by scripts/subtype_select.py from the\n"
                f"# configs/subtype_grid.yaml sweep in {', '.join(map(str, args.runs))}, margin {args.margin} pts.\n")
        Path(args.write).write_text(head + yaml.safe_dump({"subtypes": chosen}, allow_unicode=True,
                                                           sort_keys=False, width=200))
        print(f"-> {args.write}")


def table(args):
    runs = collect(args.runs)
    groups = [k for k in (("raw", "raw"), ("selected", "selected")) if k in runs]
    base = {st: runs[(st, "base")] for st in SUBTYPES if (st, "base") in runs}
    cols = ["raw"] + (["base (routed)"] if base else []) + (["per-subtype"] if ("selected", "selected") in runs else [])
    print("| subtype | items | " + " | ".join(cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    tot = defaultdict(lambda: [0.0, 0.0, 0])
    raw_by = by_subtype(runs.get(("raw", "raw"), {}))
    sel_by = by_subtype(runs.get(("selected", "selected"), {}))
    for st in SUBTYPES:
        cells = []
        for col, rows in (("raw", raw_by.get(st, [])), ("base (routed)", list(base.get(st, {}).values())),
                          ("per-subtype", sel_by.get(st, []))):
            if col not in cols:
                continue
            e, m, u = score(rows)
            t = tot[col]
            t[0] += e; t[1] += m; t[2] += u
            cells.append(fmt(e, m, u))
        n = len(raw_by.get(st, []) or base.get(st, {}))
        print(f"| {st} | {n} | " + " | ".join(cells) + " |")
    print("| **total** | | " + " | ".join(f"**{fmt(*tot[c])}**" for c in cols) + " |")
    _ = groups


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["select", "table"])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--grid", default=str(ROOT / "configs/subtype_grid.yaml"))
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--write", help="select: write the chosen setups here (e.g. configs/subtypes.yaml)")
    a = ap.parse_args()
    select(a) if a.cmd == "select" else table(a)
