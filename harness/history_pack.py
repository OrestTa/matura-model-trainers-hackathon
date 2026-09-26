#!/usr/bin/env python3
"""Shared helpers for Tarasiuk Lab history mock-format packs.

Works for the official gauge (`history-2023-mock-v1`) and any pack under
`data/history_extended/` that passes `scripts/validate_history_pack.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACK_DIR = ROOT / "data/official/history-2023-mock-v1"
DEFAULT_EXAM_ID = "history-2023-mock-v1"

# OCR cache used by the official mock text-only path (optional).
DEFAULT_OCR_CACHE = ROOT / "runs/official_mock_3b/ocr_cache.json"


def resolve_pack_dir(pack_dir: str | Path | None, exam_dir: str | Path | None = None) -> Path:
    """Resolve pack directory. `--pack-dir` wins; `--exam-dir` is a back-compat alias."""
    if pack_dir and exam_dir:
        raise SystemExit("pass only one of --pack-dir / --exam-dir")
    raw = pack_dir or exam_dir or DEFAULT_PACK_DIR
    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        raise SystemExit(f"pack dir not found: {p}")
    if not (p / "exam.json").exists():
        raise SystemExit(f"missing exam.json in {p}")
    if not (p / "answers-template.json").exists():
        raise SystemExit(f"missing answers-template.json in {p}")
    return p


def load_pack(pack_dir: Path, exam_id: str | None = None) -> tuple[dict, dict]:
    """Load exam.json + answers-template.json; optionally verify exam_id."""
    exam = json.loads((pack_dir / "exam.json").read_text(encoding="utf-8"))
    template = json.loads((pack_dir / "answers-template.json").read_text(encoding="utf-8"))
    eid = exam.get("exam_id")
    if not eid:
        raise SystemExit(f"exam.json missing exam_id in {pack_dir}")
    if exam_id and exam_id != eid:
        raise SystemExit(
            f"--exam-id={exam_id!r} does not match pack exam_id={eid!r} ({pack_dir})"
        )
    if template.get("exam_id") != eid:
        raise SystemExit(
            f"answers-template exam_id={template.get('exam_id')!r} != exam exam_id={eid!r}"
        )
    return exam, template


def is_essay(item: dict) -> bool:
    """Essay / wypracowanie — id varies by year (26 for most; 25 in 2025)."""
    if int(item.get("max_points") or 0) >= 15:
        return True
    q = item.get("question") or ""
    if "trzy tematy" in q.lower() or "minimum 300" in q.lower():
        return True
    # Official mock hard-codes id 26; keep as last resort for that pack only.
    if item.get("id") == "26" and "wypracow" in q.lower():
        return True
    return False


def is_closed(item: dict) -> bool:
    fmt = (item.get("answer_format") or "").strip()
    q = item.get("question") or ""
    if is_essay(item):
        return False
    if re.fullmatch(r"[A-D]", fmt):
        return True
    if re.search(r"^\d+[.:]\s*[APFABCD]\b", fmt, re.M):
        return True
    if "Zaznacz P" in q or "Zaznacz właściwą" in q or "Dokończ zdania" in q:
        return True
    if re.match(r"^[A-D]:\s*\d", fmt):
        return True
    return False


def categorize(item: dict) -> str:
    if is_essay(item):
        return "essay"
    has_img = bool(item.get("images"))
    closed = is_closed(item)
    if has_img and closed:
        return "image_closed"
    if has_img and not closed:
        return "image_open"
    if closed:
        return "text_closed"
    return "text_open"


def max_tokens_for(item: dict, *, essay: int = 1200, closed: int = 64, open_: int = 384) -> int:
    if is_essay(item):
        return essay
    if is_closed(item):
        return closed
    return open_


def load_ocr_cache(pack_dir: Path, extra: Path | None = None) -> dict:
    for cand in [
        extra,
        DEFAULT_OCR_CACHE,
        pack_dir / "ocr_cache.json",
        pack_dir / "runs" / "ocr_cache.json",
    ]:
        if cand is None:
            continue
        if cand.exists():
            try:
                return json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


def read_image_bytes(path: Path) -> bytes | None:
    """Load PNG (or other image) bytes when the file exists; None if missing."""
    try:
        if path.is_file():
            return path.read_bytes()
    except OSError:
        return None
    return None


def ocr_image(path: Path, cache: dict | None = None) -> str:
    """OCR caption for a text-only model. Falls back if file/OCR missing."""
    cache = cache or {}
    rel = f"images/{path.name}"
    if rel in cache:
        c = cache[rel]
        if c.get("error"):
            return f"[Ilustracja {path.name}: blad OCR: {c['error']}]"
        o = (c.get("ocr") or "").strip()
        wh = f"{c.get('w', '?')}x{c.get('h', '?')}px"
        if not o:
            return (
                f"[Ilustracja {path.name}: {wh}, OCR pusty — "
                "tresc wizualna niedostepna dla modelu tekstowego]"
            )
        return f"[Ilustracja {path.name}: {wh}]\nOCR:\n{o}"

    raw = read_image_bytes(path)
    if raw is None:
        return f"[Brak pliku: {rel}]"

    try:
        from PIL import Image
        import io
        import pytesseract
    except Exception as e:
        # Bytes were loaded; report size so vision-capable callers know the file is there.
        return f"[Ilustracja {path.name}: {len(raw)} B, OCR niedostepne: {e}]"

    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
        text = pytesseract.image_to_string(img, lang="pol+eng")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return f"[Ilustracja {path.name}: {w}x{h}px, OCR pusty]"
        if len(text) > 2500:
            text = text[:2500] + "…"
        return f"[Ilustracja {path.name}: {w}x{h}px]\nOCR:\n{text}"
    except Exception as e:
        return f"[Ilustracja {path.name}: blad OCR: {e}]"


def build_user_prompt(
    item: dict,
    pack_dir: Path,
    image_notes: dict[str, str],
    cache: dict | None = None,
) -> str:
    parts = [
        f"Zadanie id={item['id']} (max_points={item.get('max_points')})",
        "",
        "POLECENIE:",
        item.get("question") or "",
    ]
    src = (item.get("source_text") or "").strip()
    if src:
        parts += ["", "MATERIAŁ ŹRÓDŁOWY (tekst):", src]
    imgs = item.get("images") or []
    if imgs:
        parts += ["", "OPISY ILUSTRACJI (OCR/caption — model nie widzi pikseli):"]
        for im in imgs:
            rel = im["path"]
            if rel not in image_notes:
                p = pack_dir / rel
                image_notes[rel] = ocr_image(p, cache)
            parts += [image_notes[rel], ""]
    fmt = (item.get("answer_format") or "").strip()
    if fmt:
        parts += ["FORMAT ODPOWIEDZI (skladnia, NIE gotowe rozwiazanie):", fmt]
    parts.append("")
    if is_essay(item):
        parts.append(
            "Napisz wypracowanie: najpierw numer tematu (1, 2 lub 3), potem pelny tekst. "
            "MINIMUM 300 wyrazow. Styl maturalny, argumentacja historyczna."
        )
    else:
        parts.append(
            "Podaj wylacznie tresc odpowiedzi (elementy wymagane w poleceniu). "
            "Bez wstepu typu 'Odpowiedz:'."
        )
    return "\n".join(parts)


def clean_answer(text: str) -> str:
    t = text.strip()
    t = re.sub(r"<think>[\s\S]*?</think>", "", t, flags=re.I).strip()
    t = re.sub(
        r"^(Odpowiedź|Odpowiedz|Answer|Finalna odpowiedź)\s*:\s*",
        "",
        t,
        flags=re.I,
    )
    t = t.strip().strip("`").strip()
    if len(t) > 100_000:
        t = t[:100_000]
    return t


def answers_payload(exam_id: str, template: dict, answers_by_id: dict[str, str]) -> dict:
    """Polish answers.json contract: only {exam_id, answers:[{id,answer}]}."""
    return {
        "exam_id": exam_id,
        "answers": [
            {"id": a["id"], "answer": answers_by_id.get(a["id"], "")}
            for a in template["answers"]
        ],
    }


def write_answers(out_path: Path, payload: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def inventory_images(exam: dict, pack_dir: Path) -> dict:
    """Count image refs vs existing PNG bytes (for dry-run / smoke reports)."""
    refs = 0
    present = 0
    missing: list[str] = []
    bytes_total = 0
    for it in exam.get("items", []):
        for im in it.get("images") or []:
            refs += 1
            rel = im["path"]
            raw = read_image_bytes(pack_dir / rel)
            if raw is None:
                missing.append(rel)
            else:
                present += 1
                bytes_total += len(raw)
    return {
        "image_refs": refs,
        "images_present": present,
        "images_missing": missing,
        "image_bytes_total": bytes_total,
    }


def add_pack_cli(ap) -> None:
    """Attach shared --pack-dir / --exam-dir / --exam-id / --dry-run flags."""
    ap.add_argument(
        "--pack-dir",
        default=None,
        help=f"History pack directory (default: {DEFAULT_PACK_DIR})",
    )
    ap.add_argument(
        "--exam-dir",
        default=None,
        help="Deprecated alias for --pack-dir (back-compat)",
    )
    ap.add_argument(
        "--exam-id",
        default=None,
        help=f"Optional; must match pack exam_id (default pack is {DEFAULT_EXAM_ID})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Load pack + write empty template answers.json; no model / no GPU",
    )
