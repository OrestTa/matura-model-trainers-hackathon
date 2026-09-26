"""Offline retrieval over a local history knowledge base (allowed at the exam; not
counted toward the size limit).

Two knowledge-base formats, picked by file extension (`load_retriever`):

- `.jsonl` of {"id", "title", "text"} passages, e.g. from scripts/build_kb.py (a
  history slice of Polish Wikipedia, CC BY-SA). In-memory BM25 with crude Polish
  stemming (a word's first 6 letters), pure Python; fine up to ~100k passages.
- `.sqlite` / `.db` with an FTS5 table `passages(title, text)` (other columns
  UNINDEXED are fine), for the full Polish Wikipedia. SQLite ranks with its own BM25.
  The index from scripts/corpus/plwiki.py (full Polish Wikipedia + Wikisource + Wolne
  Lektury, table `passage` plus a contentless FTS5 table `fts` over 6-letter prefixes)
  is detected and queried the same way.

Both return the same Passage objects, so the router doesn't care which one it has.
"""

from __future__ import annotations

import collections
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

_STOP = set("""a aby ale albo ani bo by być był była było były co czy dla do gdy i ich im
jak jaki jako jego jej jest już które który która których lub ma na nad nie niż o od oraz
po pod przez przy się są ta tak te tego tej to tu tym w we z za ze że źródło źródła
podaj wyjaśnij rozstrzygnij uzasadnij odpowiedź odpowiedzi wymień określ oceń""".split())


# Common Polish case endings, longest first. Cutting to 6 letters alone leaves short words
# inflected ("unii" vs "unia", "wojny" vs "wojna", "królów" vs "król") and they never matched.
_ENDINGS = sorted("""ami ach owi ów om em ie ii ią ię ę ą y i a u e o""".split(), key=len, reverse=True)


def stem(w: str) -> str:
    for e in _ENDINGS:
        if w.endswith(e) and len(w) - len(e) >= 3:
            w = w[:-len(e)]
            break
    return w[:6]


def terms(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"\w+", text.lower())
            if len(w) > 2 and w not in _STOP and not w.isdigit()] + re.findall(r"\b\d{3,4}\b", text)


@dataclass
class Passage:
    id: str
    title: str
    text: str
    score: float = 0.0


class BM25Retriever:
    def __init__(self, passages: list[Passage], k1: float = 1.2, b: float = 0.75):
        self.passages, self.k1, self.b = passages, k1, b
        self.postings: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
        self.lengths = []
        for i, p in enumerate(passages):
            tf = collections.Counter(terms(f"{p.title} {p.title} {p.text}"))
            self.lengths.append(sum(tf.values()))
            for t, c in tf.items():
                self.postings[t].append((i, c))
        self.avg = sum(self.lengths) / max(len(self.lengths), 1)
        n = len(passages)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    @classmethod
    def load(cls, path: str | Path) -> "BM25Retriever":
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        return cls([Passage(str(r.get("id", i)), r.get("title", ""), r["text"]) for i, r in enumerate(rows)])

    def search(self, query: str, k: int = 4) -> list[Passage]:
        scores: dict[int, float] = collections.defaultdict(float)
        for t in set(terms(query)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, c in self.postings[t]:
                norm = c + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
                scores[i] += idf * c * (self.k1 + 1) / norm
        best = sorted(scores.items(), key=lambda x: -x[1])[:k]
        return [Passage(self.passages[i].id, self.passages[i].title, self.passages[i].text, round(s, 2))
                for i, s in best]


class SQLiteRetriever:
    """FTS5 over a large knowledge base on disk; the query is OR-ed prefix terms."""

    def __init__(self, path: str | Path, table: str = "passages"):
        import sqlite3
        self.db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
        names = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master")}
        # scripts/corpus/plwiki.py: prefixes are indexed as whole tokens, text lives in `passage`.
        self.prefixed = {"fts", "passage"} <= names and table not in names
        self.table = "passage" if self.prefixed else table

    @property
    def passages(self) -> list:  # len() for logging only
        return range(self.db.execute(f"SELECT count(*) FROM {self.table}").fetchone()[0])

    def search(self, query: str, k: int = 4) -> list[Passage]:
        words = list(dict.fromkeys(terms(query)))[:32]
        if not words:
            return []
        if self.prefixed:
            # Prefix match: the index holds 6-letter prefixes, the query holds stems (maybe shorter).
            match = " OR ".join(f'"{w}"*' for w in words)
            rows = self.db.execute(
                "SELECT p.id, p.title, p.text, bm25(fts, 2.0, 1.0) AS s FROM fts "
                "JOIN passage p ON p.id = fts.rowid WHERE fts MATCH ? ORDER BY s LIMIT ?",
                (match, k)).fetchall()
            return [Passage(str(r[0]), r[1], r[2], round(-r[3], 2)) for r in rows]
        match = " OR ".join(f'"{w}"*' for w in words)
        rows = self.db.execute(
            f"SELECT rowid, title, text, bm25({self.table}, 2.0, 1.0) AS s FROM {self.table} "
            f"WHERE {self.table} MATCH ? ORDER BY s LIMIT ?", (match, k)).fetchall()
        return [Passage(str(r[0]), r[1], r[2], round(-r[3], 2)) for r in rows]


def load_retriever(path: str | Path):
    path = Path(path)
    if path.suffix in (".sqlite", ".db", ".sqlite3"):
        return SQLiteRetriever(path)
    return BM25Retriever.load(path)


def format_knowledge(passages: list[Passage], max_chars: int = 3000) -> str:
    """The retrieved passages as a block the router prepends to the question."""
    out, used = [], 0
    for p in passages:
        chunk = f"[{p.title}] {p.text.strip()}"
        if used + len(chunk) > max_chars:
            chunk = chunk[:max(0, max_chars - used)]
        if not chunk:
            break
        out.append(chunk)
        used += len(chunk)
    if not out:
        return ""
    # Close the block explicitly so the model doesn't take the encyclopedia for the task's source.
    return ("Wiedza pomocnicza (fragmenty encyklopedii, mogą być nieistotne dla zadania):\n"
            + "\n\n".join(out) + "\n\nKoniec wiedzy pomocniczej. Treść zadania i źródła:")
