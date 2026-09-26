#!/usr/bin/env python3
"""Turns one paper of our eval set into a package in the organisers' exam format, for dress
rehearsals of the exact on-stage path (serve_exam.sh + run_exam.py) before Sunday.

    python scripts/fetch_matura.py --images                      # eval rows with `images`
    python scripts/make_exam_package.py 2023-05 -o work/packages/2023-05
    bash scripts/serve_exam.sh gemma4-12b &
    python scripts/run_exam.py work/packages/2023-05 --model gemma4-12b -o answers.json
    python scripts/grade_batches.py prep answers.json ...        # grade against the CKE key

Writes exam.json (exam_id, instructions, items[id, max_points, question, source_text,
images[path, source_page, sha256], answer_format]), images/*.jpg and answers-template.json.
Item ids follow the paper's numbering ("2.1"). The answer-sheet lines ("Rozstrzygnięcie: …")
stay in the question, as our eval rows have them; `answer_format` is left empty.
CKE content: packages go under work/ (gitignored), never into the repo.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INSTRUCTIONS = ("Egzamin maturalny z historii, poziom rozszerzony. Odpowiedz na każde zadanie po polsku. "
                "W wypracowaniu podaj numer wybranego tematu i napisz co najmniej 300 słów.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paper", help="paper id from the eval set, e.g. 2023-05")
    ap.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"))
    ap.add_argument("-o", "--out", help="default work/packages/<paper>")
    args = ap.parse_args()

    rows = [json.loads(ln) for ln in open(args.eval, encoding="utf-8") if ln.strip()]
    rows = [r for r in rows if r.get("paper") == args.paper]
    if not rows:
        sys.exit(f"no rows for paper {args.paper} in {args.eval}")
    missing = [r["id"] for r in rows if r.get("needs_image") and not r.get("images")]
    if missing:
        print(f"WARNING: {len(missing)} items need a picture but have none "
              f"(build the eval set with fetch_matura.py --images): {missing[:5]}", file=sys.stderr)
    out = Path(args.out or ROOT / "work/packages" / args.paper)
    (out / "images").mkdir(parents=True, exist_ok=True)

    items = []
    for r in rows:
        iid = re.sub(r"^.*-z", "", r["id"])
        imgs = []
        for i, src in enumerate(r.get("images") or [], 1):
            src = Path(src) if Path(src).is_absolute() else ROOT / src
            dst = out / "images" / f"Z{iid}_{i}{src.suffix}"
            shutil.copyfile(src, dst)
            imgs.append({"path": f"images/{dst.name}", "source_page": None,
                         "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})
        items.append({"id": iid, "max_points": r.get("points", 1), "question": r["question"],
                      "source_text": r.get("context", ""), "images": imgs, "answer_format": ""})

    exam = {"exam_id": f"rehearsal-{args.paper}", "instructions": INSTRUCTIONS, "items": items}
    (out / "exam.json").write_text(json.dumps(exam, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "answers-template.json").write_text(json.dumps(
        {"exam_id": exam["exam_id"], "answers": [{"id": it["id"], "answer": ""} for it in items]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: {len(items)} items, {sum(it['max_points'] for it in items)} points, "
          f"{sum(len(it['images']) for it in items)} images", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
