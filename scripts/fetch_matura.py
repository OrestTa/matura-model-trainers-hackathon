#!/usr/bin/env python3
"""Builds the eval set from real CKE history matura papers (poziom rozszerzony).

The papers and answer keys are CKE's copyrighted PDFs, so they are never committed.
This script downloads them from cke.gov.pl into data/raw/cke/ and parses them into
data/eval/matura.jsonl in the format scripts/run_baselines.py reads (see the README,
"Eval set format"):

    python scripts/fetch_matura.py                  # all papers in PAPERS
    python scripts/fetch_matura.py --papers 2025-05 # just one

Each row is one scored item ("Zadanie 5.1."): the shared sources go in `context`,
the instruction (with any A-D options or P/F statements) in `question`, and the key
from "Zasady oceniania" in `gold`. Closed items get a machine-checkable key; open
items get the official model answer in `gold` (for the LLM judge) and, where the key
is a short list, `gold_keywords`. Extra fields the harness ignores:

    needs_image  the item depends on a photo, map, plan or chart we can't pass as text
    visuals      which kinds of visual the sources mention
    rubric       CKE's scoring rules for the item
    decision     for "Rozstrzygnij ... uzasadnij" items, the expected verdict alone
    paper, year, source_url

Needs pymupdf (pip install pymupdf).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne"

# Formuła 2023, main May session. Each paper is worth 60 points.
PAPERS = {
    "2023-05": {
        "arkusz": f"{BASE}/2023/Historia/MHIP-R0-100-2305.pdf",
        "zasady": f"{BASE}/2023/Historia/MHIP-R0-100-2305-zasady.pdf",
    },
    "2024-05": {
        "arkusz": f"{BASE}/2024/Historia/MHIP-R0-100-A-2405-arkusz.pdf",
        "zasady": f"{BASE}/2024/Historia/MHIP-R0-100-2405-zasady.pdf",
    },
    "2025-05": {
        "arkusz": f"{BASE}/2025/Historia/MHIP-R0-100-A-2505-arkusz.pdf",
        "zasady": f"{BASE}/2025/zasady_oceniania/MHIP-R0-100-2505-zasady.pdf",
    },
    "2026-05": {
        "arkusz": f"{BASE}/2026/Historia/MHIP-R0-100-A-2605-arkusz.pdf",
        "zasady": f"{BASE}/2026/Historia/MHIP-R0-100-2605-zasady.pdf",
    },
}

IMG = "[ilustracja – niedostępna w wersji tekstowej]"

# ---------------------------------------------------------------- download / text


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (matura-eval fetch)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"{url} did not return a PDF")
    dest.write_bytes(data)
    return dest


def pdf_lines(path: Path, mark_images: bool) -> list[str]:
    """Text lines in reading order, with IMG markers where large pictures sit."""
    import pymupdf

    out: list[str] = []
    for page in pymupdf.open(path):
        h = page.rect.height
        imgs = []
        if mark_images:
            for info in page.get_image_info():
                x0, y0, x1, y1 = info["bbox"]
                # Skip logos, barcodes and the margin score boxes.
                if (x1 - x0) * (y1 - y0) > 4000 and y0 < h * 0.93 and (x1 - x0) > 60:
                    imgs.append(y0)
        imgs.sort()
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                text = "".join(s["text"] for s in line["spans"])
                y = line["bbox"][1]
                # Page headers/footers come first in content order; don't anchor pictures to them.
                while imgs and imgs[0] <= y and h * 0.07 < y < h * 0.93:
                    imgs.pop(0)
                    out.append(IMG)
                out.append(text)
        out.extend(IMG for _ in imgs)
    return out


# ---------------------------------------------------------------- cleaning

JUNK = [
    r"^\s*Strona \d+ z \d+\s*$", r"^\s*MHIP-R0_100\s*$", r"^\s*MHIP-R0-\d+", r"^\s*Układ graficzny",
    r"^\s*© CKE", r"^\s*BRUDNOPIS", r"^\s*\(nie podlega ocenie\)", r"^\s*[PF]\s*$",
    r"^\s*\d(\s*[–-]\s*\d+)+\s*[–-]?\s*$", r"^\s*\d+(\.\d+)?\.\s*$", r"^\s*Egzamin maturalny z historii",
    r"^\s*Zasady oceniania rozwiązań zadań\s*$", r"^\s*Wypełnia\s*$", r"^\s*egzaminator\s*$",
    r"^\s*Nr zadania", r"^\s*Maks\. liczba", r"^\s*Uzyskana liczba",
]
JUNK_RE = re.compile("|".join(JUNK), re.I)


def clean(lines: list[str]) -> list[str]:
    out = []
    for ln in lines:
        ln = ln.replace(" ", " ").rstrip()
        ln = re.sub(r"[.…]{4,}", " …", ln)          # answer blanks
        ln = re.sub(r"\s{2,}", " ", ln).strip()
        if not ln or ln == "…" or JUNK_RE.search(ln):
            continue
        if ln == IMG and out and out[-1] == IMG:
            continue
        out.append(ln)
    return out


BREAK_BEFORE = re.compile(r"^([A-F]\.|\d+\.|\d+\)|[•–-] |Źródło|Fragment|Rozstrzygnięcie|Uzasadnienie|Na podstawie|"
                          r"Przykładow|Podobieństwo|Różnica|Nazwa|Wydarzenie|Opis|\[ilustracja|[A-ZĄĆĘŁŃÓŚŹŻ][^ ]* –)")


def join(lines: list[str]) -> str:
    """Re-flows lines the PDF wrapped mid-sentence; keeps list items and labels on their own lines."""
    out: list[str] = []
    for ln in lines:
        if out and not BREAK_BEFORE.match(ln) and out[-1] != IMG and ln != IMG \
                and not re.search(r"[:.;!?…]$", out[-1]) and len(out[-1]) > 40:
            if out[-1].endswith("-") and ln.startswith("-"):   # CKE's "polsko-\n-krzyżackie"
                out[-1] = out[-1] + ln[1:]
            else:
                out[-1] = out[-1] + " " + ln
        else:
            out.append(ln)
    return "\n".join(out).strip()


# ---------------------------------------------------------------- splitting

HEADER = re.compile(r"^Zadanie (\d+)(?:\.(\d+))?\.?(?=\s|$)\s*(?:\(0\s*[–-]\s*(\d+)\))?\s*(.*)$")


def split_tasks(lines: list[str]) -> list[dict]:
    """[{num, sub, points, lines}] in paper order."""
    tasks, cur = [], None
    for ln in lines:
        m = HEADER.match(ln)
        if m:
            cur = {"num": int(m[1]), "sub": int(m[2]) if m[2] else None,
                   "points": int(m[3]) if m[3] else None, "lines": []}
            if m[4].strip():
                cur["lines"].append(m[4].strip())
            tasks.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)
    return tasks


INSTR = re.compile(
    r"^(Rozstrzygnij|Wyjaśnij|Podaj|Oceń|Dokończ|Uzupełnij|Uporządkuj|Uszereguj|Wymień|"
    r"Przyporządkuj|Zaznacz|Wybierz|Każdemu|Każdej|Każdego|Określ|Porównaj|Scharakteryzuj|Wskaż|"
    r"Napisz|Zadanie zawiera|Rozpoznaj|Zapisz|Sformułuj|Przedstaw|Odwołując|Korzystając|Ustal|"
    r"Oblicz|Nazwij|Wpisz|Przypisz|Dobierz|Czy |W którym|Które|Który|Która|Jakie|Jaki|Na podstawie (?!:))")
SOURCE_START = re.compile(
    r"^(Źródło \d|Źródła?\b|Fragment\w* (dokument|opracowani|tekst|przemówieni|listu|traktatu|ustawy|konstytucji|relacji|pamiętnik|wspomnie|artykułu|utworu|kroniki)|"
    r"Mapa\b|Tabela\b|Wykres\b|Ilustracja\b|Fotografi|Plakat\b|Karykatura\b|Plan\b|Schemat\b|Rysunek\b|Obraz\b|Tekst \d|Informacje\b|Dane\b)")


def split_question(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separates leading source material from the instruction in one task block."""
    last_src = max((i for i, ln in enumerate(lines) if SOURCE_START.match(ln) or ln.startswith("Na podstawie:")),
                   default=-1)
    for i, ln in enumerate(lines):
        if i > last_src and INSTR.match(ln):
            return lines[:i], lines[i:]
    for i, ln in enumerate(lines):  # fallback: first instruction-like line
        if INSTR.match(ln):
            return lines[:i], lines[i:]
    return [], lines


def trailing_sources(lines: list[str]) -> tuple[list[str], list[str]]:
    """A sub-task block can end with the sources for the next sub-task."""
    for i, ln in enumerate(lines):
        if i > 0 and SOURCE_START.match(ln):
            return lines[:i], lines[i:]
    return lines, []


def paper_items(lines: list[str]) -> list[dict]:
    items, shared, shared_num = [], [], None
    for t in split_tasks(lines):
        if t["points"] is None:          # "Zadanie 5." group header: shared sources
            shared, shared_num = list(t["lines"]), t["num"]
            continue
        if t["sub"] is None:             # stand-alone "Zadanie 2. (0–1)"
            ctx, q = split_question(t["lines"])
            shared, shared_num = [], None
        else:
            if shared_num != t["num"]:
                shared, shared_num = [], t["num"]
            lead, body = split_question(t["lines"])
            q, extra = trailing_sources(body)
            ctx = shared + lead
            shared = shared + lead + extra
        qid = f"{t['num']}.{t['sub']}" if t["sub"] else f"{t['num']}"
        items.append({"task": qid, "points": t["points"], "context": ctx, "question": q})
    return items


# ---------------------------------------------------------------- answer keys

KEY_START = re.compile(r"^(Rozwiązani[ea]|Przykładow\w+ (odpowied|rozwiąz|realizacj)|Poprawn\w+ odpowied)", re.I)
FOOTNOTE = re.compile(r"^(\d\s*)?Rozporządzenie Ministra|^\(Dz\.\s?U\.|^programowej kształcenia|^Załącznik nr", re.I)


def key_items(lines: list[str]) -> dict[str, dict]:
    keys = {}
    for t in split_tasks(lines):
        if t["points"] is None:
            continue
        body = [ln for ln in t["lines"] if not FOOTNOTE.search(ln)]
        rub_i = next((i for i, ln in enumerate(body) if ln.startswith("Zasady oceniania")), None)
        sol_i = next((i for i, ln in enumerate(body) if KEY_START.match(ln)), None)
        rubric = body[rub_i + 1: sol_i if sol_i and sol_i > (rub_i or -1) else None] if rub_i is not None else []
        solution = body[sol_i:] if sol_i is not None else []
        if solution and re.match(r"^Rozwiązani[ea]\s*$", solution[0]):
            solution = solution[1:]
        if not rubric and not solution and t["points"] >= 10:
            rubric = body   # 2025 essay: no "Zasady oceniania" line, the whole section is the criteria
        qid = f"{t['num']}.{t['sub']}" if t["sub"] else f"{t['num']}"
        if qid in keys:   # the essay criteria can span two "Zadanie 26." sections
            keys[qid]["rubric"] = (keys[qid]["rubric"] + "\n" + join(rubric)).strip()
            keys[qid]["solution"] = (keys[qid]["solution"] + "\n" + join(solution)).strip()
        else:
            keys[qid] = {"points": t["points"], "rubric": join(rubric), "solution": join(solution)}
    return keys


# ---------------------------------------------------------------- typing & gold

VISUALS = {
    "mapa": r"\bmap(a|y|ie|ę|ą)\b|\bmapk", "fotografia": r"\bfotografi|\bzdjęci", "ilustracja": r"\bilustracj(?!a –)|\brycin|\brysun|\bobraz(\b|u|ie|em)",
    "plakat": r"plakat", "karykatura": r"karykatur", "plan": r"\bplan(ie|u)? (miasta|bitwy|twierdzy|zamku|budowli|osady)|\bplan\b\s*$",
    "wykres": r"wykres|diagram", "moneta/medal": r"monet|medal|pieczęć|pieczęci|banknot", "schemat": r"schemat",
    "dzieło sztuki": r"relief|rzeźb|obraz\w* olejn|fresk|mozaik|witraż|budowl\w* na fotografii",
}


def detect_category(q: str, ctx: str, points: int, solution: str) -> str:
    ql = q.lower()
    if points >= 10 or "wypracowani" in ql:
        return "essay"
    if re.search(r"oceń prawdziwość|zaznacz p,|wybierz p,|\bp, jeśli", ql):
        return "true_false"
    if re.search(r"uporządkuj|uszereguj|chronologiczn|od najwcześniejsz", ql) and "rozstrzygnij" not in ql:
        return "chronology"
    if re.search(r"przyporządkuj|dobierz|przypisz", ql):
        return "matching"
    if re.search(r"zaznacz|wybierz|podkreśl", ql) and re.search(r"(^|\n)A\.? ", q) and re.search(r"(^|\n)B\.? ", q):
        return "closed_choice"
    if re.search(r"spośród podanych|poprawne dokończenie|właściwą odpowiedź", ql):
        return "closed_choice"
    if re.search(r"źród|fotografi|map|ilustracj|tekś|ulotk|znaczk|cytowan|przytoczon|plakat|karykatur|tabel|plan|wykres|tekst|fragment|dokument|"
                 r"relief|rycin|schemat|medal|obraz|mow[ayi]|rysun|drzew|genealog|autor|legend", ql):
        return "source_analysis"
    return "short_open"


def alts(value: str) -> list[str]:
    """Keyword alternatives from a key line.

    '/', 'albo', 'lub' and top-level commas separate alternatives. Square brackets mark optional
    words ('[Ignacy] Łukasiewicz' -> 'Łukasiewicz'), except a trailing bracket of synonyms after a
    one-word answer ('Hanza [hanza niemiecka, związek hanzeatycki]').
    """
    out = []
    for part in re.split(r"\s*/\s*|\s+albo\s+|\s+lub\s+|,\s*(?![^\[]*\])", value):
        m = re.fullmatch(r"\s*(\S+)\s*\[([^\]]+)\]\s*", part)
        if m:
            out += [m[1], *re.split(r",\s*", m[2])]
            continue
        base = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", part)
        out.append(re.sub(r"\s+", " ", base))
    out = [x.strip(" .,;:") for x in out]
    return list(dict.fromkeys(x for x in out if len(x) > 1))


def closed_gold(cat: str, solution: str) -> str | None:
    s = solution.strip()
    first = re.sub(r"^Rozstrzygnięcie:\s*", "", s.splitlines()[0]).strip() if s else ""
    if cat == "closed_choice":
        if re.fullmatch(r"[A-F](\s*(,|i|oraz)\s*[A-F])*\.?", first):
            return ", ".join(re.findall(r"[A-F]", first))
        return None
    if cat == "true_false":
        pairs = re.findall(r"(\d+)\.?\s*[–-]\s*([PF])\b", s)
        if pairs:
            return ", ".join(v for _, v in sorted(pairs, key=lambda p: int(p[0])))
        if re.fullmatch(r"[PF]{2,6}", first.replace(" ", "")):
            return ", ".join(first.replace(" ", ""))
        return None
    if cat == "chronology":
        seq = re.findall(r"\b([A-F]|\d)\b", first)
        return ", ".join(seq) if len(seq) >= 3 else None
    if cat == "matching":
        pairs = re.findall(r"^(\d+)\.?\s*[–-]\s*([A-F])\s*$", s, re.M)
        return ", ".join(f"{a} – {b}" for a, b in pairs) if pairs else None
    return None


def pair_keywords(solution: str) -> list[list[str]] | None:
    """For keys that are a short list of 'label – value' lines, one keyword group per line."""
    lines = [ln for ln in solution.splitlines() if ln.strip()]
    if not 1 <= len(lines) <= 6:
        return None
    groups = []
    for ln in lines:
        m = re.match(r"^(?:Fragment |Opis |Dokument |Źródło )?([A-F1-9]|[A-ZĄĆĘŁŃÓŚŹŻ]\w+(?: \w+){0,2})\.?\s*[–-]\s*(.+)$", ln)
        if not m or len(m[2]) > 80:
            if len(lines) <= 4 and len(ln.split()) <= 5 and not re.match(r"^(Rozstrzygnięcie|Przykładow|Nazwa|•)", ln) \
                    and ":" not in ln:
                groups.append(alts(ln))     # a plain list: one answer per line
                continue
            return None
        label, value = m[1], m[2].strip()
        if re.fullmatch(r"[A-F1-9]", value):     # letter <-> number pair
            groups.append([f"{label} – {value}", f"{label} - {value}", f"{label}-{value}",
                           f"{label}–{value}", f"{label}: {value}", f"{label} {value}"])
        else:
            groups.append(alts(value))
    return groups


VISUAL_REF = re.compile(r"fotografi|ilustracj|\bmap|plakat|karykatur|\bplan|rycin|relief|medal|monet|banknot|obraz|"
                        r"rysun|zdjęci|schemat|wykres|znaczk|ulotk|okładk|herb|grafi(czn|k)|widoczn|przedstawion\w* na", re.I)


def image_needed(ctx: str, q: str) -> bool:
    """True if answering needs a picture we only have as a placeholder."""
    if IMG in q:
        return True
    if IMG not in ctx:
        return False
    if VISUAL_REF.search(q):
        return True
    # Which numbered sources carry a picture, and does the question use one of them?
    parts = re.split(r"(?m)^(?=Źródło ?\d)", ctx)
    with_img = {m[1] for p in parts if IMG in p and (m := re.match(r"Źródło ?(\d)", p))}
    if not with_img:            # a single unnumbered source that is a picture
        return True
    asked = set(re.findall(r"źród\w* ?(\d)", q, re.I))
    if re.search(r"\bobu źródeł|\bźródeł\b|\bźródła\b(?! ?\d)", q, re.I):
        return True
    return bool(asked & with_img)


def short_keywords(solution: str) -> list[list[str]] | None:
    """A one-line key naming a thing ('Rumunia', '[Eugeniusz] Kwiatkowski') becomes one keyword group."""
    lines = [ln for ln in solution.splitlines() if ln.strip()]
    if len(lines) != 1 or len(lines[0]) > 90 or re.match(r"^(Rozstrzygnięcie|Przykładow|•)", lines[0]):
        return None
    group = alts(lines[0])
    return [group] if group and all(len(a.split()) <= 6 for a in group) else None


def build_row(paper: str, url: str, it: dict, key: dict | None) -> dict:
    ctx, q = join(it["context"]), join(it["question"])
    full = ctx + "\n" + q
    solution = key["solution"] if key else ""
    cat = detect_category(q, ctx, it["points"], solution)
    visuals = sorted(k for k, pat in VISUALS.items() if re.search(pat, full, re.I))
    needs_image = image_needed(ctx, q)
    row = {
        "id": f"{paper}-z{it['task']}",
        "question": q,
        "context": ctx,
        "category": cat,
        "points": it["points"],
    }
    gold = closed_gold(cat, solution) if cat in {"closed_choice", "true_false", "chronology", "matching"} else None
    if gold:
        row["gold"] = gold
    else:
        kw = (pair_keywords(solution) or short_keywords(solution)) if cat != "essay" else None
        if cat in {"closed_choice", "true_false", "chronology", "matching"}:
            # A closed type whose key isn't in the scorer's format (e.g. "Fragment A – Karol IX"):
            # score it by keywords, not with the closed scorer.
            if kw:
                row["gold_keywords"] = kw
            row["reference"] = solution
        elif cat == "essay":
            row["gold"] = key["rubric"] if key else None   # criteria for the judge; there is no model essay
        else:
            row["gold"] = solution or None
            if kw:
                row["gold_keywords"] = kw
    m = re.search(r"Rozstrzygnięcie:\s*(.+)", solution)
    if m:
        row["decision"] = m[1].strip()
    row.update({
        "needs_image": bool(needs_image),
        "visuals": visuals,
        "rubric": key["rubric"] if key else "",
        "paper": paper,
        "year": int(paper[:4]),
        "source_url": url,
    })
    if not key:
        row["warning"] = "no answer key found"
    return row


# ---------------------------------------------------------------- main


def build(paper: str, raw: Path) -> list[dict]:
    urls = PAPERS[paper]
    ark = download(urls["arkusz"], raw / Path(urls["arkusz"]).name)
    zas = download(urls["zasady"], raw / Path(urls["zasady"]).name)
    items = paper_items(clean(pdf_lines(ark, mark_images=True)))
    keys = key_items(clean(pdf_lines(zas, mark_images=False)))
    # CKE sometimes numbers the essay differently in the key (2025: item 25, key 26).
    missing = [it for it in items if it["task"] not in keys]
    spare = [k for k in keys if k not in {it["task"] for it in items}]
    if len(missing) == 1 and len(spare) == 1 and keys[spare[0]]["points"] == missing[0]["points"]:
        keys[missing[0]["task"]] = keys.pop(spare[0])
    rows = [build_row(paper, urls["arkusz"], it, keys.get(it["task"])) for it in items]
    total = sum(r["points"] for r in rows)
    missing = [it["task"] for it in items if it["task"] not in keys]
    extra = sorted(set(keys) - {it["task"] for it in items})
    print(f"{paper}: {len(rows)} items, {total} points"
          + (f", no key for {missing}" if missing else "")
          + (f", keys without item {extra}" if extra else ""), file=sys.stderr)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--papers", default=",".join(PAPERS), help="comma-separated, e.g. 2024-05,2025-05")
    ap.add_argument("--raw-dir", default=str(ROOT / "data/raw/cke"))
    ap.add_argument("-o", "--out", default=str(ROOT / "data/eval/matura.jsonl"))
    ap.add_argument("--text-only", action="store_true", help="drop items that need an image")
    args = ap.parse_args()

    rows = []
    for p in args.papers.split(","):
        rows += build(p.strip(), Path(args.raw_dir))
    if args.text_only:
        rows = [r for r in rows if not r["needs_image"]]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cats = Counter(r["category"] for r in rows)
    auto = sum(1 for r in rows if (r.get("gold") and r["category"] in
               {"closed_choice", "true_false", "chronology", "matching"}) or r.get("gold_keywords"))
    print(f"wrote {len(rows)} items ({sum(r['points'] for r in rows)} points) to {out}", file=sys.stderr)
    print(f"  by type: {dict(cats)}", file=sys.stderr)
    print(f"  auto-scorable: {auto}, needs image: {sum(r['needs_image'] for r in rows)}", file=sys.stderr)


if __name__ == "__main__":
    main()
