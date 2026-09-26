#!/usr/bin/env python3
"""History slice of the Polish web (FineWeb-2) for continued pretraining and the RAG index.

    pip install pyarrow
    python scripts/corpus/fineweb.py                 # FineWeb2-HQ pol_Latn, 176 shards, 180 GB
    python scripts/corpus/fineweb.py --dataset fineweb2 --workers 3   # full FineWeb-2, 226 GB
    python scripts/corpus/fineweb.py --shards 0-9    # a subset (resumable: done shards skipped)

Sources (both ODC-By 1.0, Common Crawl text; we keep URLs so every document is attributable):
- `epfml/FineWeb2-HQ`, pol_Latn: the top ~10% of FineWeb-2 by a quality classifier.
  Each 1.1 GB shard is mostly embeddings; the text is ~80k documents.
- `HuggingFaceFW/fineweb-2`, data/pol_Latn/train: everything, 55 shards of 4.8 GB.

Each shard is downloaded, filtered and deleted, so disk use stays at a few GB. A vectorised
regex (pyarrow) keeps documents with at least 8 history-word hits, then plwiki.py's
history_score ranks them; documents under --min-score, Wikipedia mirrors and paragraphs
sharing an 8-word run with the eval set are dropped. One shard takes ~15 s to download and
~7 s to filter, and yields ~900 documents / ~2M words of history text on FineWeb2-HQ.

Outputs: data/corpus/fineweb/<dataset>/<shard>.jsonl per shard, then (after all shards)
data/dapt/<dataset>_history.jsonl ({"title", "url", "text", "score"}, best first) for
scripts/train_dapt.py; `--rag` also appends the passages to data/rag/plwiki.sqlite.
Only this script is in the repo, not the data.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plwiki as P  # noqa: E402

ROOT = P.ROOT
DATASETS = {  # repo, directory
    "fineweb2hq": ("epfml/FineWeb2-HQ", "pol_Latn"),
    "fineweb2": ("HuggingFaceFW/fineweb-2", "data/pol_Latn/train"),
}


def shard_names(repo: str, path: str) -> list[str]:
    url = f"https://huggingface.co/api/datasets/{repo}/tree/main/{path}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return sorted(x["path"].rsplit("/", 1)[-1] for x in json.load(r)
                      if x["path"].endswith(".parquet"))
PREFILTER = (r"\b(wojn|bitw|król|cesarz|powstani|traktat|sejm|szlacht|rozbior|zabor|okupacj|"
             r"rewolucj|dynasti|średniow|starożyt|konstytucj|hetman|piastow|jagiell|prl\b|sanacj|"
             r"legion|insurekcj|konfederacj|pańszczyzn|reformacj)")
SKIP_URL = ("wikipedia.org", "wikiwand.com", "wiki2.org", "wikizero",
            # Exam papers and answer keys (paraphrased keys slip past the 8-word overlap check
            # and would make the eval score look better than the model is).
            "cke.gov.pl", "oke.", "arkusze.pl", "matur")
# A page about the matura that also carries answers/keys: skip it whatever the site.
EXAM_PAGE = re.compile(r"matur\w*.{0,300}(klucz|odpowied|rozwiązan|arkusz|zasady oceniania)|"
                       r"(klucz|odpowied|rozwiązan|arkusz|zasady oceniania).{0,300}matur", re.I | re.S)

_SH = None


def _init(eval_path):
    global _SH
    _SH = P.eval_shingles(Path(eval_path))


def shard(args):
    base, name, out_dir, tmp_dir, min_score, min_hits = args
    out = Path(out_dir) / (name.replace(".parquet", ".jsonl"))
    if out.exists():
        return name, "skip", 0, 0
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    t0 = time.time()
    tmp = Path(tmp_dir) / name
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(f"{base}/{name}", tmp)
            break
        except Exception as e:  # noqa: BLE001 - network hiccups: retry with backoff
            if attempt == 3:
                return name, f"download failed: {e}", 0, 0
            time.sleep(2 ** (attempt + 1))
    try:
        t = pq.read_table(tmp, columns=["text", "url"])
    finally:
        tmp.unlink(missing_ok=True)
    hits = pc.count_substring_regex(pc.utf8_lower(t["text"]), PREFILTER)
    cand = t.filter(pc.greater_equal(hits, min_hits))
    rows = []
    for text, url in zip(cand["text"].to_pylist(), cand["url"].to_pylist()):
        if any(s in (url or "") for s in SKIP_URL) or EXAM_PAGE.search(text):
            continue
        pars = [p.strip() for p in text.split("\n") if p.strip() and not P.overlaps(p, _SH)]
        s = P.history_score("", pars)
        if s >= min_score:
            title = pars[0][:120] if pars else ""
            rows.append({"title": title, "url": url, "text": "\n".join(pars), "score": s})
    rows.sort(key=lambda r: -r["score"])
    part = out.with_suffix(".part")
    with open(part, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    part.rename(out)
    return name, f"{time.time() - t0:.0f}s", len(rows), sum(len(r["text"].split()) for r in rows)


def merge(out_dir: Path, dst: Path):
    """All shard files -> one file, best first."""
    rows = []
    for f in sorted(out_dir.glob("*.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            rows.append((r["score"], line))
    rows.sort(key=lambda x: -x[0])
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        for _, line in rows:
            f.write(line)
    return len(rows)


def add_to_rag(src: Path, db_path: Path, min_score: float):
    db = sqlite3.connect(db_path)
    db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;")
    pid = db.execute("SELECT max(id) FROM passage").fetchone()[0] or 0
    rows, frows, n = [], [], 0
    for line in open(src, encoding="utf-8"):
        r = json.loads(line)
        if r["score"] < min_score:
            break  # file is sorted, best first
        for ps in P.passages(r["title"], r["text"].split("\n")):
            pid += 1; n += 1
            rows.append((pid, r["title"], r["url"], ps))
            frows.append((pid, " ".join(P.norm(r["title"])), " ".join(P.norm(ps))))
        if len(rows) > 20000:
            db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
            db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
            rows, frows = [], []
    db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
    db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
    db.execute("INSERT INTO fts(fts) VALUES('optimize')")
    db.commit(); db.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=list(DATASETS), default="fineweb2hq")
    ap.add_argument("--shards", default="", help="e.g. 0-9 (default: all)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "data/corpus/fineweb"))
    ap.add_argument("--tmp", default=str(ROOT / "data/corpus/fineweb/tmp"))
    ap.add_argument("--dapt-dir", default=str(ROOT / "data/dapt"))
    ap.add_argument("--eval", default=os.environ.get("EVAL", str(ROOT / "data/eval/matura.jsonl")))
    ap.add_argument("--min-score", type=float, default=10.0)
    ap.add_argument("--min-hits", type=int, default=8)
    ap.add_argument("--rag", action="store_true", help="also add docs to the RAG index")
    ap.add_argument("--rag-min-score", type=float, default=15.0)
    ap.add_argument("--db", default=str(ROOT / "data/rag/plwiki.sqlite"))
    a = ap.parse_args()
    repo, path = DATASETS[a.dataset]
    base = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    names = shard_names(repo, path)
    if a.shards:
        lo, _, hi = a.shards.partition("-")
        names = names[int(lo):int(hi or lo) + 1]
    out_dir = Path(a.out) / a.dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    Path(a.tmp).mkdir(parents=True, exist_ok=True)
    P.eval_shingles(Path(a.eval))  # fail early without the eval set
    jobs = [(base, n, str(out_dir), a.tmp, a.min_score, a.min_hits) for n in names]
    docs = words = 0
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a.eval,)) as ex:
        for name, msg, d, w in ex.map(shard, jobs):
            docs += d; words += w
            print(f"{name}: {msg}, {d} docs, {w:,} words (run total {docs} docs, {words:,} words)",
                  flush=True)
    dst = Path(a.dapt_dir) / f"{a.dataset}_history.jsonl"
    print(f"merged {merge(out_dir, dst)} docs -> {dst}", flush=True)
    if a.rag:
        print(f"added {add_to_rag(dst, Path(a.db), a.rag_min_score)} passages to {a.db}")


if __name__ == "__main__":
    main()
