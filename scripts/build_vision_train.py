#!/usr/bin/env python3
"""Picture items from the past papers (not the held-out May 2023-2026) as image+text LoRA data.

    python scripts/build_vision_train.py -o data/train/vision/vision.jsonl
    # rows: {"messages": [...], "images": ["<abs path>", ...], "source": id}

Same prompt the exam path sends in raw mode (build_messages(GENERAL, fill_template=False)),
with the pictures' placeholders pointed at the attached images as router.py does. The answer
is the CKE key in the shape build_train_from_papers.py writes. Messages use TRL's VLM format:
user content = [{"type": "text"}, {"type": "image"} per picture]; train_lora.py --vision loads it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_train_from_papers import answer_for, shingles  # noqa: E402
from matura_router.categories import Category  # noqa: E402
from matura_router.prompts import build_messages  # noqa: E402

PLACEHOLDER = re.compile(r"\[ilustracja – niedostępna w wersji tekstowej\]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(ROOT / "data/eval/matura_all.jsonl"))
    ap.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"))
    ap.add_argument("--image-root", default=str(ROOT), help="images in rows are relative to this")
    ap.add_argument("-o", "--out", default=str(ROOT / "data/train/vision/vision.jsonl"))
    args = ap.parse_args()

    held = [json.loads(l) for l in open(args.eval, encoding="utf-8")]
    held_ids = {r["id"] for r in held}
    from fetch_matura import HEADLINE
    # The picture placeholder and source-URL shingles recur across papers: drop shingles found in
    # 3+ held-out items (boilerplate), so only real shared sources count as overlap.
    from collections import Counter
    per_item = [set().union(*(shingles(r.get(f) or "") for f in ("question", "context"))) for r in held]
    common = {s for s, c in Counter(s for sh in per_item for s in sh).items() if c >= 3}
    held_parts = [(r["id"], sh) for r in held for f in ("question", "context")
                  if len(sh := shingles(r.get(f) or "") - common) >= 5]
    # f15 papers sat on the same May days as the held-out ones and share sources: leave them out.
    held_days = {p.split("-", 1)[1] if p.startswith("f15-") else p for p in HEADLINE}

    kept, skipped = [], {}
    for line in open(args.source, encoding="utf-8"):
        r = json.loads(line)
        why = None
        if r["id"] in held_ids or r.get("paper") in HEADLINE:
            continue
        if r.get("paper", "").startswith("f15-") and r["paper"][4:] in held_days:
            why = "same day as a held-out paper"
        elif not r.get("images") or not r.get("needs_image"):
            continue
        elif r["category"] == "essay":
            why = "essay"
        imgs = [str(Path(args.image_root) / p) for p in r.get("images") or []]
        if not why and not all(Path(p).exists() for p in imgs):
            why = "image missing"
        ans = None if why else answer_for(r)
        if not why and (not ans or r.get("warning")):
            why = "no usable key"
        if not why:
            mine = shingles(r["question"] + " " + r["context"])
            if any(len(sh & mine) / len(sh) > 0.2 for _, sh in held_parts):
                why = "overlaps eval"
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        n = iter(range(1, 1000))
        ctx = PLACEHOLDER.sub(lambda m: f"[ilustracja {next(n)} – obraz dołączony do wiadomości]", r["context"])
        msgs = build_messages(Category.GENERAL, r["question"], ctx, fill_template=False)
        msgs[1]["content"] = [{"type": "text", "text": msgs[1]["content"]}, *({"type": "image"} for _ in imgs)]
        msgs[0]["content"] = [{"type": "text", "text": msgs[0]["content"]}]
        msgs.append({"role": "assistant", "content": [{"type": "text", "text": ans}]})
        kept.append({"messages": msgs, "images": imgs, "source": r["id"], "category": r["category"]})

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for k in kept:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    print(f"{len(kept)} picture items -> {args.out}; skipped {skipped}", file=sys.stderr)


if __name__ == "__main__":
    main()
