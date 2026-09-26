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
Reads `items[]` with `id`, `max_points` and `claude_points` (or `points`).
"""

from __future__ import annotations

import json
import sys

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


def fmt(b: dict) -> str:
    return "  ".join(f"{c} {e:g}/{m:g} ({100 * e / m:.1f}%)" for c, (e, m) in b.items() if m)


def main() -> None:
    for path in sys.argv[1:]:
        items = json.load(open(path))["items"]
        print(path)
        print("  all items (/60):     ", fmt(breakdown(items)))
        print("  deck text mode (/55):", fmt(breakdown(items, text_mode=True)))


if __name__ == "__main__":
    main()
