"""Offline OCR of the exam's pictures for text-only models (Tesseract, Polish).

Many CKE pictures are posters, headlines, caricatures with captions or document scans, so
their printed text answers much of the question. A text-only model otherwise sees only a
placeholder. Tesseract is a local tool (no model weights to count), runs on CPU in about a
second per page, and needs `apt-get install tesseract-ocr tesseract-ocr-pol` on the exam box.
"""

from __future__ import annotations

import functools
import re
import shutil
import subprocess

PLACEHOLDER = "[ilustracja – niedostępna w wersji tekstowej]"


def available() -> bool:
    return shutil.which("tesseract") is not None


@functools.lru_cache(maxsize=4096)
def ocr(path: str, lang: str = "pol", max_chars: int = 1500) -> str:
    """The picture's printed text, whitespace-normalised; "" if none or on error."""
    try:
        out = subprocess.run(["tesseract", str(path), "-", "-l", lang],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = [re.sub(r"\s+", " ", l).strip() for l in out.splitlines()]
    # Drop OCR noise from photos and maps: lines with too few letters.
    lines = [l for l in lines if sum(ch.isalpha() for ch in l) >= 3]
    return "\n".join(lines)[:max_chars]


def with_ocr(context: str, images, lang: str = "pol") -> str:
    """Replaces each picture placeholder, in order, with that picture's OCR text; pictures
    without a placeholder in the context are appended."""
    texts = []
    for img in images:
        t = ocr(str(img), lang)
        texts.append(f"[ilustracja – tekst odczytany z obrazu (OCR):\n{t}\n]" if t
                     else "[ilustracja – bez czytelnego tekstu]")
    it = iter(texts)
    out = re.sub(re.escape(PLACEHOLDER), lambda m: next(it, m.group(0)), context)
    rest = list(it)
    return (out + ("\n" + "\n".join(rest) if rest else "")).strip()
