#!/usr/bin/env python3
"""Ania's deck vs our Claude-graded May 2023 results, per deck category (Orest, 20:12 CEST).

    python scripts/deck_compare.py --deck gemma-4-12b base=<claude_score.json> optimised=<claude_score.json> ...

Prints a markdown table: rows = the deck's five categories + total, columns = the deck's number, then each
labelled run with its delta vs the deck. Only May 2023 is in the deck; other papers have no deck column.
Deck numbers are from warsaw-matura-method.ania-olchowik.chatgpt.site (per-model pages, 22 Sep 2026).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_breakdown import breakdown  # noqa: E402

# earned points per category; image mode is /60, text mode /55 (tasks 7, 8, 15 dropped)
DECK = {
    # gemma-4-12b-vision.html: bf16, original page images, up to 8,192 thinking tokens (16,384 essay)
    # no text-mode (/55) run of Gemma 4 12B in the deck
    "gemma-4-12b": {"mode": "images /60", "closed": 10, "open": 24, "essay": 12, "text28": 24, "text30": 26, "total": 46,
                    "text55": None},
    # bielik-4-5b page: text mode /55
    "bielik-4.5b": {"mode": "text /55", "closed": 6, "open": 15, "essay": 2, "text28": 12, "text30": 14, "total": 23,
                    "text55": 23},
}
ROWS = [("closed", "Closed /11"), ("open", "Open /34"), ("essay", "Essay /15"),
        ("text28", "Text-only /28"), ("text30", "Text + table /30"), ("total", "Total /60")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True, choices=sorted(DECK))
    ap.add_argument("runs", nargs="+", help="label=path/to/claude_score.json (May 2023)")
    a = ap.parse_args()
    deck = DECK[a.deck]
    text_mode = deck["mode"].startswith("text")
    runs = []
    for spec in a.runs:
        label, path = spec.split("=", 1)
        items = json.load(open(path))["items"]
        runs.append((label, breakdown(items, text_mode=text_mode)))
    head = ["Category", f"Deck ({deck['mode']})"] + [f"{l}" for l, _ in runs]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for key, name in ROWS:
        if text_mode:
            name = name.replace("/34", "/29").replace("/60", "/55")
        cells = [name, f"{deck[key]:g}"]
        for _, b in runs:
            e = b[key][0]
            cells.append(f"{e:g} ({e - deck[key]:+g})")
        print("| " + " | ".join(cells) + " |")
    if not text_mode:
        # The deck's text mode is a separate run: pictures replaced by written descriptions, tasks 7, 8, 15
        # dropped. Ours here is only the same 34 items cut out of the picture run, so it is not the same run.
        d = deck.get("text55")
        cells = ["Text mode /55 (ours: picture run minus 7, 8, 15)", "not in deck" if d is None else f"{d:g}"]
        for label, _ in runs:
            items = json.load(open(dict(r.split("=", 1) for r in a.runs)[label]))["items"]
            e = breakdown(items, text_mode=True)["total"][0]
            cells.append(f"{e:g}" if d is None else f"{e:g} ({e - d:+g})")
        print("| " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
