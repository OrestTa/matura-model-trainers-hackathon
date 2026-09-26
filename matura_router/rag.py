"""Offline retrieval over a local history knowledge base (allowed at the exam; not
counted toward the size limit).

The knowledge base is a JSONL of {"id", "title", "text"} passages, built before the
exam by scripts/build_kb.py (Polish Wikipedia, CC BY-SA). Retrieval is plain BM25
with crude Polish stemming (a word's first 6 letters), in pure Python: no extra
model, no GPU, and ~30k passages index in a few seconds.
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


def terms(text: str) -> list[str]:
    return [w[:6] for w in re.findall(r"\w+", text.lower())
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
    return ("Wiedza pomocnicza (fragmenty encyklopedii, mogą być nieistotne dla zadania):\n"
            + "\n\n".join(out))
