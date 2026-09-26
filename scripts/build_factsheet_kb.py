#!/usr/bin/env python3
"""Fact sheets (one Markdown file per era, Claude-written, no CKE key text) -> RAG passages.

    python scripts/build_factsheet_kb.py /mnt/project-files/data/kb/factsheets -o data/kb/factsheets.jsonl

One passage per '###' subsection (or '##' section when it has none), titled with the era and the
section headings, so BM25 retrieves a compact block of dated facts. Use with RAG_PATH (router.py),
alone or next to the Wikipedia passages: RAG_PATH=data/kb/factsheets.jsonl,data/kb/passages.jsonl
"""
import argparse
import json
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("-o", "--out", default="data/kb/factsheets.jsonl")
a = ap.parse_args()
rows = []
for f in sorted(Path(a.src).glob("*.md")):
    era, h2, h3, buf = f.stem, "", "", []

    def flush():
        text = "\n".join(buf).strip()
        if len(text.split()) >= 8:
            rows.append({"id": f"fs-{f.stem}-{len(rows)}", "title": " / ".join(x for x in (era, h2, h3) if x),
                         "text": text})
        buf.clear()

    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            era = line[2:].split(":")[0].strip()
        elif line.startswith("## "):
            flush(); h2, h3 = re.sub(r"^\d+\.\s*", "", line[3:].strip()), ""
        elif line.startswith("### "):
            flush(); h3 = line[4:].strip()
        elif line.strip() and not line.startswith(">"):
            buf.append(line)
    flush()
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
print(f"{len(rows)} passages -> {a.out}")
