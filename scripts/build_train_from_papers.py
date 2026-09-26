#!/usr/bin/env python3
"""Turns the past papers that are not in the eval set into LoRA training data.

The headline eval (formuła 2023, May 2023-2026) stays held out. Everything else CKE
published with a key (formuła 2015 May 2015-2024, the 2022 demo paper, the January 2026
mock) becomes real exam-style training data with official answers:

    python scripts/fetch_matura.py --papers all          # -> data/eval/matura_all.jsonl
    python scripts/build_train_from_papers.py            # -> data/train/past_papers.jsonl

Output rows are {"category", "question", "context", "answer", "source"}, the input of
scripts/split_by_category.py, with answers written in the shape the router's prompts ask
for (a letter, "1. P", "1 – B", or the answer-sheet template filled in). Items that need a
picture, essays (the key is a rubric, not an essay) and items without a readable key are
skipped. Items that overlap an eval item (EHIP and MHIP papers sat on the same day share
sources) are dropped by the same shingle check scripts/gen_synthetic.py uses.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.prompts import answer_template  # noqa: E402

HEADER = re.compile(r"^(Przykładow\w*|Poprawn\w*|Prawidłow\w*)\s+(odpowied\w*|rozwiąz\w*|realizacj\w*)\s*:?\s*$|"
                    r"^Rozwiązani[ea]\s*:?\s*$", re.I)
PLURAL_ALTS = re.compile(r"^Przykładowe (uzasadnienia|odpowiedzi|rozwiązania|argumenty|wyjaśnienia)\s*:?\s*$", re.I)


def shingles(s: str, n: int = 5) -> set[str]:
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def debracket(s: str) -> str:
    """'[Ignacy] Łukasiewicz' -> 'Łukasiewicz': square brackets hold optional words or synonyms."""
    return re.sub(r"\s{2,}", " ", re.sub(r"\s*\[[^\]]*\]", "", s)).strip()


def clean_open(gold: str) -> str:
    """The first model answer from a CKE key, without its headers and alternative answers."""
    lines = [ln.strip() for ln in gold.splitlines() if ln.strip()]
    # "•" on its own line followed by the text: join them.
    merged: list[str] = []
    for ln in lines:
        if merged and merged[-1] == "•":
            merged[-1] = "• " + ln
        else:
            merged.append(ln)
    out, alt_mode, took_bullet = [], False, False
    for ln in merged:
        if re.match(r"^(Uwaga|Schemat punktowania|Zasady oceniania)\b", ln):
            break
        if HEADER.match(ln):
            continue
        if PLURAL_ALTS.match(ln):   # a list of alternatives follows: keep the first
            alt_mode, took_bullet = True, False
            out.append(re.sub(r"^Przykładowe \w+", lambda m: {
                "uzasadnienia": "Uzasadnienie", "argumenty": "Argumenty"}.get(m[0].split()[1], ""), ln).strip())
            continue
        m = re.match(r"^Przykładow\w* (\w+)\s*:\s*(.*)$", ln)
        if m:                        # "Przykładowe uzasadnienie: …" -> "Uzasadnienie: …"
            out.append(f"{m[1].capitalize()}: {m[2]}".rstrip())
            alt_mode = False
            continue
        if ln.startswith("•"):
            if alt_mode:
                if took_bullet:
                    continue
                took_bullet = True
                ln = ln.lstrip("• ")
            out.append(ln)
            continue
        if alt_mode and took_bullet and not re.match(r"^[A-ZĄĆĘŁŃÓŚŹŻ][\w ]{0,30}:", ln):
            out[-1] = out[-1] + " " + ln   # continuation of the kept bullet
            continue
        alt_mode = alt_mode and not re.match(r"^[A-ZĄĆĘŁŃÓŚŹŻ][\w ]{0,30}:", ln)
        out.append(ln)
    text = "\n".join(x for x in out if x and x != ":")
    text = re.sub(r"(?m)^(\w+):\n(?!\w+:)", r"\1: ", text)   # "Uzasadnienie:\ntext" -> one line
    # Short one-line answers list alternatives with "/": keep the first.
    if "\n" not in text and len(text) < 90:
        text = re.split(r"\s+/\s+", text)[0]
    return debracket(text)


def answer_for(r: dict) -> str | None:
    cat, gold = r["category"], r.get("gold") or ""
    if cat == "closed_choice":
        if gold:
            return gold
        pairs = [g[0] for g in r.get("gold_keywords") or []]
        return "\n".join(pairs) or None
    if cat == "true_false":
        return "\n".join(f"{i}. {v}" for i, v in enumerate(re.findall(r"[PF]", gold), 1)) or None
    if cat == "chronology":
        return gold or None
    if cat == "matching":
        if gold:
            return "\n".join(p.strip() for p in gold.split(","))
        ref = r.get("reference") or ""
        return debracket(ref) if ref and len(ref) < 400 else None
    if not gold:
        return None
    text = clean_open(gold)
    tmpl = answer_template(r["question"])
    if r.get("decision") and any(t.lower().startswith("rozstrzygnięcie") for t in tmpl):
        why = re.search(r"(?m)^(Uzasadnienie|Wyjaśnienie|Argumenty?)\s*:\s*(.+(?:\n(?![A-ZĄĆĘŁŃÓŚŹŻ]\w*:).+)*)", text)
        if why:
            return f"Rozstrzygnięcie: {debracket(r['decision'])}\nUzasadnienie: {' '.join(why[2].split())}"
    return text or None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / "data/eval/matura_all.jsonl"))
    ap.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"), help="held-out set for the leak check")
    ap.add_argument("-o", "--out", default=str(ROOT / "data/train/past_papers.jsonl"))
    ap.add_argument("--keep-images", action="store_true", help="also keep items that need a picture")
    args = ap.parse_args()

    held = [json.loads(l) for l in open(args.eval, encoding="utf-8")]
    held_ids = {r["id"] for r in held}
    held_parts = [(r["id"], sh) for r in held for f in ("question", "context")
                  if len(sh := shingles(r.get(f) or "")) >= 3]

    stats, kept = Counter(), []
    for line in open(args.source, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] in held_ids:
            continue
        if r["category"] == "essay":
            stats["skip: essay"] += 1
            continue
        if r["needs_image"] and not args.keep_images:
            stats["skip: needs image"] += 1
            continue
        ans = answer_for(r)
        if not ans or r.get("warning"):
            stats["skip: no usable key"] += 1
            continue
        mine = shingles(r["question"] + " " + r["context"])
        hit = next((eid for eid, sh in held_parts if len(sh & mine) / len(sh) > 0.2), None)
        if hit:
            stats["skip: overlaps eval"] += 1
            print(f"dropped {r['id']}: overlaps eval item {hit}", file=sys.stderr)
            continue
        kept.append({"category": r["category"], "question": r["question"], "context": r["context"],
                     "answer": ans, "source": r["id"]})
        stats[f"kept: {r['category']}"] += 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for k in kept:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"{len(kept)} training items -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
