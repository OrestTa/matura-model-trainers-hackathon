"""Per-category system prompts and answer post-processing.

The prompts double as the training-time system prompts (scripts/split_by_category.py
writes them into each adapter's dataset), so train and inference stay aligned.
"""

from __future__ import annotations

import re

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
                             "opartymi na faktach (daty, postacie, wydarzenia), uwzględnij tło epoki i sformułuj wniosek."),
    Category.GENERAL: _BASE + "Odpowiedz poprawnie i zwięźle, w formacie wymaganym w poleceniu.",
}


def build_messages(category: Category, question: str, context: str = "") -> list[dict]:
    user = f"{context.strip()}\n\n{question.strip()}" if context.strip() else question.strip()
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[category]},
        {"role": "user", "content": user},
    ]


def postprocess(category: Category, text: str) -> str:
    """Light normalisation so closed answers come out in a gradable shape."""
    text = text.strip()
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
