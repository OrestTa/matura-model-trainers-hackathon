"""Turns past CKE papers with official keys into training items for the adapters.

Real exam items teach the answer format better than synthetic ones. The input is the
full set from `scripts/fetch_matura.py --papers all` (data/eval/matura_all.jsonl); the
headline eval papers (formuła 2023, May 2023-2026) are always left out, so the
headline eval stays clean. Scores on the other papers are no longer a clean eval once
the adapters train on them.

    python scripts/cke_train_items.py data/eval/matura_all.jsonl -o data/train/cke.jsonl
    cat data/train/synthetic.jsonl data/train/cke.jsonl > data/train/all.jsonl

Output rows are {"category", "question", "context", "answer", "source"}, the input
format of scripts/split_by_category.py. Items that need a picture, and keys that are
only a grading scheme, are skipped. Model answers are cleaned into the shape the
router's prompts ask for: "Przykładowe uzasadnienie:" becomes the template's
"Uzasadnienie:", only the first of several alternative answers is kept, and
bracketed optional wording ("[Ignacy] Łukasiewicz") is dropped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.prompts import answer_template  # noqa: E402

HEADLINE_PAPERS = {"2023-05", "2024-05", "2025-05", "2026-05"}
CLOSED = {"closed_choice", "true_false", "matching", "chronology"}


def _first_alternative(body: str) -> str:
    """'•\\nA ... •\\nB ...' -> 'A ...' (keys list several acceptable answers)."""
    parts = [p.strip() for p in re.split(r"(?:^|\n)\s*•\s*", body) if p.strip()]
    return re.sub(r"\s*\n\s*", " ", parts[0]) if parts else ""


def clean_answer(gold: str, question: str) -> str:
    text = re.sub(r"^\s*Przykładow\w+ (rozwiązani\w+|odpowied\w+)\s*:?\s*$", "", gold, flags=re.M | re.I)
    labels = [ln.split("…")[0].rstrip(" :–") for ln in answer_template(question)]
    labels = [lb for lb in labels if lb and lb not in ("•", "-", "–")]
    # "Przykładowe uzasadnienie:" / "Przykładowe wyjaśnienia:" -> the label the sheet uses.
    just = next((lb for lb in labels if lb.lower() != "rozstrzygnięcie"), "Uzasadnienie") \
        if any(lb.lower() == "rozstrzygnięcie" for lb in labels) else None
    text = re.sub(r"Przykładow\w+ (uzasadnie|wyjaśnie)\w*\s*:",
                  lambda m: f"{just or m.group(1).capitalize() + 'nie'}:", text, flags=re.I)
    text = re.sub(r"\s*\[[^\]]{1,120}\]", "", text)  # [optional or alternative wording]
    if labels:
        # Keep one answer per label, in the sheet's order.
        out = []
        for i, lb in enumerate(labels):
            nxt = labels[i + 1] if i + 1 < len(labels) else None
            m = re.search(re.escape(lb) + r"\s*[:–]\s*(.*?)(?=" + (re.escape(nxt) + r"\s*[:–]" if nxt else r"$") + ")",
                          text, flags=re.S)
            if not m:
                return ""
            out.append(f"{lb}{':' if ':' in question.split(lb, 1)[1][:3] else ' –'} {_first_alternative(m.group(1))}")
        return "\n".join(out)
    if "•" in text:
        text = _first_alternative(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def convert(row: dict) -> dict | None:
    if row.get("paper") in HEADLINE_PAPERS or str(row.get("needs_image")) == "True" or row.get("needs_image") is True:
        return None
    cat, gold, q = row.get("category") or "general", row.get("gold") or "", row["question"]
    if cat == "essay" or not gold:
        return None  # essay keys are grading schemes, not model essays
    answer = gold.strip() if cat in CLOSED else clean_answer(gold, q)
    if len(answer) < 1 or len(answer) > 1500 or "pkt" in answer:
        return None
    return {"category": cat, "question": q, "context": row.get("context", ""), "answer": answer,
            "source": f"CKE {row.get('paper')} {row.get('id')}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", default=str(ROOT / "data/eval/matura_all.jsonl"))
    ap.add_argument("-o", "--out", default=str(ROOT / "data/train/cke.jsonl"))
    args = ap.parse_args()
    rows = [json.loads(line) for line in open(args.input, encoding="utf-8") if line.strip()]
    items = [it for it in map(convert, rows) if it]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by = {}
    for it in items:
        by[it["category"]] = by.get(it["category"], 0) + 1
    print(f"{len(items)} of {len(rows)} items -> {args.out}  {by}")


if __name__ == "__main__":
    main()
