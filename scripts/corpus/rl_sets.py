#!/usr/bin/env python3
"""History questions with checkable answers, for RLVR (GRPO) and extra SFT.

    python scripts/corpus/rl_sets.py            # after plwiki.py build (uses its history slice)

Writes data/rl/<source>.jsonl, one question per line:
    {"id", "source", "license", "category", "question", "answer", "answers", "reward"}
`answers` lists every accepted form; `reward` names the checker:
    choice  - the answer is one letter (A-D)
    alias   - normalised exact match against any of `answers` (case, diacritics kept)
    year    - the first 3-4 digit number in the reply equals `answer`
    order   - the letters in the reply, in order, equal `answer` (e.g. "CABD")

Sources:
- polqa: `ipipan/polqa` (CC BY-SA 4.0), Polish quiz questions ("Jeden z dziesięciu") with
  answer aliases; kept when the question uses history vocabulary or a relevant passage is
  a strongly historical article (score >= 20) from data/dapt/plwiki_history.jsonl.
- gmmlu: `CohereLabs/Global-MMLU` pl test (Apache-2.0), subjects high_school_european_history,
  high_school_world_history, high_school_us_history and prehistory: 4-option MCQ.
- wiki_year / wiki_order: generated from the Polish Wikipedia history slice (CC BY-SA 4.0):
  events (battles, treaties, uprisings, unions...) whose first sentence dates them. "In which
  year...?" and "order these four events" (the matura's chronology task), years >= 5 apart.
Questions sharing an 8-word run with the eval set are dropped. Only the script is in the repo.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plwiki as P  # noqa: E402

ROOT = P.ROOT
POLQA = "https://huggingface.co/datasets/ipipan/polqa/resolve/main/data/{}.csv"
GMMLU = "https://huggingface.co/datasets/CohereLabs/Global-MMLU/resolve/main/pl/test-00000-of-00001.parquet"
GMMLU_SUBJ = {"high_school_european_history", "high_school_world_history",
              "high_school_us_history", "prehistory"}
EVENT = re.compile(r"^(Bitwa|Oblężenie|Powstanie|Traktat|Pokój|Unia|Wojna|Konstytucja|Sejm|Zjazd|"
                   r"Hołd|Konfederacja|Bunt|Rewolucja|Przewrót|Zamach|Rokosz|Kongres|Konferencja|"
                   r"Układ|Przywilej|Statut|Rozbiór|I rozbiór|II rozbiór|III rozbiór|Chrzest|"
                   r"Koronacja|Insurekcja|Potop|Odsiecz|Wyprawa|Najazd|Manifest|Ustawa|Edykt|"
                   r"Reforma|Pakt|Kampania|Operacja|Strajk|Wydarzenia|Masakra|Rzeź|Porozumienia?)\b")
YEAR = re.compile(r"\b(1[0-9]{3}|[5-9][0-9]{2})\b")


def fetch(url: str, dst: Path) -> Path:
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dst.with_suffix(".part"))
        dst.with_suffix(".part").rename(dst)
    return dst


def clean(q: str, sh) -> bool:
    return not P.overlaps(q, sh)


def polqa(src: Path, hist_titles: set, sh) -> list[dict]:
    csv.field_size_limit(10**9)
    by_q = {}
    for split in ("train", "valid", "test"):
        for r in csv.DictReader(open(fetch(POLQA.format(split), src / f"polqa_{split}.csv"),
                                     encoding="utf-8")):
            q = by_q.setdefault((split, r["question_id"]), {"q": r["question"], "a": r["answers"],
                                                            "titles": set()})
            if r["relevant"] == "True":
                q["titles"].add(r["passage_title"])
    out = []
    for (split, qid), q in by_q.items():
        words = P.norm(q["q"])
        if not (q["titles"] & hist_titles or sum(w in P.HIST for w in words) >= 1):
            continue
        try:
            answers = [a for a in ast.literal_eval(q["a"]) if a]
        except (ValueError, SyntaxError):
            continue
        if not answers or not clean(q["q"], sh):
            continue
        out.append(dict(id=f"polqa-{split}-{qid}", source="ipipan/polqa", license="CC BY-SA 4.0",
                        category="short_open", question=q["q"], answer=answers[0],
                        answers=answers, reward="alias"))
    return out


def gmmlu(src: Path, sh) -> list[dict]:
    import pyarrow.parquet as pq
    t = pq.read_table(fetch(GMMLU, src / "gmmlu_pl.parquet")).to_pylist()
    out = []
    for r in t:
        if r["subject"] not in GMMLU_SUBJ or not clean(r["question"], sh):
            continue
        opts = "\n".join(f"{k}. {r['option_' + k.lower()]}" for k in "ABCD")
        out.append(dict(id=f"gmmlu-{r['sample_id']}", source="CohereLabs/Global-MMLU (pl)",
                        license="Apache-2.0", category="closed_choice",
                        question=f"{r['question']}\n{opts}", answer=r["answer"].strip(),
                        answers=[r["answer"].strip()], reward="choice"))
    return out


def wiki_events(dapt: Path) -> list[tuple[str, int]]:
    """(title, year) for event articles whose first sentence carries the year."""
    ev = {}
    for line in open(dapt, encoding="utf-8"):  # best-scored first, so dict order = relevance
        r = json.loads(line)
        # "Bitwa pod Neerwinden (1793)": the qualifier would give the answer away.
        t = re.sub(r"\s*\(.*?\)", "", r["title"]).strip()
        if not EVENT.match(r["title"]) or YEAR.search(t) or t in ev:
            continue
        body = r["text"].split("\n", 2)
        first = (body[2] if len(body) > 2 else r["text"])[:300].split(". ")[0]
        m = YEAR.search(first)
        if m and "p.n.e" not in first[:m.end() + 8]:
            y = int(m.group(1))
            if 500 <= y <= 2010:
                ev[t] = y
    return list(ev.items())


def wiki_sets(events, n_order: int, seed: int = 0, top: int = 3000) -> tuple[list, list]:
    """Year questions for every event; ordering sets from the `top` most history-dense."""
    rnd = random.Random(seed)
    years = [dict(id=f"wiki-year-{i}", source="pl.wikipedia (history slice)",
                  license="CC BY-SA 4.0", category="short_open",
                  question=f"W którym roku miało miejsce wydarzenie: {t}? Podaj sam rok.",
                  answer=str(y), answers=[str(y)], reward="year")
             for i, (t, y) in enumerate(events)]
    order, tries = [], 0
    while len(order) < n_order and tries < n_order * 50 and len(events[:top]) >= 4:
        tries += 1
        pick = rnd.sample(events[:top], 4)
        ys = sorted(y for _, y in pick)
        if min(b - a for a, b in zip(ys, ys[1:])) < 5:
            continue
        letters = "ABCD"
        lines = "\n".join(f"{letters[i]}. {t}" for i, (t, _) in enumerate(pick))
        ans = "".join(letters[i] for i, _ in sorted(enumerate(pick), key=lambda x: x[1][1]))
        order.append(dict(id=f"wiki-order-{len(order)}", source="pl.wikipedia (history slice)",
                          license="CC BY-SA 4.0", category="chronology",
                          question="Uporządkuj chronologicznie wydarzenia, od najwcześniejszego. "
                                   f"Zapisz litery we właściwej kolejności.\n{lines}",
                          answer=ans, answers=[ans], reward="order"))
    return years, order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "data/corpus/rl"))
    ap.add_argument("--dapt", default=str(ROOT / "data/dapt/plwiki_history.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data/rl"))
    ap.add_argument("--eval", default=os.environ.get("EVAL", str(ROOT / "data/eval/matura.jsonl")))
    ap.add_argument("--n-order", type=int, default=5000)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sh = P.eval_shingles(Path(a.eval))
    hist_titles, events = set(), []
    if Path(a.dapt).exists():
        # Only clearly historical articles vouch for a quiz question (country pages don't).
        hist_titles = {r["title"] for r in map(json.loads, open(a.dapt, encoding="utf-8"))
                       if r["score"] >= 20}
        events = wiki_events(Path(a.dapt))
    else:
        print(f"{a.dapt} missing: PolQA filtered by vocabulary only, no Wikipedia sets")
    sets = {"polqa": polqa(src, hist_titles, sh), "gmmlu": gmmlu(src, sh)}
    sets["wiki_year"], sets["wiki_order"] = wiki_sets(events, a.n_order)
    for name, rows in sets.items():
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name}: {len(rows)} -> {out / name}.jsonl")


if __name__ == "__main__":
    main()
