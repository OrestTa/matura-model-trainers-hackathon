#!/usr/bin/env python3
"""Held-out report of the per-subtype harness: raw vs routed base vs the dev-chosen setups.

    python scripts/subtype_report.py results/subtype/heldout --subtypes configs/subtypes.yaml

Reads a graded sweep (<run>/<group>/<candidate>/answers.claude.jsonl, scripts/claude_grade.py merge) that ran
every candidate on the held-out papers, and assembles three submissions item by item: `raw` (the plain
single-prompt model), `base` (each item's subtype run with the plain think setup) and `optimised` (each item's
subtype run with the setup configs/subtypes.yaml chose on the dev papers). The choice was made on dev only;
this run just evaluates it. Prints the per-subtype table, per-paper totals, and the deck's five categories for
May 2023 (scripts/deck_breakdown.py).
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from matura_router.subtypes import SUBTYPES  # noqa: E402
from deck_breakdown import ORDER, breakdown  # noqa: E402
from subtype_select import collect, fmt  # noqa: E402

DECK_2023 = {"closed": 10, "open": 24, "essay": 12, "text28": 24, "text30": 26, "total": 46}  # Gemma 4 12B bf16
LABELS = {"closed": "Closed /11", "open": "Open /34", "essay": "Essay /15", "text28": "Text-only /28",
          "text30": "Text + table /30", "total": "Total /60"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--subtypes", default=str(ROOT / "configs/subtypes.yaml"))
    a = ap.parse_args()
    runs = collect(a.runs)
    chosen = {k: v.get("name", "base") for k, v in yaml.safe_load(Path(a.subtypes).read_text())["subtypes"].items()}
    raw = runs.get(("raw", "raw"), {})
    sub = {}  # item id -> subtype, from any subtype run
    for (g, _), rows in runs.items():
        if g in SUBTYPES:
            for i in rows:
                sub[i] = g
    ids = sorted(set(raw) | set(sub))
    subs = {"raw": {}, "base": {}, "optimised": {}}
    for i in ids:
        st = sub.get(i) or raw.get(i, {}).get("subtype")
        subs["raw"][i] = raw.get(i)
        subs["base"][i] = runs.get((st, "base"), {}).get(i)
        subs["optimised"][i] = runs.get((st, chosen.get(st, "base")), {}).get(i)
    for k in subs:  # an item a crashed shard never answered is shown as missing, not as 0
        subs[k] = {i: r for i, r in subs[k].items() if r is not None}

    print("chosen on dev:", chosen)
    print("\n| subtype | items | raw | base (think) | optimised | setup |")
    print("|---|---|---|---|---|---|")
    tot = defaultdict(lambda: [0.0, 0.0, 0, 0])
    for st in SUBTYPES:
        its = [i for i in ids if sub.get(i) == st]
        cells = []
        for k in subs:
            rows = [subs[k][i] for i in its if i in subs[k]]
            e = sum(r.get("score") or 0 for r in rows)
            m = sum(r["points"] for r in rows)
            u = sum(1 for r in rows if r.get("score") is None) + (len(its) - len(rows))
            t = tot[k]
            t[0] += e; t[1] += m; t[2] += u
            cells.append(fmt(e, m) + (f" ({len(its) - len(rows)} missing)" if len(rows) < len(its) else ""))
        print(f"| {st} | {len(its)} | " + " | ".join(cells) + f" | {chosen.get(st, 'base')} |")
    print("| **total** | {} | ".format(len(ids)) + " | ".join(f"**{fmt(tot[k][0], tot[k][1])}**" for k in subs) + " | |")

    print("\n| paper | " + " | ".join(subs) + " |\n|---|" + "---|" * len(subs))
    for p in sorted({i.rsplit("-z", 1)[0] for i in ids}):
        cells = []
        for k in subs:
            rows = [r for i, r in subs[k].items() if i.rsplit("-z", 1)[0] == p]
            cells.append(f"{sum(r.get('score') or 0 for r in rows):g}/{sum(r['points'] for r in rows):g}")
        print(f"| {p} | " + " | ".join(cells) + " |")

    print("\nMay 2023 in the deck's categories (deck = Ania's Gemma 4 12B bf16, images, 8k/16k thinking):")
    print("| category | deck | " + " | ".join(f"{k} (Δ deck)" for k in subs) + " |\n|---|---|" + "---|" * len(subs))
    bd = {}
    for k in subs:
        items = [{"id": i.split("-z", 1)[1], "max_points": r["points"], "points": r.get("score") or 0}
                 for i, r in subs[k].items() if i.startswith("2023-05-z")]
        bd[k] = breakdown(items)
    for c in ORDER:
        cells = [f"{bd[k][c][0]:g}/{bd[k][c][1]:g} ({bd[k][c][0] - DECK_2023[c]:+g})" for k in subs]
        print(f"| {LABELS[c]} | {DECK_2023[c]} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
