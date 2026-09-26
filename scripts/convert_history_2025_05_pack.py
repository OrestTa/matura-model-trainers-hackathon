#!/usr/bin/env python3
"""Convert CKE MHIP-R0-100-A-2505 (Historia rozszerzona, maj 2025) into
Tarasiuk Lab official mock pack format (separate-text-and-images-v1).

Mirrors convert_history_2024_05_pack.py. Does NOT touch history-2023-mock-v1
or history-2024-05. Does NOT copy PDFs into the pack.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ARKUSZ = ROOT / "data/raw/cke/MHIP-R0-100-A-2505-arkusz.pdf"
ZASADY = ROOT / "data/raw/cke/MHIP-R0-100-2505-zasady.pdf"
JSONL = ROOT / "data/eval/matura.jsonl"
OUT = ROOT / "data/history_extended/formulka-2023/history-2025-05"
IMG_DIR = OUT / "images"
GOLD_DIR = OUT / "gold"

EXAM_ID = "history-2025-05"
SOURCE_EXAM_ID = "MHIP-R0-100-A-2505"
TITLE = "Historia — matura rozszerzona, maj 2025"
SOURCE_URL = (
    "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/"
    "Arkusze_egzaminacyjne/2025/Historia/MHIP-R0-100-A-2505-arkusz.pdf"
)
ZASADY_URL = (
    "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/"
    "Arkusze_egzaminacyjne/2025/zasady_oceniania/MHIP-R0-100-2505-zasady.pdf"
)
INSTRUCTIONS = (
    "Rozwiąż zadania po polsku. Czytaj question, source_text i wszystkie powiązane "
    "images. Wzory answer_format pokazują tylko składnię, nie poprawne odpowiedzi."
)
DEFAULT_AF = "Tekst po polsku. Podaj wszystkie wymagane elementy odpowiedzi."
ESSAY_AF = (
    "Jeden tekst: numer wybranego tematu i całe wypracowanie. "
    "Minimum 300 wyrazów zgodnie z poleceniem."
)
IMG_PLACEHOLDER = "[ilustracja – niedostępna w wersji tekstowej]"
RENDER_ZOOM = 2.5  # ~180 dpi; mock PNGs are ~1000–1400 px wide
ESSAY_ID = "25"

# Manual crop plan: quality crops (not full pages). clip = (x0,y0,x1,y1) PDF points.
CROP_PLAN: list[dict] = [
    # Z1: three vessels A–C — one combined crop (single placeholder in text-proxy)
    {"name": "Z01.png", "page": 4, "clip": (68, 100, 522, 360), "tasks": ["1.1", "1.2"], "label": "naczynia A–C"},
    # Z3: aqueduct / ancient building photo
    {"name": "Z03.png", "page": 6, "clip": (68, 100, 530, 320), "tasks": ["3.1", "3.2"], "label": "fotografia budowli"},
    # Z5: genealogy board (many small tile images + lines)
    {"name": "Z05-S1.png", "page": 8, "clip": (65, 110, 535, 650), "tasks": ["5.1", "5.2"], "label": "tablica genealogiczna"},
    # Z6: city plan
    {"name": "Z06.png", "page": 10, "clip": (120, 100, 480, 385), "tasks": ["6"], "label": "plan miasta"},
    # Z7: map + legend inset
    {"name": "Z07-S2.png", "page": 11, "clip": (95, 45, 530, 360), "tasks": ["7.1", "7.2"], "label": "mapa"},
    # Z8: church photo
    {"name": "Z08.png", "page": 12, "clip": (175, 95, 420, 395), "tasks": ["8"], "label": "fotografia kościoła"},
    # Z10: medal reverse
    {"name": "Z10.png", "page": 13, "clip": (190, 415, 405, 630), "tasks": ["10"], "label": "medal"},
    # Z12: banknote
    {"name": "Z12-S2.png", "page": 15, "clip": (100, 80, 495, 300), "tasks": ["12"], "label": "banknot"},
    # Z14: uprising map
    {"name": "Z14-S1.png", "page": 16, "clip": (90, 100, 510, 615), "tasks": ["14.1", "14.2"], "label": "mapa"},
    # Z14: coats of arms A–B combined
    {"name": "Z14-S2.png", "page": 17, "clip": (95, 75, 535, 330), "tasks": ["14.1", "14.2"], "label": "herby A–B"},
    # Z16: magazine title pages A–B combined
    {"name": "Z16-S2.png", "page": 19, "clip": (130, 80, 465, 380), "tasks": ["16.1", "16.2"], "label": "czasopisma A–B"},
    # Z17: 1915 illustration
    {"name": "Z17-S1.png", "page": 20, "clip": (68, 100, 535, 420), "tasks": ["17.1", "17.2"], "label": "ilustracja"},
    # Z18: French drawing 1919
    {"name": "Z18.png", "page": 21, "clip": (155, 95, 445, 455), "tasks": ["18"], "label": "rysunek"},
    # Z20: book cover
    {"name": "Z20.png", "page": 22, "clip": (145, 355, 450, 660), "tasks": ["20"], "label": "okładka książki"},
    # Z21: magazine masthead + poster
    {"name": "Z21-S1.png", "page": 23, "clip": (140, 95, 455, 225), "tasks": ["21.1", "21.2"], "label": "czasopismo"},
    {"name": "Z21-S2.png", "page": 23, "clip": (190, 240, 405, 510), "tasks": ["21.1", "21.2"], "label": "plakat"},
    # Z23: painting
    {"name": "Z23.png", "page": 25, "clip": (90, 100, 510, 435), "tasks": ["23"], "label": "obraz"},
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl_rows() -> list[dict]:
    rows = []
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("paper") == "2025-05":
                rows.append(r)
    return rows


def item_id_from_jsonl(qid: str) -> str:
    m = re.match(r"2025-05-z(\d+(?:\.\d+)?)$", qid)
    if not m:
        raise ValueError(qid)
    return m.group(1)


def group_of(iid: str) -> int:
    return int(iid.split(".")[0])


def clean_question(q: str, iid: str) -> str:
    q = q.strip()
    q = re.sub(r"(?:\n[A-D])+\s*$", "", q)
    q = re.sub(r"(?m)^[.…\s]{3,}$", "", q)
    q = re.sub(r"\n{3,}", "\n\n", q).strip()
    return q


def clean_essay_question(q: str) -> str:
    q = re.split(r"\nWYPRACOWANIE\b", q)[0]
    q = re.sub(r"\nHISTORIA\nPoziom rozszerzony.*", "", q, flags=re.S)
    q = q.replace(IMG_PLACEHOLDER, "").strip()
    q = re.sub(r"\n{3,}", "\n\n", q)
    return q.strip()


def clean_context(ctx: str) -> str:
    """Drop false-positive placeholders that sit immediately before a Źródło heading
    when another placeholder follows that heading (common text-proxy artifact)."""
    if not ctx:
        return ctx
    ctx = re.sub(
        rf"{re.escape(IMG_PLACEHOLDER)}\n(?=Źródło\s+\d)",
        "",
        ctx,
    )
    return ctx


def derive_answer_format(row: dict) -> str:
    cat = row.get("category") or ""
    q = row.get("question") or ""
    if cat == "essay" or row.get("points", 0) >= 10:
        return ESSAY_AF
    if cat == "closed_choice":
        if re.search(r"(?m)^1\.\s", q) and re.search(r"(?m)^2\.\s", q):
            return "1: A\n2: A"
        return "A"
    if cat == "true_false":
        nums = re.findall(r"(?m)^(\d+)\.\s", q)
        if nums:
            n = max(int(x) for x in nums)
            lines = []
            for i in range(1, n + 1):
                lines.append(f"{i}: {'P' if i != 2 else 'F'}")
            return "\n".join(lines)
        return "1: P\n2: F\n3: P"
    if cat == "matching":
        if "Fragment A" in q and "Fragment B" in q:
            return "A: …\nB: …"
        if re.search(r"(?m)^A\.", q) and re.search(r"(?m)^B\.", q):
            return "A: 1\nB: 1"
        return "A: …\nB: …"
    return DEFAULT_AF


def crop_images(doc: pymupdf.Document) -> dict[str, dict]:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    notes: list[str] = []
    for spec in CROP_PLAN:
        page = doc[spec["page"] - 1]
        clip = pymupdf.Rect(*spec["clip"]) & page.rect
        mat = pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        png = pix.tobytes("png")
        im = Image.open(BytesIO(png)).convert("RGB")
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
        png = buf.getvalue()
        dest = IMG_DIR / spec["name"]
        dest.write_bytes(png)
        digest = sha256_bytes(png)
        out[spec["name"]] = {
            "path": f"images/{spec['name']}",
            "sha256": digest,
            "source_page": spec["page"],
            "tasks": list(spec["tasks"]),
            "label": spec.get("label", ""),
            "size": im.size,
            "bytes": len(png),
        }
        notes.append(
            f"- {spec['name']}: page {spec['page']} clip={spec['clip']} "
            f"→ {im.size[0]}x{im.size[1]} ({len(png)} B) tasks={spec['tasks']}"
        )
    (OUT / "_crop_notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return out


def build_task_image_index(crops: dict[str, dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for name, meta in crops.items():
        img_obj = {
            "path": meta["path"],
            "source_page": meta["source_page"],
            "sha256": meta["sha256"],
        }
        for tid in meta["tasks"]:
            idx[tid].append(img_obj)
    return idx


def inject_image_markers(source_text: str, images: list[dict]) -> str:
    if not images:
        return source_text.replace(IMG_PLACEHOLDER, "").strip()
    text = source_text
    remaining = list(images)
    while IMG_PLACEHOLDER in text and remaining:
        img = remaining.pop(0)
        text = text.replace(IMG_PLACEHOLDER, f"[Obraz: {img['path']}]", 1)
    text = text.replace(IMG_PLACEHOLDER, "").strip()
    if remaining:
        extras = "\n".join(f"[Obraz: {im['path']}]" for im in remaining)
        text = (text + "\n" + extras).strip()
    return text


def build_exam(rows: list[dict], task_imgs: dict[str, list[dict]]) -> dict:
    items = []
    for row in rows:
        iid = item_id_from_jsonl(row["id"])
        grp = group_of(iid)
        q = row["question"] or ""
        if iid == ESSAY_ID or row.get("category") == "essay":
            q = clean_essay_question(q)
        else:
            q = clean_question(q, iid)
        ctx = clean_context(row.get("context") or "")
        images = list(task_imgs.get(iid, []))
        source_text = inject_image_markers(ctx, images)
        if iid == ESSAY_ID:
            source_text = ""
            images = []
        item = {
            "id": iid,
            "group": grp,
            "max_points": int(row["points"]),
            "question": q.strip(),
            "source_text": source_text,
            "images": images,
            "answer_format": derive_answer_format(row),
        }
        items.append(item)
    max_points = sum(i["max_points"] for i in items)
    return {
        "exam_id": EXAM_ID,
        "title": TITLE,
        "source_exam_id": SOURCE_EXAM_ID,
        "source_url": SOURCE_URL,
        "input_format": "separate-text-and-images-v1",
        "language": "pl",
        "max_points": max_points,
        "instructions": INSTRUCTIONS,
        "items": items,
    }


def build_answers_template(exam: dict) -> dict:
    return {
        "exam_id": EXAM_ID,
        "answers": [{"id": it["id"], "answer": ""} for it in exam["items"]],
    }


def seed_gold(rows: list[dict]) -> dict:
    gold_answers = []
    for row in rows:
        iid = item_id_from_jsonl(row["id"])
        cat = row.get("category")
        answer = None
        raw_gold = row.get("gold")
        if raw_gold is not None and str(raw_gold).strip() in ("", "None", "null"):
            raw_gold = None
        if cat == "closed_choice" and raw_gold:
            answer = str(raw_gold).strip()
        elif cat == "true_false" and raw_gold:
            parts = [p.strip() for p in str(raw_gold).split(",")]
            answer = "\n".join(f"{i+1}: {p}" for i, p in enumerate(parts))
        elif cat == "matching" and row.get("gold_keywords"):
            kws = row["gold_keywords"]
            labels = ["A", "B", "C", "D"]
            lines = []
            for i, kw in enumerate(kws):
                val = kw[0] if isinstance(kw, list) else kw
                lines.append(f"{labels[i]}: {val}")
            answer = "\n".join(lines)
        elif row.get("decision") and cat != "essay":
            g = raw_gold
            if g and len(str(g)) < 200 and "Przykładow" not in str(g):
                answer = str(g).strip()
            else:
                answer = f"Rozstrzygnięcie: {row['decision']}"
        elif row.get("gold_keywords") and cat in ("short_open", "source_analysis"):
            parts = []
            for kw in row["gold_keywords"]:
                if isinstance(kw, list):
                    parts.append(kw[0])
                else:
                    parts.append(str(kw))
            answer = "\n".join(parts) if len(parts) > 1 else parts[0]
        elif raw_gold and cat != "essay" and len(str(raw_gold)) < 120:
            answer = str(raw_gold).strip()
        if answer is not None:
            gold_answers.append({"id": iid, "answer": answer, "category": cat})
    return {"exam_id": EXAM_ID, "source": "zasady via matura.jsonl", "answers": gold_answers}


def write_source_md(crops: dict[str, dict], exam: dict, full_page_fallback: list[str]) -> None:
    ark_sha = sha256_file(ARKUSZ)
    zas_sha = sha256_file(ZASADY)
    lines = [
        f"# SOURCE — {EXAM_ID}",
        "",
        "Official CKE History Extended (Formuła 2023), May 2025 session.",
        "Pack format mirrors `data/official/history-2023-mock-v1/` (`separate-text-and-images-v1`).",
        "",
        "## CKE originals (NOT copied into this pack)",
        "",
        f"- Arkusz: [{SOURCE_EXAM_ID}-arkusz.pdf]({SOURCE_URL})",
        f"  - local: `data/raw/cke/MHIP-R0-100-A-2505-arkusz.pdf`",
        f"  - sha256: `{ark_sha}`",
        f"- Zasady oceniania: [MHIP-R0-100-2505-zasady.pdf]({ZASADY_URL})",
        f"  - local: `data/raw/cke/MHIP-R0-100-2505-zasady.pdf`",
        f"  - sha256: `{zas_sha}`",
        "",
        "## Pack contents",
        "",
        f"- `exam_id`: `{EXAM_ID}`",
        f"- `source_exam_id`: `{SOURCE_EXAM_ID}`",
        f"- items: {len(exam['items'])}",
        f"- max_points: {exam['max_points']}",
        f"- images: {len(crops)} PNGs under `images/`",
        f"- text seed: `data/eval/matura.jsonl` rows with `paper=2025-05` "
        "(question/context/gold); images cropped from arkusz with pymupdf",
        "",
        "## Image crops",
        "",
        "Crops rendered at 2.5× zoom from planned page clips (quality crops, not full pages).",
        "",
    ]
    for name, meta in crops.items():
        lines.append(
            f"- `{name}` — page {meta['source_page']}, "
            f"{meta['size'][0]}×{meta['size'][1]}, sha256 `{meta['sha256']}`, "
            f"tasks {meta['tasks']} ({meta['label']})"
        )
    if full_page_fallback:
        lines += ["", "## Full-page fallbacks", ""]
        lines += [f"- {x}" for x in full_page_fallback]
    else:
        lines += ["", "## Full-page fallbacks", "", "- none (all planned crops succeeded)", ""]
    lines += [
        "## Known gaps / QA",
        "",
        "- Transcription quality follows `matura.jsonl` / pymupdf text extract "
        "(same OCR-ish limitations as the text-proxy eval set).",
        "- Crop boxes are automatic heuristics from page image bboxes + manual clip tuning; "
        "visual QA recommended before using as a hard gauge.",
        f"- Essay is item `{ESSAY_ID}` (15 pkt); `source_text` empty; three topic choices in `question`.",
        "- Optional `gold/answers.json` seeded for closed / short / decision items from zasady "
        "via matura.jsonl — not a substitute for full CKE rubric grading.",
        "- Zadanie 1 vessels: one combined crop of A–C (`Z01.png`).",
        "- Zadanie 5 genealogy: one combined crop of the ruler tiles (`Z05-S1.png`); "
        "names also transcribed in `source_text`.",
        "- Zadanie 14 herby: one combined crop of A–B (`Z14-S2.png`).",
        "- Zadanie 16 magazines: one combined crop of A–B (`Z16-S2.png`).",
        "- Zadanie 7 text-proxy had a false placeholder before `Źródło 2`; stripped in pack build.",
        "",
        "## License note",
        "",
        "CKE exam PDFs are copyrighted; do not commit the PDFs. This pack keeps only "
        "transcribed text + cropped illustration PNGs for local/eval use. Confirm "
        "distribution policy before any public push.",
        "",
    ]
    (OUT / "SOURCE.md").write_text("\n".join(lines), encoding="utf-8")


def validate(exam: dict, template: dict, crops: dict[str, dict]) -> list[str]:
    errs: list[str] = []
    ids = [it["id"] for it in exam["items"]]
    if len(ids) != len(set(ids)):
        errs.append(f"duplicate item ids: {ids}")
    tmpl_ids = [a["id"] for a in template["answers"]]
    if set(tmpl_ids) != set(ids) or len(tmpl_ids) != len(ids):
        errs.append(f"answers-template ids mismatch: exam={ids} tmpl={tmpl_ids}")
    if template["exam_id"] != exam["exam_id"]:
        errs.append("exam_id mismatch between exam and template")
    pts = sum(it["max_points"] for it in exam["items"])
    if pts != exam["max_points"]:
        errs.append(f"max_points field {exam['max_points']} != sum {pts}")
    if pts != 60:
        errs.append(f"max_points sum is {pts}, expected 60")
    required_top = {
        "exam_id", "title", "source_exam_id", "source_url", "input_format",
        "language", "max_points", "instructions", "items",
    }
    missing = required_top - set(exam.keys())
    if missing:
        errs.append(f"exam missing keys: {missing}")
    if exam.get("input_format") != "separate-text-and-images-v1":
        errs.append("bad input_format")
    if exam.get("language") != "pl":
        errs.append("bad language")
    if exam.get("exam_id") != EXAM_ID:
        errs.append("bad exam_id")
    for it in exam["items"]:
        for k in ("id", "group", "max_points", "question", "source_text", "images", "answer_format"):
            if k not in it:
                errs.append(f"item {it.get('id')} missing {k}")
        for im in it["images"]:
            p = OUT / im["path"]
            if not p.exists():
                errs.append(f"missing image file {im['path']}")
            else:
                got = sha256_file(p)
                if got != im["sha256"]:
                    errs.append(f"sha256 mismatch {im['path']}: json={im['sha256']} file={got}")
    referenced = {im["path"] for it in exam["items"] for im in it["images"]}
    for meta in crops.values():
        if meta["path"] not in referenced:
            errs.append(f"orphan image not referenced: {meta['path']}")
    return errs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl_rows()
    assert len(rows) == 38, len(rows)

    doc = pymupdf.open(ARKUSZ)
    crops = crop_images(doc)
    task_imgs = build_task_image_index(crops)
    exam = build_exam(rows, task_imgs)
    template = build_answers_template(exam)
    gold = seed_gold(rows)

    (OUT / "exam.json").write_text(
        json.dumps(exam, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "answers-template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (GOLD_DIR / "answers.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_source_md(crops, exam, full_page_fallback=[])

    errs = validate(exam, template, crops)
    report = {
        "path": str(OUT),
        "n_items": len(exam["items"]),
        "max_points_sum": exam["max_points"],
        "n_images": len(crops),
        "n_items_with_images": sum(1 for it in exam["items"] if it["images"]),
        "item_ids": [it["id"] for it in exam["items"]],
        "validator_errors": errs,
        "validator_ok": not errs,
        "gold_seeded": len(gold["answers"]),
        "image_files": sorted(crops.keys()),
    }
    (OUT / "_validate_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
