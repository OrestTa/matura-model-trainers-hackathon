#!/usr/bin/env python3
"""Polish Wikipedia -> offline RAG index + history slice for continued pretraining (DAPT).

    pip install pyarrow
    python scripts/corpus/plwiki.py download            # 1.8 GB parquet -> data/corpus/plwiki/
    python scripts/corpus/plwiki.py build               # both outputs below
    python scripts/corpus/plwiki.py search "unia lubelska 1569"

Source: Hugging Face `wikimedia/wikipedia`, config 20231101.pl (1.6M articles, plain text,
CC BY-SA 4.0 / GFDL). Only this script is in the repo; the data is not.

Outputs (both under data/, gitignored):
- data/rag/plwiki.sqlite: every article split into ~150-word passages, with an SQLite FTS5
  index. Stdlib only at query time (sqlite3), no GPU, no internet: this is the exam-day
  knowledge base. It sits beside the model and does not count toward the 8 GB model limit.
  Polish inflects heavily, so the index holds 6-letter word prefixes ("powstania" and
  "powstaniu" both become "powsta"), and queries are prefixed the same way.
- data/dapt/plwiki_history.jsonl: history articles ({"title", "text", "score"}), best first,
  for scripts/train_dapt.py (which takes the top N tokens). Ranked by density and variety of
  history vocabulary plus pre-1990 years; village stubs, sport, music, biology, lists and
  year/day pages are dropped.

Both drop every paragraph that shares an 8-word run with the eval set
(data/eval/matura.jsonl: question, context and gold of each item), so scores on the
2023-2026 papers stay honest. Counts go to data/rag/plwiki.meta.json.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HF = "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.pl"
SHARDS = [f"train-{i:05d}-of-00006.parquet" for i in range(6)]

WORD = re.compile(r"\w+", re.U)
PREFIX = 6

# History vocabulary as 6-letter prefixes (same normalisation as the index).
HIST = """wojna wojny wojen bitwa bitwy bitwie powstanie powstania król króla królem królestwo
cesarz cesarstwo imperium dynastia dynastii panowanie panowania traktat traktatu pokoju sejmu
sejm szlachta szlachty rozbiór rozbioru zabór zaboru zaborów okupacja okupacji rewolucja
rewolucji reformacja reformacji średniowiecze średniowieczu starożytność starożytnej
konstytucja konstytucji hetman hetmana książę księcia księstwo papież papieża biskup
kościoła krucjata zakon zakonu rzeczpospolita rzeczypospolitej sanacja sanacji komunistyczna
komunistycznej partia partii polityczny polityki armia armii wojsko wojska wojskowy legiony
legionów piłsudski piastów jagiellonów wazów sasów napoleon hitler stalin ii_wojna niepodległość niepodległości emigracja
kolonia kolonii kolonialny feudalny senat senatu republika republiki monarchia monarchii
unia unii konfederacja konfederacji insurekcja rokosz elekcja elekcji wolna ustawa ustawy
przywilej przywileju magnateria chłopi chłopów pańszczyzna uwłaszczenie industrializacja
faszyzm nazizm totalitaryzm holokaust getto obóz obozu deportacja solidarność prl stalinizm
odwilż strajk strajku stan_wojenny opozycja opozycji""".split()
HIST = {w[:PREFIX] for w in HIST if "_" not in w}

# Pages that are full of years but are not history.
NOISE = re.compile(
    r"piłkar|sezon[ uie]|album|singl|utw[oó]r muzyczny|gatunek (ro[sś]lin|zwierz|owad|ptak)|"
    r"rodzaj (ro[sś]lin|owad)|plemnik|mecz|olimpijsk|zawodni|drużyn|klub sportowy|"
    r"film (fabularny|amerykański)|serial|gra komputerowa|wydany przez|piosenk|raper|"
    r"miejscowość administracyjnie należała|jest (wsią|częścią wsi)|gmina wiejska|"
    r"stacja kolejowa|planetoid|asteroid|galaktyk|gwiazd[ay] w gwiazdozbiorze",
    re.I)
# Year and day pages ("1569", "7 listopada") are timelines: good for RAG, poor prose.
DATE_PAGE = re.compile(r"^\d+( p\.n\.e\.)?$|^\d{1,2} \w+$")
YEAR = re.compile(r"\b(1[0-9]{3}|[1-9][0-9]{2})\b(?! ?(?:m|km|kg|mm|cm|ha|zł|osób)\b)")


def norm(text: str) -> list[str]:
    return [w[:PREFIX] for w in WORD.findall(text.lower())]


# --- eval overlap ------------------------------------------------------------

def eval_shingles(path: Path, n: int = 8) -> set:
    """All 8-word runs from the eval items' question, context and gold."""
    if not path.exists():
        sys.exit(f"eval set {path} not found: refusing to build without the overlap filter "
                 "(run scripts/fetch_matura.py or pass --eval)")
    sh = set()
    for line in open(path, encoding="utf-8"):
        it = json.loads(line)
        for k in ("question", "context", "gold"):
            w = WORD.findall((it.get(k) or "").lower())
            sh.update(zip(*(w[i:] for i in range(n))))
    return sh


def overlaps(par: str, sh: set, n: int = 8) -> bool:
    w = WORD.findall(par.lower())
    return len(w) >= n and not sh.isdisjoint(zip(*(w[i:] for i in range(n))))


# --- download ------------------------------------------------------------------

def download(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for s in SHARDS:
        dst = out / s
        if dst.exists() and dst.stat().st_size > 1e8:
            continue
        print(f"downloading {s}", flush=True)
        tmp = dst.with_suffix(".part")
        urllib.request.urlretrieve(f"{HF}/{s}", tmp)
        tmp.rename(dst)
    print(f"parquet in {out}")


def articles(src: Path):
    import pyarrow.parquet as pq
    files = sorted(glob.glob(str(src / "*.parquet")))
    if not files:
        sys.exit(f"no parquet in {src}: run `plwiki.py download` first")
    for f in files:
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=2000, columns=["id", "url", "title", "text"]):
            for r in batch.to_pylist():
                yield r


def paragraphs(text: str) -> list[str]:
    """Paragraphs without the trailing reference/link sections."""
    out = []
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            continue
        if p in ("Przypisy", "Bibliografia", "Linki zewnętrzne", "Zobacz też", "Uwagi"):
            break
        out.append(p)
    return out


def passages(title: str, pars: list[str], target: int = 150) -> list[str]:
    """Groups paragraphs into ~target-word passages; very long paragraphs are split."""
    out, cur, n = [], [], 0
    for p in pars:
        words = p.split()
        while len(words) > 2 * target:
            if cur:
                out.append(" ".join(cur)); cur, n = [], 0
            out.append(" ".join(words[:target])); words = words[target:]
        cur.append(" ".join(words)); n += len(words)
        if n >= target:
            out.append(" ".join(cur)); cur, n = [], 0
    if cur and (n >= 20 or not out):
        out.append(" ".join(cur))
    elif cur:
        out[-1] += " " + " ".join(cur)
    return out


def history_score(title: str, pars: list[str]) -> float:
    """Density of history words and pre-1990 years, times log length and word variety."""
    text = "\n".join(pars)
    words = norm(text)
    n = len(words)
    if (n < 150 or NOISE.search(text[:600]) or title.startswith(("Lista", "Wykaz"))
            or DATE_PAGE.match(title)):
        return 0.0
    hits = [w for w in words if w in HIST]
    old = sum(int(y) < 1990 for y in YEAR.findall(text))
    dens = len(hits) / n * 100 + min(old / n * 100, 3)
    return round(dens * math.log10(min(n, 8000)) * min(len(set(hits)), 15) / 15, 2)


def build(src: Path, db_path: Path, dapt_path: Path, eval_path: Path, min_score: float,
          limit: int = 0):
    sh = eval_shingles(eval_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    dapt_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_db = db_path.with_suffix(".tmp")
    if tmp_db.exists():
        tmp_db.unlink()
    db = sqlite3.connect(tmp_db)
    db.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE passage(id INTEGER PRIMARY KEY, title TEXT, url TEXT, text TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(title, body, content='',
            tokenize='unicode61 remove_diacritics 0');
    """)
    hist = []
    stats = dict(articles=0, passages=0, dropped_overlap=0, history_articles=0)
    t0, pid = time.time(), 0
    rows, frows = [], []
    for a in articles(src):
        if limit and stats["articles"] >= limit:
            break
        stats["articles"] += 1
        pars = paragraphs(a["text"])
        keep = []
        for p in pars:
            if overlaps(p, sh):
                stats["dropped_overlap"] += 1
            else:
                keep.append(p)
        for ps in passages(a["title"], keep):
            pid += 1
            rows.append((pid, a["title"], a["url"], ps))
            frows.append((pid, " ".join(norm(a["title"])), " ".join(norm(ps))))
        s = history_score(a["title"], keep)
        if s >= min_score:
            hist.append((s, a["title"], "\n".join(keep)))
        if len(rows) > 20000:
            db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
            db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
            stats["passages"] += len(rows); rows, frows = [], []
        if stats["articles"] % 100000 == 0:
            print(f"{stats['articles']} articles, {stats['passages']} passages, "
                  f"{len(hist)} history, {time.time() - t0:.0f}s", flush=True)
    db.executemany("INSERT INTO passage VALUES (?,?,?,?)", rows)
    db.executemany("INSERT INTO fts(rowid,title,body) VALUES (?,?,?)", frows)
    stats["passages"] += len(rows)
    print("optimizing index", flush=True)
    db.execute("INSERT INTO fts(fts) VALUES('optimize')")
    db.commit(); db.close()
    tmp_db.rename(db_path)

    hist.sort(key=lambda x: -x[0])
    words = 0
    with open(dapt_path, "w", encoding="utf-8") as f:
        for s, t, text in hist:
            words += len(text.split())
            f.write(json.dumps({"title": t, "text": f"{t}\n\n{text}", "score": s},
                               ensure_ascii=False) + "\n")
    stats.update(history_articles=len(hist), history_words=words, min_score=min_score,
                 seconds=round(time.time() - t0), db_gb=round(db_path.stat().st_size / 1e9, 2),
                 source="wikimedia/wikipedia 20231101.pl (CC BY-SA 4.0)")
    db_path.with_suffix(".meta.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


# --- query -----------------------------------------------------------------------

STOP = {w[:PREFIX] for w in """i w z na do o się że nie jest to od po za przez dla oraz lub
czy jak który która które którzy jego jej ich tym tej ten ta te być był była było były
odpowiedź uzasadnij rozstrzygnij podaj wyjaśnij wymień fragment źródło źródła tekst
ilustracja podstawie odwołując informacji własnej wiedzy""".split()}


def search(db_path: Path, query: str, k: int = 5) -> list[dict]:
    """BM25 search; returns [{title, url, text, score}]. Stdlib only, for the exam harness."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    terms = [w for w in dict.fromkeys(norm(query)) if w not in STOP and len(w) > 1]
    if not terms:
        return []
    q = " OR ".join(f'"{t}"' for t in terms)
    cur = db.execute(
        "SELECT p.title, p.url, p.text, bm25(fts, 3.0, 1.0) AS s FROM fts "
        "JOIN passage p ON p.id = fts.rowid WHERE fts MATCH ? ORDER BY s LIMIT ?", (q, k))
    return [dict(title=t, url=u, text=x, score=round(-s, 2)) for t, u, x, s in cur]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download", "build", "search"])
    ap.add_argument("query", nargs="?")
    ap.add_argument("--src", default=str(ROOT / "data/corpus/plwiki"))
    ap.add_argument("--db", default=str(ROOT / "data/rag/plwiki.sqlite"))
    ap.add_argument("--dapt", default=str(ROOT / "data/dapt/plwiki_history.jsonl"))
    ap.add_argument("--eval", default=os.environ.get("EVAL", str(ROOT / "data/eval/matura.jsonl")))
    ap.add_argument("--min-score", type=float, default=10.0)
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="first N articles only (testing)")
    a = ap.parse_args()
    if a.cmd == "download":
        download(Path(a.src))
    elif a.cmd == "build":
        build(Path(a.src), Path(a.db), Path(a.dapt), Path(a.eval), a.min_score, a.limit)
    else:
        for r in search(Path(a.db), a.query or "", a.k):
            print(f"[{r['score']}] {r['title']}\n{r['text'][:400]}\n")


if __name__ == "__main__":
    main()
