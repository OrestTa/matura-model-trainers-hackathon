"""The organisers' five-category breakdown of a May 2023 (official mock) result, as on Ania's benchmark site.

    python scripts/deck_breakdown.py results/claude-graded/official_mock/<run>/summary.json [...]

Categories (warsaw-matura-method.ania-olchowik.chatgpt.site, per-model pages; slides 3 and 17-18):
  Closed  = tasks 2.2, 3, 10, 11.2, 13.2, 19, 21                       (11 pts)
  Open    = every other item except 26                                  (34 pts; 29 in their text mode)
  Essay   = task 26                                                     (15 pts)
  Text28  = "originally text only": task groups 2, 6, 11, 12, 16, 22, 23, 25, 26  (13 items, 28 pts)
  Text30  = Text28 + task 10's data table                               (14 items, 30 pts)
Text28/Text30 are subsets of the total, not extra points. Total is /60 with images; the deck's text mode
drops tasks 7, 8 and 15 (5 pts) and is /55, so the script prints both.
Also prints the text/vision split (docs/FINDINGS.md, 1af64b8): open-text, open-vision, closed-text,
closed-vision, essay, where "vision" = the eval row's needs_image flag (data/eval/matura_all.jsonl).
Reads `items[]` with `id`, `max_points` and `claude_points` (or `points`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVALS = [Path(__file__).resolve().parent.parent / "data/eval/matura_all.jsonl",
         Path("/mnt/project-files/data/eval/matura_all.jsonl")]

CLOSED = {"2.2", "3", "10", "11.2", "13.2", "19", "21"}
TEXT_GROUPS = {"2", "6", "11", "12", "16", "22", "23", "25", "26"}
NOT_IN_TEXT_MODE = {"7", "8", "15"}
ORDER = ["closed", "open", "essay", "text28", "text30", "total"]


def categories(item_id: str) -> list[str]:
    group = item_id.split(".")[0]
    cats = ["essay" if item_id == "26" else "closed" if item_id in CLOSED else "open", "total"]
    if group in TEXT_GROUPS:
        cats.append("text28")
    if group in TEXT_GROUPS | {"10"}:
        cats.append("text30")
    return cats


def breakdown(items: list[dict], text_mode: bool = False) -> dict:
    out = {c: [0.0, 0.0] for c in ORDER}
    for it in items:
        if text_mode and it["id"].split(".")[0] in NOT_IN_TEXT_MODE:
            continue
        pts = it.get("claude_points", it.get("points")) or 0
        for c in categories(it["id"]):
            out[c][0] += float(pts)
            out[c][1] += float(it["max_points"])
    return out


CLOSED_KINDS = {"closed_choice", "true_false", "matching"}


def eval_rows(paper: str) -> dict[str, dict]:
    for p in EVALS:
        if p.exists():
            rows = (json.loads(l) for l in open(p, encoding="utf-8") if l.strip())
            return {r["id"].split("-z", 1)[1]: r for r in rows if r.get("paper") == paper}
    return {}


def kind_of(item_id: str, paper: str, rows: dict[str, dict]) -> str:
    """closed/open/essay: the deck's lists for May 2023, the eval row's category for other papers."""
    if paper == "2023-05":
        return categories(item_id)[0]
    cat = rows.get(item_id, {}).get("category")
    return "essay" if cat == "essay" else "closed" if cat in CLOSED_KINDS else "open"


def split(items: list[dict], rows: dict[str, dict], paper: str) -> dict:
    out = {c: [0.0, 0.0] for c in ["open-text", "open-vision", "closed-text", "closed-vision", "essay"]}
    img = {i: bool(r.get("needs_image")) for i, r in rows.items()}
    for it in items:
        kind = kind_of(it["id"], paper, rows)
        c = "essay" if kind == "essay" else f"{kind}-{'vision' if img.get(it['id']) else 'text'}"
        out[c][0] += float(it.get("claude_points", it.get("points")) or 0)
        out[c][1] += float(it["max_points"])
    return out


def fmt(b: dict) -> str:
    return "  ".join(f"{c} {e:g}/{m:g} ({100 * e / m:.1f}%)" for c, (e, m) in b.items() if m)


def main() -> None:
    for path in sys.argv[1:]:
        data = json.load(open(path))
        items, paper = data["items"], data.get("paper", "2023-05")
        rows = eval_rows(paper)
        print(path, paper)
        if paper == "2023-05":
            print("  all items (/60):     ", fmt(breakdown(items)))
            print("  deck text mode (/55):", fmt(breakdown(items, text_mode=True)))
        else:  # the deck's categories exist only for May 2023
            tot = {"closed": [0.0, 0.0], "open": [0.0, 0.0], "essay": [0.0, 0.0], "total": [0.0, 0.0]}
            for it in items:
                for c in (kind_of(it["id"], paper, rows), "total"):
                    tot[c][0] += float(it.get("claude_points", it.get("points")) or 0)
                    tot[c][1] += float(it["max_points"])
            print("  closed/open/essay:   ", fmt(tot))
        if rows:
            print("  text/vision split:   ", fmt(split(items, rows, paper)))


if __name__ == "__main__":
    main()
