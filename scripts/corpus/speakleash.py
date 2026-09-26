#!/usr/bin/env python3
"""Adds SpeakLeash corpora (Polish Wikisource, Wolne Lektury) to the RAG index and DAPT data.

    pip install zstandard
    python scripts/corpus/speakleash.py download              # ~1.1 GB -> data/corpus/speakleash/
    python scripts/corpus/speakleash.py build                 # after plwiki.py build

SpeakLeash (speakleash.org) publishes cleaned Polish corpora as jsonl.zst; the `speakleash`
pip package reads the same URLs. We use two:
- plwikisource (0.96 GB, 632k docs, CC BY-SA 3.0; texts mostly public domain): primary
  sources such as treaties, constitutions, laws, proclamations and chronicles, the kind of
  text the exam quotes in its source-analysis tasks.
- wolne_lektury_corpus (0.12 GB, 6.6k works, CC BY-SA 4.0 or Licencja Wolnej Sztuki):
  school readings with period context.

`build` appends every document's passages to data/rag/plwiki.sqlite (same FTS5 scheme, URL
kept so answers can cite it) and writes the history-scored documents, best first, to
data/dapt/<name>_history.jsonl. Paragraphs sharing an 8-word run with the eval set are
dropped, as in plwiki.py. Only scripts are in the repo, not the data.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plwiki as P  # noqa: E402

ROOT = P.ROOT
BASE = "https://d6t0.c15.e2-2.dev/speakleash-ds-pub/datasets_text"
NAMES = ["plwikisource", "wolne_lektury_corpus"]


def download(out: Path, names):
    out.mkdir(parents=True, exist_ok=True)
    for n in names:
        for ext in (".manifest", ".jsonl.zst"):
            dst = out / (n + ext)
            if dst.exists() and dst.stat().st_size > 1000:
                continue
            print(f"downloading {n}{ext}", flush=True)
            tmp = dst.with_name(dst.name + ".part")
            urllib.request.urlretrieve(f"{BASE}/{n}{ext}", tmp)
            tmp.rename(dst)


def docs(path: Path):
    import zstandard
    with open(path, "rb") as f:
        for line in io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(f),
                                     encoding="utf-8"):
            j = json.loads(line)
            meta = j.get("meta") or {}
            if isinstance(meta, str):
                try:
                    meta = ast.literal_eval(meta)
                except (ValueError, SyntaxError):
                    meta = {}
            yield j.get("text") or "", meta


def build(src: Path, db_path: Path, dapt_dir: Path, eval_path: Path, names, min_score: float):
    sh = P.eval_shingles(eval_path)
    if not db_path.exists():
        sys.exit(f"{db_path} not found: run plwiki.py build first")
    db = sqlite3.connect(db_path)
    db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;")
    pid = db.execute("SELECT max(id) FROM passage").fetchone()[0] or 0
    meta_path = db_path.with_suffix(".meta.json")
    allstats = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for n in names:
        t0 = time.time()
        stats = dict(docs=0, passages=0, dropped_overlap=0)
        hist, rows, frows = [], [], []
        for text, meta in docs(src / f"{n}.jsonl.zst"):
            stats["docs"] += 1
            title = str(meta.get("title") or "").removesuffix("/całość")
            url = meta.get("url") or f"speakleash:{n}"
            keep = []
            for p in (x.strip() for x in text.split("\n")):
                if not p:
                    continue
                if P.overlaps(p, sh):
                    stats["dropped_overlap"] += 1
                else:
                    keep.append(p)
            for ps in P.passages(title, keep):
                pid += 1
                rows.append((pid, title, url, ps))
                frows.append((pid, " ".join(P.norm(title)), " ".join(P.norm(ps))))
            s = P.history_score(title, keep)
            if s >= min_score:
                hist.append((s, title, "\n".join(keep)))
            if len(rows) > 20000:
                db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
                db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
                stats["passages"] += len(rows); rows, frows = [], []
        db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
        db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
        db.commit()
        stats["passages"] += len(rows)
        hist.sort(key=lambda x: -x[0])
        dapt_dir.mkdir(parents=True, exist_ok=True)
        words = 0
        with open(dapt_dir / f"{n}_history.jsonl", "w", encoding="utf-8") as f:
            for s, t, text in hist:
                words += len(text.split())
                f.write(json.dumps({"title": t, "text": f"{t}\n\n{text}", "score": s},
                                   ensure_ascii=False) + "\n")
        stats.update(history_docs=len(hist), history_words=words, seconds=round(time.time() - t0))
        print(n, json.dumps(stats), flush=True)
        allstats[f"speakleash:{n}"] = stats
    print("optimizing index", flush=True)
    db.execute("INSERT INTO fts(fts) VALUES('optimize')")
    db.commit(); db.close()
    allstats["db_gb"] = round(db_path.stat().st_size / 1e9, 2)
    meta_path.write_text(json.dumps(allstats, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download", "build"])
    ap.add_argument("--names", nargs="+", default=NAMES)
    ap.add_argument("--src", default=str(ROOT / "data/corpus/speakleash"))
    ap.add_argument("--db", default=str(ROOT / "data/rag/plwiki.sqlite"))
    ap.add_argument("--dapt-dir", default=str(ROOT / "data/dapt"))
    ap.add_argument("--eval", default=os.environ.get("EVAL", str(ROOT / "data/eval/matura.jsonl")))
    ap.add_argument("--min-score", type=float, default=10.0)
    a = ap.parse_args()
    if a.cmd == "download":
        download(Path(a.src), a.names)
    else:
        build(Path(a.src), Path(a.db), Path(a.dapt_dir), Path(a.eval), a.names, a.min_score)


if __name__ == "__main__":
    main()
