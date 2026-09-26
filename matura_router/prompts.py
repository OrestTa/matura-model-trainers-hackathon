"""Per-category system prompts and answer post-processing.

The prompts double as the training-time system prompts (scripts/split_by_category.py
writes them into each adapter's dataset), so train and inference stay aligned.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from .categories import Category

_BASE = ("Jesteś ekspertem z historii Polski i świata, który rozwiązuje zadania "
         "z egzaminu maturalnego z historii. ")

SYSTEM_PROMPTS: dict[Category, str] = {
    Category.CLOSED_CHOICE: _BASE + "Odpowiedz wyłącznie literą (lub literami) poprawnej odpowiedzi, np. \"B\" albo \"A, C\".",
    Category.TRUE_FALSE: _BASE + "Dla każdego zdania w kolejności podaj P (prawda) lub F (fałsz), np. \"1. P\\n2. F\\n3. P\".",
    Category.MATCHING: _BASE + "Podaj przyporządkowanie w formacie \"1 – B\\n2 – D\", bez komentarzy.",
    Category.CHRONOLOGY: _BASE + "Podaj wyłącznie kolejność oznaczeń od najwcześniejszego do najpóźniejszego, np. \"C, A, D, B\".",
    Category.SOURCE_ANALYSIS: _BASE + "Odpowiedz zwięźle na podstawie podanego źródła i własnej wiedzy. Wskaż konkretne fakty, nazwiska i daty.",
    Category.SHORT_OPEN: _BASE + "Odpowiedz krótko i konkretnie, jednym lub dwoma zdaniami. Podawaj dokładne nazwy, nazwiska i daty.",
    Category.ESSAY: _BASE + ("Napisz wypracowanie: postaw tezę, uzasadnij ją co najmniej trzema argumentami "
                             "opartymi na faktach (daty, postacie, wydarzenia), uwzględnij tło epoki i sformułuj wniosek. "
                             "Jeśli podano kilka tematów, wybierz jeden i zacznij od linii „Temat nr X”. "
                             "Wypracowanie musi mieć co najmniej 300 słów, najlepiej 400–600."),
    Category.GENERAL: _BASE + "Odpowiedz poprawnie i zwięźle, w formacie wymaganym w poleceniu.",
}


# A fill-in line from the answer sheet: "Rozstrzygnięcie: …", "Fragment A – …", "• …".
_TEMPLATE_LINE = re.compile(r"^\s*(?:[•\-–]|[^\s:–].{0,80}?\s*[:–])\s*(?:…|\.\.\.)\s*$")
_CLOSED = {Category.CLOSED_CHOICE, Category.TRUE_FALSE, Category.MATCHING, Category.CHRONOLOGY}


def answer_template(question: str) -> list[str]:
    """The answer sheet's fill-in lines, in order (about half the CKE items have them)."""
    return [ln.strip() for ln in question.splitlines() if _TEMPLATE_LINE.match(ln)]


def template_instruction(question: str) -> str:
    lines = answer_template(question)
    if not lines:
        return ""
    text = ("\n\nOdpowiedz, wypełniając dokładnie ten szablon z karty odpowiedzi: zachowaj "
            "etykiety i ich kolejność, a „…” zastąp swoją odpowiedzią. Bez dodatkowych komentarzy.\n"
            + "\n".join(lines))
    if any(ln.lower().startswith("rozstrzygnięcie") for ln in lines):
        text += ("\nRozstrzygnięcie to krótka odpowiedź na pytanie z polecenia, jedną z podanych "
                 "w nim możliwości (np. „Tak”, „Nie”, „A”, „Fragment 2.”). Uzasadnienie to 1–3 zdania "
                 "z konkretnym faktem, odwołujące się do źródła i własnej wiedzy.")
    return text


def image_part(path: str | Path) -> dict:
    """An OpenAI-style image content part (PNG/JPEG file as a data URL), for vision models."""
    p = Path(path)
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {"type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"}}


def build_messages(category: Category, question: str, context: str = "",
                   fill_template: bool = True, images: tuple = ()) -> list[dict]:
    """fill_template=False keeps the raw baseline free of harness help. `images` are file
    paths sent as image parts (only for a vision model; the router decides)."""
    user = f"{context.strip()}\n\n{question.strip()}" if context.strip() else question.strip()
    system = SYSTEM_PROMPTS[category]
    if fill_template and category not in _CLOSED:
        system += template_instruction(question)
    content = [{"type": "text", "text": user}, *(image_part(i) for i in images)] if images else user
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]


def strip_think(text: str) -> str:
    """Drop Qwen3-style <think>...</think> reasoning (also an unclosed one cut off by max_tokens)."""
    text = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.S)
    return text.strip()


_VERDICT = re.compile(r"rozstrzygni[eę]cie\s*[:\-–]\s*(.+)", re.I)
_FILLER = {"fragment", "źródło", "źródła", "zrodlo", "ilustracja", "odpowiedź", "odpowiedz"}


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"\w+", s.lower()) if t not in _FILLER]


def extract_verdict(answer: str) -> str:
    """The text after "Rozstrzygnięcie:", or the first line when the label is missing."""
    m = _VERDICT.search(answer.replace("*", ""))
    if m:
        return m.group(1).strip()
    first = answer.strip().splitlines()
    return first[0].strip() if first else ""


def verdict_matches(answer: str, decision: str) -> bool:
    """Whether the answer's verdict agrees with the key's (CKE gives 0 pts otherwise)."""
    gold, got = _tokens(decision), _tokens(extract_verdict(answer))
    if not gold or not got:
        return False
    if gold[0] in ("tak", "nie") and len(gold) == 1:
        yn = [t for t in got if t in ("tak", "nie")]
        return (yn[0] if yn else ("nie" if "niezgodne" in got else "")) == gold[0]
    # Short keys ("A", "3") need the exact token; words may differ by inflection.
    def hit(g):
        if len(g) <= 5:
            return any(t == g or (len(g) > 2 and t.startswith(g)) or (len(t) >= 4 and g.startswith(t))
                       for t in got)
        return any(t[:len(g) - 2] == g[:len(g) - 2] for t in got)
    return all(hit(g) for g in gold)


def postprocess(category: Category, text: str) -> str:
    """Light normalisation so closed answers come out in a gradable shape.

    Only rewrites short answers: a long one usually means the question was misrouted
    (e.g. a table to fill in), and shrinking it to letters would throw the answer away.
    """
    text = strip_think(text)
    if len(text) > 40 and category in (Category.CLOSED_CHOICE, Category.CHRONOLOGY):
        return text
    if category is Category.CLOSED_CHOICE:
        letters = re.findall(r"\b([A-F])\b", text)
        return ", ".join(dict.fromkeys(letters)) if letters else text
    if category is Category.TRUE_FALSE:
        marks = re.findall(r"\b([PF])\b", text)
        return "\n".join(f"{i}. {m}" for i, m in enumerate(marks, 1)) if marks else text
    if category is Category.CHRONOLOGY:
        items = re.findall(r"\b([A-F]|\d)\b", text)
        return ", ".join(dict.fromkeys(items)) if items else text
    return text
