#!/usr/bin/env python3
"""Builds the eval set from real CKE history matura papers (poziom rozszerzony).

The papers and answer keys are CKE's copyrighted PDFs, so they are never committed.
This script downloads them from cke.gov.pl into data/raw/cke/ and parses them into
data/eval/matura.jsonl in the format scripts/run_baselines.py reads (see the README,
"Eval set format"):

    python scripts/fetch_matura.py                   # headline: May 2023-2026 -> data/eval/matura.jsonl
    python scripts/fetch_matura.py --papers all      # all 16 papers -> data/eval/matura_all.jsonl
    python scripts/fetch_matura.py --papers 2025-05  # just one

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
B15 = "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2015/Arkusze_egzaminacyjne"
EXTRA = "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe"

# Every historia (poziom rozszerzony) paper CKE publishes with an answer key. CKE only posts the
# main May session. "formula" 2023 is the current exam; 2015 is the previous one (2015-2020 "MHI-R1",
# 2021-2024 "EHIP", still sat by technikum students until 2024). The default set is the current format.
PAPERS = {
    # formuła 2023, main May session (the headline eval set)
    "2023-05": {"formula": 2023, "kind": "main",
                "arkusz": f"{BASE}/2023/Historia/MHIP-R0-100-2305.pdf",
                "zasady": f"{BASE}/2023/Historia/MHIP-R0-100-2305-zasady.pdf"},
    "2024-05": {"formula": 2023, "kind": "main",
                "arkusz": f"{BASE}/2024/Historia/MHIP-R0-100-A-2405-arkusz.pdf",
                "zasady": f"{BASE}/2024/Historia/MHIP-R0-100-2405-zasady.pdf"},
    "2025-05": {"formula": 2023, "kind": "main",
                "arkusz": f"{BASE}/2025/Historia/MHIP-R0-100-A-2505-arkusz.pdf",
                "zasady": f"{BASE}/2025/zasady_oceniania/MHIP-R0-100-2505-zasady.pdf"},
    "2026-05": {"formula": 2023, "kind": "main",
                "arkusz": f"{BASE}/2026/Historia/MHIP-R0-100-A-2605-arkusz.pdf",
                "zasady": f"{BASE}/2026/Historia/MHIP-R0-100-2605-zasady.pdf"},
    # formuła 2023, CKE demo paper (March 2022) and mock exam (January 2026)
    "pokaz-2022-03": {"formula": 2023, "kind": "demo",
                      "arkusz": f"{EXTRA}/pokazowe/Historia/MHIP-R0-100-2305.pdf",
                      "zasady": f"{EXTRA}/pokazowe/Historia/MHIP-R0-100-200-300-400-660-700-Q00-2203-zasady.pdf"},
    "probny-2026-01": {"formula": 2023, "kind": "mock",
                       "arkusz": f"{EXTRA}/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-A-2601-arkusz.pdf",
                       "zasady": f"{EXTRA}/probny_egzamin/2026_styczen/Historia/MHIP-R0-100-2601-zasady.pdf"},
    # formuła 2015, main May session
    "f15-2015-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2015/formula_od_2015/MHI-R1_1P-152.pdf",
                    "zasady": f"{B15}/2015/formula_od_2015/odpowiedzi/MHI-R1-N.pdf"},
    "f15-2016-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2016/formula_od_2015/MHI-R1_1P-162.pdf",
                    "zasady": f"{B15}/2016/formula_od_2015/zasady_oceniania/MHI-R1-N.pdf"},
    "f15-2017-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2017/formula_od_2015/historia/MHI-R1_1P-172.pdf",
                    "zasady": f"{B15}/2017/formula_od_2015/zasady_oceniania/MHI-R1-N.pdf"},
    "f15-2018-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2018/formula_od_2015/historia/MHI-R1_1P-182.pdf",
                    "zasady": f"{B15}/2018/formula_od_2015/Zasady_oceniania/MHI-R1_1P-182_zasady_oceniania.pdf"},
    "f15-2019-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2019/formula_od_2015/historia/MHI-R1_1P-192.pdf",
                    "zasady": f"{B15}/2019/formula_od_2015/Zasady_oceniania/MHI-R1_1P-192_model.pdf"},
    "f15-2020-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2020/formula_od_2015/historia/MHI-R1_1P-202.pdf",
                    "zasady": f"{B15}/2020/formula_od_2015/Zasady_oceniania/MHI-PR-202_zasady.pdf"},
    "f15-2021-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2021/Historia/poziom_rozszerzony/EHIP-R0-100-2105.pdf",
                    "zasady": f"{B15}/2021/Zasady_Oceniania/EHIP-R0-100-2105-zasady.pdf"},
    "f15-2022-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2022/Historia/poziom_rozszerzony/EHIP-R0-100-2205.pdf",
                    "zasady": f"{B15}/2022/Zasady_oceniania/EHIP-R0-100-2205-zasady.pdf"},
    "f15-2023-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2023/Historia/EHIP-R0-100-2305.pdf",
                    "zasady": f"{B15}/2023/Historia/EHIP-R0-100-2305-zasady.pdf"},
    "f15-2024-05": {"formula": 2015, "kind": "main",
                    "arkusz": f"{B15}/2024/Historia/EHIP-R0-100-A-2405-arkusz.pdf",
                    "zasady": f"{B15}/2024/Historia/EHIP-R0-100-2405-zasady.pdf"},
}
# More official CKE history papers with keys (found 26 Sep 2026 by crawling cke.gov.pl; every URL checked
# HTTP 200 + %PDF): formuła 2023 December mocks, formuła 2015 demo/mocks, formuła 2005 ("stara matura")
# May 2005-2020, June 2012, January 2006 and mocks. CKE publishes no June/August extended history papers
# for formuła 2015/2023. Training data only (set "extra"); never the held-out May 2023-2026 papers.
CKE = "https://cke.gov.pl/images"
B15 = f"{CKE}/_EGZAMIN_MATURALNY_OD_2015"
A15 = f"{B15}/Arkusze_egzaminacyjne"
M23 = f"{CKE}/_EGZAMIN_MATURALNY_OD_2023/materialy_dodatkowe"
ST = f"{CKE}/stories"

_EXTRA = {
    # ---------------------------------------------------------------- formula 2023: mocks
    # Diagnostic ("arkusze diagnostyczne") sets CKE ran for the new formula, December 2022 and December 2024.
    "probny-2022-12": {"formula": 2023, "kind": "mock",
                       "arkusz": f"{M23}/diagnostyczne_12/historia/MHIP-R0-100-2212.pdf",
                       "zasady": f"{M23}/diagnostyczne_12/historia/MHIP-R0-100-200-300-400-660-700-Q00-Z00-2212-zasady.pdf"},
    # Listed under formula 2023 "arkusze diagnostyczne grudzien 2024", but the files sit in the _OD_2015/Probny/2024 folder.
    "probny-2024-12": {"formula": 2023, "kind": "mock",
                       "arkusz": f"{B15}/Probny/2024/Historia/MHIP-R0-100-A-2412-arkusz.pdf",
                       "zasady": f"{B15}/Probny/2024/Historia/MHIP-R0-100-200-300-400-660-Q00-2412-zasady.pdf"},

    # ---------------------------------------------------------------- formula 2015: mocks / demo
    # "Przykladowy zestaw zadan" published December 2013 ahead of the 2015 exam (demo, A1 = standard version).
    "f15-pokaz-2013-12": {"formula": 2015, "kind": "demo",
                          "arkusz": f"{B15}/Przykladowe_arkusze/2015/historia_PR/historia_PR_A1.pdf",
                          "zasady": f"{B15}/Przykladowe_arkusze/2015/historia_PR/historia_model_PR_A1_A2_A3_A4_A7.pdf"},
    # Proba (probny) exam held 18 Dec 2014; cover says "przykladowy arkusz egzaminacyjny". A1 = standard version.
    "f15-probny-2014-12": {"formula": 2015, "kind": "mock",
                           "arkusz": f"{B15}/egzamin_probny_2015/historia_pr/A1Historia_PR_arkusz.pdf",
                           "zasady": f"{B15}/egzamin_probny_2015/historia_pr/A1A2A3A4A7Historia_PR_model_odpowiedzi.pdf"},
    # Online proba exam, April 2020 (1P = standard version).
    "f15-probny-2020-04": {"formula": 2015, "kind": "mock",
                           "arkusz": f"{B15}/Probny/2020/MHI-R1_1P.pdf",
                           "zasady": f"{B15}/Probny/2020/MHI-R1-zasady.pdf"},
    # Proba exam, March 2021 (EHIP, the 2021-2024 formula-2015 variant).
    "f15-probny-2021-03": {"formula": 2015, "kind": "mock",
                           "arkusz": f"{B15}/Probny/2021/EHIP-R0-100-2103.pdf",
                           "zasady": f"{B15}/Probny/2021/EHIP-R0-100-2103-zasady.pdf"},

    # ---------------------------------------------------------------- formula 2005 ("stara matura")
    # 2005-2006: the extended level was Arkusz I (shared with basic) + Arkusz II. Only Arkusz II is
    # extended-only, so these entries point at Arkusz II and its model answers.
    "f05-2005-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{ST}/Matura2005/hist_a2.pdf",
                    "zasady": f"{ST}/Matura_odp_2005/hist_a2_model.pdf"},
    # Diagnostic set of December 2005 ("material diagnostyczny"), Arkusz II.
    "f05-probny-2005-12": {"formula": 2005, "kind": "mock",
                           "arkusz": f"{ST}/arkusze05grudzien/mh_a2.pdf",
                           "zasady": f"{ST}/arkusze05grudzien/mh_model_a2.pdf"},
    # Winter session, January 2006 (code MHI-R1A1P-061): a real exam session, not a mock. Arkusz II.
    "f05-2006-01": {"formula": 2005, "kind": "main",
                    "arkusz": f"{ST}/Arkusz2006styczen/historia_a2.pdf",
                    "zasady": f"{ST}/Arkusz2006styczen/hist_mod_a2.pdf"},
    "f05-2006-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{ST}/Matura2006/a2_hist.pdf",
                    "zasady": f"{ST}/Matura2006/a2_hist_rozw.pdf"},
    # Proba matura, November 2006 (poziom rozszerzony).
    "f05-probny-2006-11": {"formula": 2005, "kind": "mock",
                           "arkusz": f"{ST}/06_mp/hist_pr.pdf",
                           "zasady": f"{ST}/06_mp/hist_oc_pr.pdf"},
    "f05-2007-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{ST}/mat2_07/his_pr.pdf",
                    "zasady": f"{ST}/mat2_07/his_pr_rozw.pdf"},
    "f05-2008-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2008/hist_pr.pdf",
                    "zasady": f"{A15}/2008/hist_pr_rozw.pdf"},
    # 2009 key is one PDF for both levels: poziom podstawowy pp. 1-18, poziom rozszerzony from p. 19.
    "f05-2009-05": {"formula": 2005, "kind": "main", "key_from_page": 19,
                    "arkusz": f"{A15}/2009/historia_pr.pdf",
                    "zasady": f"{A15}/2009/KLUCZE/historia.pdf"},
    "f05-2010-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2010/Historia/historia_pr.pdf",
                    "zasady": f"{A15}/2010/Historia/historia_klucz_pr.pdf"},
    "f05-2011-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2011/R/historia_pr.pdf",
                    "zasady": f"{A15}/2011/kryteria/historia_model_pr.pdf"},
    "f05-2012-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2012/maj/hist/historia_pr.pdf",
                    "zasady": f"{A15}/2012/maj/klucze/historia_pr_klucz.pdf"},
    "f05-2012-06": {"formula": 2005, "kind": "june",
                    "arkusz": f"{A15}/2012/czerwiec/historia/historia_pr.pdf",
                    "zasady": f"{A15}/2012/czerwiec/klucze/historia_06_pr_klucz.pdf"},
    "f05-2013-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2013/historia_PR.pdf",
                    "zasady": f"{A15}/2013/Kryteria-Oceniania/historia_model_PR.pdf"},
    "f05-2014-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2014/historia_PR_A1.pdf",
                    "zasady": f"{A15}/2014/odpowiedzi/Historia_PR.pdf"},
    # 2015-2020: formula 2005 was still sat by pre-2015 graduates ("formula_do_2014" folders). These are
    # different papers from the formula-2015 ones with the same code (e.g. MHI-R1_1P-162), per the
    # separate formula_do_2014 paths and "-S" (stara) vs "-N" (nowa) answer keys.
    "f05-2015-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2015/formula_do_2014/MHI-R1_1P-152.pdf",
                    "zasady": f"{A15}/2015/formula_do_2014/odpowiedzi/MHI-R1-S.pdf"},
    "f05-2016-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2016/formula_do_2014/MHI-R1_1P-162.pdf",
                    "zasady": f"{A15}/2016/formula_do_2014/zasady_oceniania/MHI-R1-S.pdf"},
    "f05-2017-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2017/formula_do_2014/historia/MHI-R1_1P-172.pdf",
                    "zasady": f"{A15}/2017/formula_do_2014/zasady_oceniania/MHI-R1-S.pdf"},
    "f05-2018-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2018/formula_do_2014/historia/MHI-R1_1P-182.pdf",
                    "zasady": f"{A15}/2018/formula_do_2014/Zasady_ocenienia/MHI-R1_1P-182_zasady_oceniania.pdf"},
    "f05-2019-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2019/formula_do_2014/historia/MHI-R1_1P-192.pdf",
                    "zasady": f"{A15}/2019/formula_do_2014/Zasady_ocenienia/MHI-R1_1P-192_model.pdf"},
    "f05-2020-05": {"formula": 2005, "kind": "main",
                    "arkusz": f"{A15}/2020/formula_do_2014/historia/MHI-R1_1R-202s.pdf",
                    "zasady": f"{A15}/2020/formula_do_2014/Zasady_oceniania/MHI-PR-202s_zasady.pdf"},
}

PAPERS.update(_EXTRA)

HEADLINE = [p for p, v in PAPERS.items() if v["formula"] == 2023 and v["kind"] == "main"]

IMG = "[ilustracja – niedostępna w wersji tekstowej]"
IMG_ID = re.compile(r"\[ilustracja – niedostępna w wersji tekstowej #(\d+)\]")  # pdf_lines' numbered marker


def is_img(ln: str) -> bool:
    return ln == IMG or bool(IMG_ID.fullmatch(ln))

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


def pdf_lines(path: Path, mark_images: bool, image_dir: Path | None = None) -> list[str]:
    """Text lines in reading order, with IMG markers where large pictures sit. With image_dir,
    each picture is also saved as <image_dir>/<pdf stem>-NNN.jpg (JPEG q85 keeps the upload small) and its marker carries #NNN."""
    import pymupdf

    out: list[str] = []
    n = 0
    for page in pymupdf.open(path):
        h = page.rect.height
        imgs = []
        if mark_images:
            for info in page.get_image_info():
                x0, y0, x1, y1 = info["bbox"]
                # Skip logos, barcodes and the margin score boxes.
                if (x1 - x0) * (y1 - y0) > 4000 and y0 < h * 0.93 and (x1 - x0) > 60:
                    imgs.append((y0, pymupdf.Rect(info["bbox"])))
        imgs.sort(key=lambda t: t[0])
        marks = []
        for _, rect in imgs:
            if image_dir is None:
                marks.append(IMG)
                continue
            n += 1
            image_dir.mkdir(parents=True, exist_ok=True)
            page.get_pixmap(clip=rect & page.rect, dpi=150).save(str(image_dir / f"{path.stem}-{n:03d}.jpg"), jpg_quality=85)
            marks.append(f"[ilustracja – niedostępna w wersji tekstowej #{n:03d}]")
        imgs = [y for y, _ in imgs]
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                text = "".join(s["text"] for s in line["spans"])
                y = line["bbox"][1]
                # Page headers/footers come first in content order; don't anchor pictures to them.
                while imgs and imgs[0] <= y and h * 0.07 < y < h * 0.93:
                    imgs.pop(0)
                    out.append(marks.pop(0))
                out.append(text)
        out.extend(marks)
    return out


# ---------------------------------------------------------------- cleaning

JUNK = [
    r"^\s*Strona \d+ z \d+\s*$", r"^\s*MHIP-R0_100\s*$", r"^\s*MHIP-R0-\d+", r"^\s*Układ graficzny",
    r"^\s*© CKE", r"^\s*BRUDNOPIS", r"^\s*\(nie podlega ocenie\)", r"^\s*[PF]\s*$",
    r"^\s*\d(\s*[–-]\s*\d+)+\s*[–-]?\s*$", r"^\s*\d+(\.\d+)?\.\s*$", r"^\s*(Próbny e|E)gzamin maturalny z historii",
    r"^\s*Zasady oceniania rozwiązań zadań\s*$", r"^\s*Wypełnia\s*$", r"^\s*egzaminator\s*$",
    r"^\s*Nr zadania", r"^\s*[A-Z]{3,4}-R\d_\d+", r"^\s*[ME]HIP?_\w+\s*$", r"^\s*(\d+\.\d+\.\s*){2,}$", r"^\s*\d\s*$", r"^\s*Maks\. liczba", r"^\s*Uzyskana liczba",
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
        if ln == IMG and out and out[-1] == IMG:  # numbered markers stay: each is its own picture
            continue
        out.append(ln)
    return out


BREAK_BEFORE = re.compile(r"^([A-F]\.|\d+\.|\d+\)|[•–-] |Źródło|Fragment|Rozstrzygnięcie|Uzasadnienie|Na podstawie|"
                          r"Przykładow|Podobieństwo|Różnica|Nazwa|Wydarzenie|Opis|\[ilustracja|[A-ZĄĆĘŁŃÓŚŹŻ][^ ]* –)")


def join(lines: list[str]) -> str:
    """Re-flows lines the PDF wrapped mid-sentence; keeps list items and labels on their own lines."""
    out: list[str] = []
    for ln in lines:
        if out and not BREAK_BEFORE.match(ln) and not is_img(out[-1]) and not is_img(ln) \
                and not re.search(r"[:.;!?…]$", out[-1]) and len(out[-1]) > 40:
            if out[-1].endswith("-") and ln.startswith("-"):   # CKE's "polsko-\n-krzyżackie"
                out[-1] = out[-1] + ln[1:]
            else:
                out[-1] = out[-1] + " " + ln
        else:
            out.append(ln)
    return "\n".join(out).strip()


# ---------------------------------------------------------------- splitting

HEADER = re.compile(r"^Zadanie\.? (\d+)(?:\.(\d+))?\.?(?=\s|$|\()\s*(?:\(0\s*[–-]\s*(\d+)\))?\s*(.*)$")


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

KEY_START = re.compile(r"^(Rozwiązani[ea]|Odpowiedź:|Przykładow\w+ (odpowied|rozwiąz|realizacj|argument)|(Poprawn|Prawidłow)\w+ (odpowied|rozwiąz))", re.I)
KEY_LABEL = re.compile(r"^(Rozwiązani[ea]|Przykładow\w+ (odpowied|rozwiąz)\w*|(Poprawn|Prawidłow)\w+ (odpowied|rozwiąz)\w*)\s*:?\s*$", re.I)
RUBRIC_START = re.compile(r"^(Zasady oceniania|Schemat (punktowania|oceniania))\b")
FOOTNOTE = re.compile(r"^(\d\s*)?Rozporządzenie Ministra|^\(Dz\.\s?U\.|^programowej kształcenia|^Załącznik nr", re.I)


def key_items(lines: list[str]) -> dict[str, dict]:
    keys = {}
    for t in split_tasks(lines):
        if t["points"] is None:
            continue
        body = [ln for ln in t["lines"] if not FOOTNOTE.search(ln)]
        rub_i = next((i for i, ln in enumerate(body) if RUBRIC_START.match(ln)), None)
        sol_i = next((i for i, ln in enumerate(body) if KEY_START.match(ln)), None)
        rubric, solution = [], []
        if rub_i is not None:   # rubric runs to the solution if that follows it, else to the end
            rubric = body[rub_i + 1: sol_i if sol_i is not None and sol_i > rub_i else None]
        if sol_i is not None:   # formuła 2015 keys put the solution before the rubric
            solution = body[sol_i: rub_i if rub_i is not None and rub_i > sol_i else None]
        if solution and KEY_LABEL.match(solution[0]):
            solution = solution[1:]
        if not rubric and not solution:   # essays: the criteria come under their own headings
            rubric = [ln for ln in body if not re.match(r"^Wymagani[ea]", ln)]
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
        part = re.sub(r"\([^)]*\)", "", part)
        opts = re.findall(r"\[[^\]]*\]", part)
        # every combination of the optional [..] words: "Jan [II] Kazimierz" -> "Jan Kazimierz", "Jan II Kazimierz"
        for mask in range(2 ** min(len(opts), 3)):
            v, n = part, 0
            for j, o in enumerate(opts):
                v = v.replace(o, o[1:-1] if j < 3 and mask >> j & 1 else "", 1)
            out.append(re.sub(r"\s+", " ", v))
    out = [x.strip(" .,;:") for x in out]
    return list(dict.fromkeys(x for x in out if len(x) > 1))


def closed_gold(cat: str, solution: str) -> str | None:
    s = solution.strip()
    first = re.sub(r"^(Rozstrzygnięcie|Odpowiedź):\s*", "", s.splitlines()[0]).strip() if s else ""
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
        pairs = re.findall(r"^(\d+)\.?\s*[–-]\s*([A-F])\.?\s*$", s, re.M)
        return ", ".join(f"{a} – {b}" for a, b in pairs) if pairs else None
    return None


def pair_keywords(solution: str) -> list[list[str]] | None:
    """For keys that are a short list of 'label – value' lines, one keyword group per line."""
    lines = [ln for ln in solution.splitlines() if ln.strip()]
    if not 1 <= len(lines) <= 6:
        return None
    groups = []
    for ln in lines:
        m = re.match(r"^(?:Fragment |Opis |Dokument |Źródło )?([A-F1-9]|[A-ZĄĆĘŁŃÓŚŹŻ]\w+(?: \w+){0,2})\.?\s*[–-]\s*(.+)$", ln) \
            or re.match(r"^(?:Tekst )?([A-F])\.?\s*[–-]?\s+(.+)$", ln)
        if not m or len(m[2]) > 80:
            if len(lines) <= 4 and len(ln.split()) <= 5 and not re.match(r"^(Rozstrzygnięcie|Przykładow|Nazwa|•)", ln) \
                    and ":" not in ln:
                groups.append(alts(ln))     # a plain list: one answer per line
                continue
            return None
        label, value = m[1], m[2].strip().rstrip(".")
        if (short := re.search(r"\b([A-F1-9])$", label)):   # "Tekst A" -> "A"
            label = short[1]
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


def strip_ids(text: str, image_dir: Path | None, stem: str) -> tuple[str, list[str]]:
    """Numbered markers -> the plain placeholder (consecutive ones merged, as before), plus the
    JPEG paths they stood for, relative to the repo root."""
    paths = []
    if image_dir is not None:
        for num in IMG_ID.findall(text):
            f = image_dir / f"{stem}-{num}.jpg"
            paths.append(str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f))
    text = IMG_ID.sub(IMG, text)
    text = re.sub(rf"({re.escape(IMG)})(\n{re.escape(IMG)})+", r"\1", text)
    return text, paths


def build_row(paper: str, url: str, it: dict, key: dict | None, image_dir: Path | None = None,
              stem: str = "") -> dict:
    ctx, q = join(it["context"]), join(it["question"])
    ctx, ctx_imgs = strip_ids(ctx, image_dir, stem)
    q, q_imgs = strip_ids(q, image_dir, stem)
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
    if ctx_imgs or q_imgs:
        row["images"] = ctx_imgs + q_imgs   # PNGs of the pictures, for vision models (--images)
    row.update({
        "needs_image": bool(needs_image),
        "visuals": visuals,
        "rubric": key["rubric"] if key else "",
        "paper": paper,
        "year": int(re.search(r"20\d\d", paper)[0]),
        "formula": PAPERS[paper]["formula"],
        "kind": PAPERS[paper]["kind"],
        "source_url": url,
    })
    if not key:
        row["warning"] = "no answer key found"
    elif not solution and cat != "essay":
        row["warning"] = "answer key is an image in the PDF; not machine-readable"
    return row


# ---------------------------------------------------------------- formuła 2005 ("stara matura")
# Task headers read "Zadanie 5. (2 pkt)". In the source-analysis part the sources ("Źródło A", ...) are
# printed once, and each task names the ones it uses in a line just above its header ("na podstawie
# źródeł B i C"). The answer keys come in three layouts: a table with a task-number column (2005-2006
# Arkusz II and the 2005/2006 mocks), the paper itself with the answers printed in blue (May 2006-2008),
# and "Zadanie 5. (0–2)" sections much like formuła 2015 (2009 onward).

HEADER05 = re.compile(r"^Zadanie\.? ?(\d+)(?:\.(\d+))?\.?\s*(?:\((\d+)\s*pkt\.?\s*\)|\(0\s*[–-]\s*(\d+)\))?\s*(.*)$")
JUNK05 = re.compile(r"^(Poziom rozszerzony|Arkusz I+|ARKUSZ I+|ARKUSZ ODPOWIEDZI|Wypełnia egzaminator!?|.*egzaminator!.*|"
                    r"(Klucz punktowania|Kryteria oceniania) odpowiedzi( [–-] poziom rozszerzony)?|Historia [–-] poziom rozszerzony|"
                    r"\d+\.[A-F]\.?|Uzyskana liczba pkt|Egzamin maturalny|Nr zad\.?|Punkty|Wypełnia sprawdzający|"
                    r"(\d+ )?Materiał pomocniczy do doskonalenia nauczycieli.*|Historia [–-] grudzień 2005 r\.)$")
SRC05 = re.compile(r"^(?:Źródło|ŹRÓDŁO) ([A-ZĄĆĘŁŃÓŚŹŻ])(?:[.:]?\s|[.:]?$)")
INTRO05 = re.compile(r"^[Nn]a podstawie (?!:)(?!.*\d{4})"
                     r"(?=.*(źród|ilustracj|tekst|map|tabel|wykres|schemat|fotografi|rysun|plakat|karykatur|wiedzy))")
SECTION05 = re.compile(r"^(CZĘŚĆ|Część) [IV]+\b|^ZADANI[EA] [A-ZĄĆĘŁŃÓŚŹŻ]{3,}|^(I|II|III|IV|V|VI)\. [A-ZĄĆĘŁŃÓŚŹŻ ]{4,}|"
                       r"^TEST SPRAWDZAJĄCY|^W STANDARDACH WYMAGAŃ|^OD ROZBIORÓW|^\(\d+ punktów\)$|^Temat( arkusza)?:|^TEMAT:")
CITE05 = re.compile(r"^(\[w:\]|\[za:\]|Źródła?: |Na podstawie: |Za: |Opracowano na podstawie|Oprac\. na podstawie)", re.I)
INSTR05 = re.compile(r"^(?:[A-F]\.\s*|[a-f]\)\s*)?(?:" + INSTR.pattern[2:-1] + r"|Podkreśl|Przeanalizuj|Przeczytaj|Odpowiedz|"
                     r"Zaproponuj|Zinterpretuj|Zidentyfikuj|Uzasadnij|Wyjaśnij|Sformułuj|Zakreśl|Oceń|Rozważ|Otocz|Połącz)")


def clean05(lines: list[str]) -> list[str]:
    """clean() plus the old papers' page furniture: running heads, answer-box labels, page numbers."""
    lines = [re.sub(r"^[\uf000-\uf0ff\x83]\s*", "• ", ln.replace("\u00a0", " ").strip()) for ln in lines]
    lines = [ln for ln in clean(lines) if not JUNK05.match(ln) and ln != "•"]
    out: list[str] = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        prv = out[-1] if out else ""
        if re.fullmatch(r"\d{1,2}", ln):   # page number: next to a header, intro, answer blank or running text
            if HEADER05.match(nxt) or INTRO05.match(nxt) or SECTION05.match(nxt) or SRC05.match(nxt) or PART05.match(nxt) \
                    or prv.endswith("…") or HEADER05.match(prv) \
                    or (len(prv) > 15 and len(nxt) > 15 and re.search(r"[a-ząćęłńóśźż]{3}", prv + nxt)):
                continue
        # justified lines the PDF broke into one word per line: "Uporządkuj / chronologicznie / wydarzenia"
        if out and " " not in ln and re.match(r"[a-ząćęłńóśźż]", ln) and not is_img(prv) \
                and not re.search(r"[.:;!?…]$", prv) and (" " not in prv or " " not in nxt) \
                and re.match(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż„(]", prv) and not HEADER05.match(prv):
            out[-1] = prv + " " + ln
            continue
        out.append(ln)
    return out


def _letters(intro: str) -> list[str]:
    return re.findall(r"(?<!\w)([A-ZĄĆĘŁŃÓŚŹŻ])(?!\w)", intro.split("podstawie", 1)[-1])


def split_question05(lines: list[str]) -> tuple[list[str], list[str]]:
    """Sources, then the instruction: the first instruction line after the last source citation.
    Tasks that put the instruction before the source keep the whole block as the question."""
    def instr(ln: str) -> bool:   # "Na podstawie źródeł wykonaj polecenie." leads in to the sources
        return bool(INSTR05.match(ln)) and not re.search(r"wykonaj polecen", ln)

    last = max((i for i, ln in enumerate(lines) if CITE05.match(ln)), default=-1)
    for i in range(last + 1, len(lines)):
        if instr(lines[i]):
            return lines[:i], lines[i:]
    if last >= 0:
        return [], lines
    for i, ln in enumerate(lines):
        if instr(ln):
            return lines[:i], lines[i:]
    return [], lines


def paper_items05(lines: list[str]) -> list[dict]:
    n = len(lines)
    hdr = [bool(HEADER05.match(ln)) for ln in lines]
    intro = {i for i in range(n - 1) if INTRO05.match(lines[i]) and hdr[i + 1]}
    wanted = {c for i in intro for c in _letters(lines[i])}
    # Shared sources: each "Źródło X" that some intro line names runs to the next source, intro, header or section.
    sources: dict[str, list[tuple[int, int, list[str]]]] = {}
    drop, section = set(), 0
    sec_at = [0] * n
    for i, ln in enumerate(lines):
        if SECTION05.match(ln):
            section += 1
        sec_at[i] = section
    for i, ln in enumerate(lines):
        m = SRC05.match(ln)
        if not m or m[1] not in wanted or i in drop:
            continue
        j = i + 1
        while j < n and not (hdr[j] or j in intro or SRC05.match(lines[j]) or SECTION05.match(lines[j])):
            j += 1
        sources.setdefault(m[1], []).append((i, sec_at[i], lines[i:j]))
        drop.update(range(i, j))

    def sources_for(intro_line: str, at: int) -> list[str]:
        out = []
        letters = [c for c in dict.fromkeys(_letters(intro_line)) if c in sources]
        if not letters and re.search(r"źródeł|źródła\b", intro_line):   # "na podstawie źródeł oraz wiedzy"
            before = [s for spans in sources.values() for s in spans if s[0] < at]
            if before:
                sec = max(before)[1]
                return [ln for s in sorted(before) if s[1] == sec for ln in s[2]]
        for c in letters:
            spans = [s for s in sources[c] if s[0] < at] or sources[c]
            out += spans[-1][2]
        return out

    tasks, cur, after_section = [], None, False
    for i, ln in enumerate(lines):
        # a section title and its wrapped all-caps second line ("WŁADZY MONARSZEJ")
        if SECTION05.match(ln) or after_section and not re.search(r"[a-ząćęłńóśźż]", ln) and re.search(r"[A-Z]{2}", ln):
            after_section, cur = True, None   # what follows a section title is the next part's preamble
            continue
        after_section = False
        if i in drop or i in intro:
            continue
        m = HEADER05.match(ln)
        if m:
            pts = m[3] or m[4]
            intro_line = lines[i - 1] if i - 1 in intro else ""
            cur = {"num": int(m[1]), "sub": int(m[2]) if m[2] else None, "points": int(pts) if pts else None,
                   "lines": [m[5].strip()] if m[5].strip() else [], "intro": intro_line,
                   "sources": sources_for(intro_line, i) if intro_line else [], "at": i}
            tasks.append(cur)
        elif cur is not None:
            cur["lines"].append(ln)

    # A task without its own intro line uses the sources its text names ("w źródle A"), or else the
    # previous task's: the intro above a run of tasks covers all of them.
    for prev, t in zip([None] + tasks, tasks):
        if t["intro"] or t["points"] is None or t["points"] >= 10:
            continue
        text = " ".join(t["lines"])
        named = [c for m in re.finditer(r"źród\w*((?:\s*(?:,|i|oraz)?\s*[A-ZĄĆĘŁŃÓŚŹŻ](?!\w))+)", text)
                 for c in _letters("podstawie" + m[1]) if c in sources]
        if named:
            t["sources"] = sources_for("podstawie " + ", ".join(dict.fromkeys(named)), t["at"])
        elif prev is not None and prev["sources"] and prev["points"] is not None:
            t["sources"] = list(prev["sources"])
    items, shared, shared_num, group_intro = [], [], None, ""
    for t in tasks:
        if t["points"] is None:          # "Zadanie 5." group header: shared sources
            shared, shared_num, group_intro = t["sources"] + list(t["lines"]), t["num"], t["intro"]
            continue
        lead, q = split_question05(t["lines"]) if t["points"] < 10 else ([], t["lines"])
        if t["sub"] is not None and shared_num == t["num"]:
            ctx = t["sources"] + shared + lead
            intro_line = t["intro"] or group_intro
        else:
            shared, shared_num, group_intro = [], None, ""
            ctx, intro_line = t["sources"] + lead, t["intro"]
        if intro_line:
            q = [intro_line[0].upper() + intro_line[1:].rstrip(" .:") + ":"] + q
        qid = f"{t['num']}.{t['sub']}" if t["sub"] else f"{t['num']}"
        items.append({"task": qid, "points": t["points"], "context": ctx, "question": q})
    return items


def _key_lines05(path: Path, first_page: int = 1) -> list[tuple[str, str]]:
    """(line text, its blue part) in reading order, from first_page on."""
    import pymupdf

    out = []
    doc = pymupdf.open(path)
    for page in doc.pages(first_page - 1):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                sp = line["spans"]
                out.append(("".join(s["text"] for s in sp), "".join(s["text"] for s in sp if s["color"] == 0x0000FF)))
    return out


def _key(points: int | None, solution: list[str], rubric: list[str]) -> dict:
    return {"points": points, "solution": join(solution), "rubric": join(rubric)}


SOL05 = re.compile(r"^((?:Poprawn|Prawidłow|Przykład|Możliw|Wzorcow)\w*(?: [\wąćęłńóśźż]+){0,6}|Odpowiedź|Rozwiązanie)"
                   r"\s*(?::\s*(.*))?$")
STOP05 = re.compile(r"^(Przykład\w* (błędn|niepoprawn|niepełn|odpowiedzi błędn)|Błędn\w* odpowied|Obszar standardów|"
                    r"Opis wymagań|Korzystanie z informacji|Tworzenie informacji|Wiadomości i rozumienie|"
                    r"Schemat punktowania|Zasady oceniania|Wymagani[ea] (ogóln|szczegół))")
SCORE05 = re.compile(r"^(\d+\s*(p\.|pkt\.?|punkt\w*|p)\s*[–-]|Zdający otrzymuje|Uwaga)")
PART05 = re.compile(r"^([A-F])\.\s*(?:\(0\s*[–-]\s*\d+\))?\s*$")


def key_text05(raw: list[str]) -> dict[str, dict]:
    """Keys laid out as "Zadanie 5. (0–2)" sections (2009 onward). 2009 puts the "0–2" on its own line."""
    raw = [ln.replace("\u00a0", " ").strip() for ln in raw]
    for i, ln in enumerate(raw):
        m = HEADER05.match(ln)
        if m and not (m[3] or m[4]):
            pts, parts = [], 0
            for j in range(i + 1, min(i + 80, len(raw))):
                if HEADER05.match(raw[j]):
                    break
                parts += bool(PART05.match(raw[j]))
                if (p := re.fullmatch(r"0\s*[–-]\s*(\d+)", raw[j])):
                    pts.append(int(p[1]))
            if pts:   # "Zadanie 8." with parts A. (0–1) and B. (0–1) is worth 2
                total = sum(pts) if parts else pts[0]
                raw[i] = f"Zadanie {m[1]}{'.' + m[2] if m[2] else ''}. (0–{total}) {m[5]}".strip()
    blocks = []
    for ln in clean05(raw):
        m = HEADER05.match(ln)
        if m:
            pts = m[3] or m[4]
            if not pts and blocks and blocks[-1]["num"] == int(m[1]):   # the essay criteria run on
                continue
            blocks.append({"num": int(m[1]), "sub": m[2], "points": int(pts) if pts else None, "body": []})
        elif blocks:
            blocks[-1]["body"].append(ln)
    keys = {}
    for b in blocks:
        if b["points"] is None:
            continue
        qid = f"{b['num']}.{b['sub']}" if b["sub"] else f"{b['num']}"
        if b["points"] >= 10:
            keys["essay"] = _key(b["points"], [], b["body"])
            continue
        parts, rubric, state, label = [], [], "pre", ""
        body = b["body"]
        for i, ln in enumerate(body):
            if (m := PART05.match(ln)):
                nxt = body[i + 1] if i + 1 < len(body) else ""
                if state == "sol" and (not nxt or SCORE05.match(nxt)):
                    parts[-1][1].append(ln)          # "Poprawna odpowiedź / B." is the answer itself
                elif state == "sol" and not parts[-1][1]:
                    parts[-1] = (m[1], [])           # "Przykłady poprawnych odpowiedzi: / A. / • ..."
                    label = m[1]
                elif state == "sol":
                    label = m[1]
                    parts.append((label, []))
                else:
                    label, state = m[1], "pre"
                continue
            if STOP05.match(ln):
                state = "stop"
                continue
            if SCORE05.match(ln):
                state = "rub"
                rubric.append((f"{label}. " if label else "") + ln)
                continue
            m = SOL05.match(ln)
            if m and not (parts and parts[-1][0] == label and state == "sol"):
                state = "sol"
                parts.append((label, []))
                if m[2]:
                    parts[-1][1].append(m[2])
                continue
            if state == "sol":
                parts[-1][1].append(ln)
            elif state == "rub":
                rubric.append(ln)
        rubric = [re.sub(r"\s*Część [IV]+$", "", r) for r in rubric]
        if not any(ls for _, ls in parts):   # 2010: the answer is only in the scoring line, "1 p. – za ... (zdanie nr 1)"
            top = [r for r in rubric if re.match(rf"^{b['points']}\s*p", r) and "(" in r]
            if len(top) == 1:
                parts = [("", [re.sub(r"^\d+\s*p\.?\s*[–-]\s*(za\s+)?", "", top[0])])]
        sol = []
        for lab, ls in parts:
            if ls:
                sol += [(f"{lab}. " if lab and not ls[0].startswith(f"{lab}.") else "") + ls[0]] + ls[1:]
        keys[qid] = _key(b["points"], sol, rubric)
        # a few headers misprint the maximum ("Zadanie 18. (0–2)" over "1 p. – za prawidłową odpowiedź")
        keys[qid]["rubric_max"] = max((int(x[1]) for r in rubric if (x := re.match(r"^(?:[A-F]\. )?(\d+)\s*p", r))),
                                      default=None)
    return keys


def key_blue05(raw: list[tuple[str, str]]) -> dict[str, dict]:
    """Keys that are the paper with the answers filled in blue (May 2006-2008)."""
    blocks, cur, label = [], None, ""
    for text, blue in raw:
        text, blue = re.sub(r"\s+", " ", text).strip(), re.sub(r"\s+", " ", blue).strip()
        m = HEADER05.match(text)
        if m and not blue:
            pts = m[3] or m[4]
            cur = {"num": int(m[1]), "sub": m[2], "points": int(pts) if pts else None, "lines": []}
            blocks.append(cur)
            label = ""
            continue
        if cur is None:
            continue
        if not blue:
            if (lm := re.match(r"^([A-F])\.\s+\S", text)):
                label = lm[1]
            continue
        black = text.replace(blue, "", 1).strip() if blue in text else ""
        if black and len(black) <= 25:
            cur["lines"].append(text)           # "A. 3", "Tytuł mapy: ..."
        else:
            cur["lines"].append((f"{label}. " if label else "") + blue)
        label = ""
    keys = {}
    for b in blocks:
        if b["points"] is None or not b["lines"]:
            continue
        lines = clean05(b["lines"])
        if b["points"] >= 10:
            prev = keys["essay"]["rubric"] + "\n" if "essay" in keys else "Przykładowe realizacje tematów (CKE):\n"
            keys["essay"] = {"points": b["points"], "solution": "", "rubric": prev + join(lines)}
        else:
            keys[f"{b['num']}.{b['sub']}" if b["sub"] else f"{b['num']}"] = _key(b["points"], lines, [])
    return keys


def _cell_lines(cell: str) -> list[str]:
    out: list[str] = []
    for ln in cell.split("\n"):
        ln = re.sub(r"^[\uf000-\uf0ff\x83]\s*", "• ", ln.strip())
        if out and re.search(r"\w-$", out[-1]) and re.match(r"[a-ząćęłńóśźż]", ln):
            out[-1] = out[-1][:-1] + ln                       # "lud-\nności"
        elif ln:
            out.append(ln)
    return out


def key_table05(path: Path) -> dict[str, dict]:
    """Keys laid out as a table: task number | [part] | model answer | partial points | task points."""
    import pymupdf

    keys, cur, last_page = {}, None, None
    doc = pymupdf.open(path)
    for pno, page in enumerate(doc):
        for tab in page.find_tables().tables:
            if tab.col_count < 4:
                continue
            part_col = tab.col_count >= 5
            for row in tab.extract():
                cells = [(c or "").strip() for c in row]
                ans = cells[2 if part_col else 1]
                num = re.fullmatch(r"(\d+)\.?", cells[0])
                if cells[0] and not num or not ans:
                    continue
                if num:
                    pts = re.search(r"\d+", cells[-1])
                    cur = {"points": int(pts[0]) if pts else None, "sol": [], "rub": []}
                    keys[num[1]] = cur
                    last_page = pno
                elif cur is None:
                    continue
                lines = _cell_lines(ans)
                part = cells[1] if part_col else ""
                if re.fullmatch(r"[A-F]\.?", part):
                    lines[0] = f"{part.rstrip('.')}. {lines[0]}"
                cur["sol"] += lines
                partial = " ".join(_cell_lines(cells[-2]))
                if partial and not re.fullmatch(r"\d+ (pkt|punkt\w*)", partial):
                    cur["rub"].append(partial)
    keys = {k: _key(v["points"], v["sol"], v["rub"]) for k, v in keys.items()}
    if last_page is not None:   # the essay criteria follow the table
        essay = [ln for page in list(doc)[last_page + 1:] for ln in page.get_text().split("\n")]
        essay = clean05(essay)
        if essay:
            keys["essay"] = _key(20, [], essay)
    return keys


def key_items05(path: Path, first_page: int = 1) -> dict[str, dict]:
    raw = _key_lines05(path, first_page)
    blue = sum(len(b) for _, b in raw)
    if blue > 0.2 * sum(len(t) for t, _ in raw):
        return key_blue05(raw)
    text = [t for t, _ in raw]
    if sum(bool(re.match(r"Zadanie \d+(\.\d+)?\.\s*(\(|$)", re.sub(r"\s+", " ", t).strip())) for t in text) >= 3:
        return key_text05(text)
    return key_table05(path)


def split_subitems05(it: dict, keys: dict[str, dict]) -> list[dict]:
    """2015-2020 papers print sub-questions "2.1. ...", "2.2. ..." inside one "Zadanie 2. (3 pkt)",
    while the key scores them separately. Split when the key's parts add up to the task's points."""
    num = it["task"]
    subs = sorted((k for k in keys if k.startswith(num + ".")), key=lambda k: int(k.split(".")[1]))
    if num in keys or not subs or sum(keys[k]["points"] for k in subs) != it["points"]:
        return [it]
    lines = it["context"] + it["question"]
    marks = []
    for k in subs:
        i = next((i for i, ln in enumerate(lines) if ln.startswith(k + ". ")), None)
        if i is None or (marks and i <= marks[-1]):
            return [it]
        marks.append(i)
    out, shared = [], lines[:marks[0]]
    for j, (k, i) in enumerate(zip(subs, marks)):
        block = lines[i: marks[j + 1] if j + 1 < len(marks) else None]
        block[0] = block[0][len(k) + 2:]
        q, extra = trailing_sources(block)
        out.append({"task": k, "points": keys[k]["points"], "context": list(shared), "question": q})
        shared = shared + extra
    return out


def build05(paper: str, urls: dict, ark: Path, zas: Path, image_dir: Path | None) -> list[dict]:
    """formuła 2005: only items whose key is found and agrees on the points are kept."""
    items = paper_items05(clean05(pdf_lines(ark, mark_images=True, image_dir=image_dir)))
    keys = key_items05(zas, urls.get("key_from_page", 1))
    essay = keys.pop("essay", None)
    if essay:
        for it in items:
            if it["points"] >= 10:
                keys[it["task"]] = essay
    items = [sub for it in items for sub in split_subitems05(it, keys)]
    # a misnumbered key (2019: item 8 scored as "Zadanie 8.2."): pair when it is the only one either way
    missing = [it for it in items if it["task"] not in keys]
    spare = [k for k in keys if k not in {it["task"] for it in items}]
    if len(missing) == 1 and len(spare) == 1 and keys[spare[0]]["points"] == missing[0]["points"]:
        keys[missing[0]["task"]] = keys.pop(spare[0])
    rows, unpaired = [], []
    for it in items:
        k = keys.get(it["task"])
        if k is not None and k["points"] != it["points"] and k.get("rubric_max") == it["points"]:
            k = dict(k, points=it["points"])
        if k is None:
            unpaired.append(f"{it['task']} (no key)")
        elif k["points"] != it["points"]:
            unpaired.append(f"{it['task']} (key {k['points']} pkt, paper {it['points']} pkt)")
        elif not k["rubric"] if it["points"] >= 10 else not k["solution"]:
            unpaired.append(f"{it['task']} (no answer in the key)")
        elif not it["question"]:
            unpaired.append(f"{it['task']} (no question text)")
        else:
            rows.append(build_row(paper, urls["arkusz"], it, k, image_dir, ark.stem))
    extra = sorted(set(keys) - {it["task"] for it in items}, key=lambda s: [int(x) for x in s.split(".")])
    print(f"{paper}: {len(rows)} items, {sum(r['points'] for r in rows)} points"
          + (f", skipped {unpaired}" if unpaired else "")
          + (f", keys without item {extra}" if extra else ""), file=sys.stderr)
    return rows


# ---------------------------------------------------------------- main


def build(paper: str, raw: Path, image_dir: Path | None = None) -> list[dict]:
    urls = PAPERS[paper]
    ark = download(urls["arkusz"], raw / f"{paper}-arkusz.pdf")
    zas = download(urls["zasady"], raw / f"{paper}-zasady.pdf")
    if urls["formula"] == 2005:
        return build05(paper, urls, ark, zas, image_dir)
    items = paper_items(clean(pdf_lines(ark, mark_images=True, image_dir=image_dir)))
    keys = key_items(clean(pdf_lines(zas, mark_images=False)))
    # CKE sometimes numbers the essay differently in the key (2025: item 25, key 26).
    missing = [it for it in items if it["task"] not in keys]
    spare = [k for k in keys if k not in {it["task"] for it in items}]
    if len(missing) == 1 and len(spare) == 1 and keys[spare[0]]["points"] == missing[0]["points"]:
        keys[missing[0]["task"]] = keys.pop(spare[0])
    rows = [build_row(paper, urls["arkusz"], it, keys.get(it["task"]), image_dir, ark.stem) for it in items]
    total = sum(r["points"] for r in rows)
    missing = [it["task"] for it in items if it["task"] not in keys]
    extra = sorted(set(keys) - {it["task"] for it in items})
    print(f"{paper}: {len(rows)} items, {total} points"
          + (f", no key for {missing}" if missing else "")
          + (f", keys without item {extra}" if extra else ""), file=sys.stderr)
    return rows


SETS = {
    "headline": HEADLINE,                                                   # current format, real May exams
    "formula2023": [p for p, v in PAPERS.items() if v["formula"] == 2023],  # + demo and mock papers
    "formula2015": [p for p, v in PAPERS.items() if v["formula"] == 2015],
    "all": list(PAPERS),
    "extra": list(_EXTRA),
}
AUTO_TYPES = {"closed_choice", "true_false", "chronology", "matching"}


def auto_scorable(r: dict) -> bool:
    return bool((r.get("gold") and r["category"] in AUTO_TYPES) or r.get("gold_keywords"))


def _shingles(s: str, n: int = 5) -> set[str]:
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def mark_duplicates(rows: list[dict]) -> list[dict]:
    """Old-format (EHIP) papers sat on the same day as the new ones (MHIP) reuse their tasks.

    A formuła 2015 item whose question and context mostly repeat a formuła 2023 item gets
    `duplicate_of`, so a full-set score doesn't count the same task twice.
    """
    new = [(r["id"], _shingles(r["question"]), _shingles(r["context"])) for r in rows if r["formula"] == 2023]
    for r in rows:
        if r["formula"] != 2015:
            continue
        q, c = _shingles(r["question"]), _shingles(r["context"])
        for rid, nq, nc in new:
            if q and len(q & nq) / len(q) > 0.6 and (not c or len(c & nc) / len(c) > 0.5):
                r["duplicate_of"] = rid
                break
    return rows


def report(rows: list[dict]) -> str:
    """Markdown table: one line per paper."""
    out = ["| paper | formuła | items | points | auto-scorable items (points) | needs image | types |",
           "|---|---|---|---|---|---|---|"]
    for paper in dict.fromkeys(r["paper"] for r in rows):
        rs = [r for r in rows if r["paper"] == paper]
        auto = [r for r in rs if auto_scorable(r)]
        cats = Counter(r["category"] for r in rs)
        out.append(f"| {paper} | {rs[0]['formula']} | {len(rs)} | {sum(r['points'] for r in rs)} | "
                   f"{len(auto)} ({sum(r['points'] for r in auto)}) | {sum(r['needs_image'] for r in rs)} | "
                   + ", ".join(f"{k} {v}" for k, v in cats.most_common()) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--papers", default="headline",
                    help=f"a set ({', '.join(SETS)}) or comma-separated paper ids, e.g. 2024-05,f15-2019-05")
    ap.add_argument("--raw-dir", default=str(ROOT / "data/raw/cke"))
    ap.add_argument("-o", "--out", default=None,
                    help="default: data/eval/matura.jsonl for headline, data/eval/matura_<set>.jsonl otherwise")
    ap.add_argument("--text-only", action="store_true", help="drop items that need an image")
    ap.add_argument("--keep-duplicates", action="store_true",
                    help="keep formuła 2015 items that repeat a formuła 2023 item (the 2023/2024 papers share tasks)")
    ap.add_argument("--images", nargs="?", const=str(ROOT / "data/eval/images"),
                    help="save the papers' pictures as PNGs here (default data/eval/images) and list them "
                         "per item in `images`, for vision models; CKE content, so not committed")
    ap.add_argument("--report", help="also write the per-paper table (markdown) here")
    args = ap.parse_args()

    papers = SETS.get(args.papers) or [p.strip() for p in args.papers.split(",")]
    rows = []
    for p in papers:
        rows += build(p, Path(args.raw_dir), Path(args.images).resolve() if args.images else None)
    rows = mark_duplicates(rows)
    if not args.keep_duplicates:
        rows = [r for r in rows if "duplicate_of" not in r]
    if args.text_only:
        rows = [r for r in rows if not r["needs_image"]]
    default = "matura.jsonl" if args.papers == "headline" else f"matura_{args.papers.replace(',', '_')}.jsonl"
    out = Path(args.out or ROOT / "data/eval" / default)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    table = report(rows)
    if args.report:
        Path(args.report).write_text(table + "\n", encoding="utf-8")
    cats = Counter(r["category"] for r in rows)
    print(table, file=sys.stderr)
    print(f"wrote {len(rows)} items ({sum(r['points'] for r in rows)} points) to {out}", file=sys.stderr)
    print(f"  by type: {dict(cats)}", file=sys.stderr)
    print(f"  auto-scorable: {sum(map(auto_scorable, rows))}, needs image: {sum(r['needs_image'] for r in rows)}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
