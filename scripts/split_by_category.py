"""Split a Q&A training set into one chat-format dataset per question type.

Each output file trains one LoRA adapter, and uses the same system prompt the
router sends at inference time.

    python scripts/split_by_category.py data/train.jsonl -o data/by_category

Input rows: {"question": ..., "answer": ..., "context": optional, "category": optional}.
Rows without a category are labelled by the rule classifier; rows it can't place
go to general.jsonl (useful for a base-model or catch-all adapter).
"""

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from matura_router.categories import Category  # noqa: E402
from matura_router.classifier import Classifier  # noqa: E402
from matura_router.prompts import build_messages  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("-o", "--out-dir", default="data/by_category")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clf = Classifier()
    files, counts = {}, collections.Counter()

    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            ctx = row.get("context", "")
            cat = Category(row["category"]) if row.get("category") \
                else clf.classify(row["question"], ctx).category
            msgs = build_messages(cat, row["question"], ctx)
            msgs.append({"role": "assistant", "content": row["answer"]})
            if cat not in files:
                files[cat] = open(out_dir / f"{cat.value}.jsonl", "w", encoding="utf-8")
            files[cat].write(json.dumps({"messages": msgs}, ensure_ascii=False) + "\n")
            counts[cat.value] += 1

    for fh in files.values():
        fh.close()
    print(json.dumps(dict(counts), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
