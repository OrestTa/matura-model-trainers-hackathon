"""Builds the offline RAG knowledge base from Polish Wikipedia (CC BY-SA 4.0).

Run before the exam on a box with internet (the cloud sessions can't reach Wikipedia):

    python scripts/build_kb.py                     # -> data/kb/passages.jsonl
    python scripts/build_kb.py --per-query 20      # wider

For every history topic (the synthetic-data topics plus the seeds below) it takes the
top Wikipedia search hits, downloads each article's plain text, drops reference
sections and splits it into ~700-character passages. Each passage keeps its article
title and URL for attribution. The router picks it up from configs/routes.yaml
(`rag.path`). The file is in data/, which git ignores; this script is its source.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

API = "https://pl.wikipedia.org/w/api.php"
UA = "matura-model-trainers-hackathon/0.1 (educational; github.com/OrestTa/matura-model-trainers-hackathon)"
DROP_SECTIONS = re.compile(r"^(Przypisy|Bibliografia|Linki zewnętrzne|Zobacz też|Uwagi|Literatura)\s*$", re.M)

# Beyond the synthetic-data topics: people, documents and terms the CKE papers lean on.
EXTRA_SEEDS = [
    "Mieszko I", "Bolesław Chrobry", "zjazd gnieźnieński", "Kazimierz Wielki", "Władysław Jagiełło",
    "bitwa pod Grunwaldem", "Kazimierz Jagiellończyk", "Zygmunt August", "konfederacja warszawska",
    "Stefan Batory", "Zygmunt III Waza", "liberum veto", "Stanisław August Poniatowski",
    "Komisja Edukacji Narodowej", "Tadeusz Kościuszko", "Legiony Polskie we Włoszech",
    "Kodeks Napoleona", "Adam Mickiewicz", "Józef Piłsudski", "Roman Dmowski", "Ignacy Paderewski",
    "traktat wersalski", "konstytucja marcowa", "konstytucja kwietniowa", "Eugeniusz Kwiatkowski",
    "pakt Ribbentrop-Mołotow", "zbrodnia katyńska", "Armia Krajowa", "Władysław Sikorski",
    "Polski Komitet Wyzwolenia Narodowego", "Bolesław Bierut", "Władysław Gomułka", "Edward Gierek",
    "Wojciech Jaruzelski", "Lech Wałęsa", "Jan Paweł II", "Tadeusz Mazowiecki", "plan Balcerowicza",
    "kodeks Hammurabiego", "Perykles", "Juliusz Cezar", "Oktawian August", "Konstantyn Wielki",
    "Justynian I Wielki", "Karol Wielki", "Otton III", "Grzegorz VII", "Marcin Luter", "Jan Kalwin",
    "sobór trydencki", "Ludwik XIV", "Piotr I Wielki", "Fryderyk II Wielki", "Napoleon Bonaparte",
    "Otto von Bismarck", "Abraham Lincoln", "Lenin", "Józef Stalin", "Adolf Hitler", "Benito Mussolini",
    "Winston Churchill", "Franklin Delano Roosevelt", "plan Marshalla", "NATO", "Układ Warszawski",
    "kryzys kubański", "mur berliński", "Michaił Gorbaczow", "romanizm", "gotyk", "renesans",
    "barok", "klasycyzm", "romantyzm", "secesja (sztuka)", "socrealizm", "Wielki kryzys",
    "rewolucja neolityczna", "paleolit", "Mezopotamia", "starożytny Egipt", "kultura minojska",
]


def api(params: dict, retries: int = 4) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001 - rate limits and hiccups: back off and retry
            time.sleep(2 ** i)
    return {}


def search(query: str, n: int) -> list[str]:
    res = api({"action": "query", "list": "search", "srsearch": query, "srlimit": n, "srnamespace": 0})
    return [h["title"] for h in res.get("query", {}).get("search", [])]


def article(title: str) -> str:
    res = api({"action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "plain",
               "redirects": 1, "titles": title})
    pages = res.get("query", {}).get("pages", [])
    return pages[0].get("extract", "") if pages else ""


def chunk(text: str, size: int = 700) -> list[str]:
    m = DROP_SECTIONS.search(text)
    text = text[:m.start()] if m else text
    out, cur = [], ""
    for para in (p.strip() for p in text.split("\n")):
        if len(para) < 40:  # headings and stubs
            continue
        if cur and len(cur) + len(para) > size:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n{para}".strip()
        while len(cur) > 2 * size:  # one very long paragraph: cut at a sentence end
            cut = cur.rfind(". ", 0, size) + 1 or size
            out.append(cur[:cut].strip())
            cur = cur[cut:].strip()
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=str(ROOT / "data/kb/passages.jsonl"))
    ap.add_argument("--per-query", type=int, default=12, help="search hits kept per topic")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    from gen_synthetic import TOPICS
    seeds = list(dict.fromkeys(TOPICS + EXTRA_SEEDS))
    with ThreadPoolExecutor(args.workers) as pool:
        titles = list(dict.fromkeys(t for hits in pool.map(lambda q: search(q, args.per_query), seeds)
                                    for t in hits))
        print(f"{len(seeds)} topics -> {len(titles)} articles", flush=True)
        texts = list(pool.map(article, titles))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for title, text in zip(titles, texts):
            url = "https://pl.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            for i, passage in enumerate(chunk(text)):
                f.write(json.dumps({"id": f"{title}#{i}", "title": title, "text": passage, "url": url},
                                   ensure_ascii=False) + "\n")
                n += 1
    (out.parent / "SOURCE.md").write_text(
        "Passages from Polish Wikipedia (https://pl.wikipedia.org), CC BY-SA 4.0. Each passage's `url` "
        "names its article. Built by scripts/build_kb.py.\n")
    print(f"{n} passages from {sum(1 for t in texts if t)} articles -> {out}")


if __name__ == "__main__":
    main()
