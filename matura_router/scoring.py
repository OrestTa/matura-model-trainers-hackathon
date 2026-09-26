"""Scores answers against the eval set's gold answers.

Eval rows (JSONL), one per exam item:
    {"id": "2023-05-z12.1", "question": "...", "context": "...",   # context optional
     "category": "true_false",       # gold question type
     "gold": "P, F, P",              # closed types: the key
     "gold_keywords": [["Piłsudski"], ["1926", "zamach majowy"]],  # open types, optional
     "points": 2}                    # max points, default 1

Closed types are scored automatically (partial credit per item). Open types score
the share of `gold_keywords` groups found in the answer (any alternative in a group
counts), or go to an LLM judge when one is configured. Rows that can't be scored
are reported as unscored rather than counted as zero.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable, Optional

from .categories import Category

CLOSED = {Category.CLOSED_CHOICE, Category.TRUE_FALSE, Category.MATCHING, Category.CHRONOLOGY}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def _letters(s: str) -> list[str]:
    # Case-sensitive: upper-casing would turn the Polish word "a" into option A.
    return re.findall(r"\b([A-F])\b", s)


def _pf(s: str) -> list[str]:
    # Accept P/F and the spelled-out Polish words.
    s = re.sub(r"\bprawda\b", "P", s, flags=re.I)
    s = re.sub(r"\bfałsz\b", "F", s, flags=re.I)
    return re.findall(r"\b([PF])\b", s.upper())


def _pairs(s: str) -> dict[str, str]:
    return {a: b.upper() for a, b in re.findall(r"(\d+)\s*[.)]?\s*[-–—:→>]*\s*([A-Fa-f])\b", s)}


def _order(s: str) -> list[str]:
    return re.findall(r"\b([A-F]|\d)\b", s.upper())


def _correct_of(category: Category, answer: str, gold: str) -> Optional[tuple[int, int]]:
    """(correct, total) sub-items for true/false and matching, else None."""
    if category is Category.TRUE_FALSE:
        g, a = _pf(gold), _pf(answer)
        return sum(x == y for x, y in zip(g, a)), len(g)
    if category is Category.MATCHING:
        g, a = _pairs(gold), _pairs(answer)
        return sum(a.get(k) == v for k, v in g.items()), len(g)
    return None


def cke_points(correct: int, total: int, points: float) -> float:
    """CKE step rule for multi-part items: full points only when all parts are right, one point
    less per mistake (3 statements/2 pts: 3->2, 2->1; 2 statements/1 pt: 2->1, 1->0)."""
    if not total:
        return 0.0
    return float(min(points, max(0.0, correct - (total - points))))


def score_closed(category: Category, answer: str, gold: str) -> float:
    """Fraction of the item answered correctly, 0..1."""
    if category is Category.CLOSED_CHOICE:
        return float(set(_letters(answer)) == set(_letters(gold)) and bool(_letters(gold)))
    if category is Category.TRUE_FALSE:
        g, a = _pf(gold), _pf(answer)
        return sum(x == y for x, y in zip(g, a)) / len(g) if g else 0.0
    if category is Category.MATCHING:
        g, a = _pairs(gold), _pairs(answer)
        return sum(a.get(k) == v for k, v in g.items()) / len(g) if g else 0.0
    if category is Category.CHRONOLOGY:
        g, a = _order(gold), _order(answer)
        return float(bool(g) and a[:len(g)] == g)
    raise ValueError(category)


def score_keywords(answer: str, groups: list[list[str]]) -> float:
    text = _norm(answer)
    hits = sum(any(_norm(alt) in text for alt in group) for group in groups)
    return hits / len(groups) if groups else 0.0


JUDGE_PROMPT = """Jesteś egzaminatorem CKE i oceniasz odpowiedź ucznia na zadanie z matury z historii.
Oceniaj ściśle według zasad oceniania. Przykładowe rozwiązanie jest tylko przykładem:
uznaj każdą merytorycznie poprawną odpowiedź spełniającą zasady.

Zadanie: {question}

Zasady oceniania: {rubric}

Przykładowe rozwiązanie: {gold}

Odpowiedź ucznia: {answer}

Podaj tylko liczbę przyznanych punktów (liczba całkowita od 0 do {points})."""


def score_row(row: dict, answer: str,
              judge: Optional[Callable[[str], str]] = None) -> Optional[float]:
    """Points earned (0..row['points']), or None if the row can't be scored."""
    points = float(row.get("points", 1))
    cat = Category(row["category"]) if row.get("category") else Category.GENERAL
    gold = row.get("gold") or row.get("reference")

    if cat in CLOSED and gold:
        parts = _correct_of(cat, answer, gold)
        if parts is not None:
            return cke_points(*parts, points)
        return points * score_closed(cat, answer, gold)
    if row.get("gold_keywords"):
        return points * score_keywords(answer, row["gold_keywords"])
    if judge and gold:
        rubric = row.get("rubric") or "brak – oceń według przykładu"
        question = row["question"]
        if row.get("context"):
            question = f"{row['context'][:3000]}\n\n{question}"
        try:
            out = judge(JUDGE_PROMPT.format(question=question, answer=answer, rubric=rubric,
                                            # Essay rows repeat the rubric as gold; don't send it twice.
                                            gold=gold if gold != rubric else "(patrz zasady oceniania)",
                                            points=int(points)))
        except Exception:  # noqa: BLE001 - a judge timeout leaves the row unscored, not the run dead
            return None
        # Expect a bare small integer; anything else (an essay, a year) counts as 0.
        m = re.match(r"\D{0,20}?(\d{1,2})\b", out.strip())
        got = float(m.group(1)) if m else 0.0
        return got if got <= points else 0.0
    return None
