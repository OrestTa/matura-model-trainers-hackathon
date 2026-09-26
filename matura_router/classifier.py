"""Question-type classifier.

Two stages:
1. RuleClassifier: weighted Polish keyword patterns. Instant, no GPU, and good
   enough for matura papers because CKE phrases each task type very consistently.
2. LLMClassifier (optional): asks the base model for a label when the rules are
   unsure. Costs one short generation.

If neither is confident, the question goes to Category.GENERAL (the base model).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .categories import Category


@dataclass
class Classification:
    category: Category
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)
    method: str = "rules"


# (pattern, weight). Patterns are matched case-insensitively against the
# question text plus any attached source/context.
RULES: dict[Category, list[tuple[str, float]]] = {
    Category.ESSAY: [
        (r"\bwypracowani\w*", 4.0),
        (r"\bnapisz\s+(wypracowanie|rozprawk\w*|prac\w*)", 4.0),
        (r"\bscharakteryzuj\b", 1.5),
        (r"\boceń\b.*\b(znaczenie|skutki|wpływ)\b", 1.0),
        (r"\bporównaj\b.*\b(sytuacj\w*|polityk\w*)\b", 1.0),
        (r"\buzasadnij\s+swoje\s+stanowisko\b", 1.5),
    ],
    Category.TRUE_FALSE: [
        (r"\bprawd\w*\b.*\bfałsz\w*\b", 3.0),
        (r"\bP\s*[—–-]?\s*jeśli\b.*\bF\s*[—–-]?\s*jeśli\b", 3.0),
        (r"\bP\s*/\s*F\b", 2.5),
        (r"\bP\s+(albo|lub)\s+F\b", 2.5),
        (r"\boceń\s+prawdziwość\b", 3.0),
        (r"\bprawdziwe\b.*\bfałszywe\b", 2.0),
    ],
    Category.CHRONOLOGY: [
        (r"\buporządkuj\b", 3.0),
        (r"\bchronologiczn\w*", 2.5),
        (r"\bod\s+najwcześniejsz\w*", 2.5),
        (r"\bkolejności\b", 1.0),
    ],
    Category.MATCHING: [
        (r"\bprzyporządkuj\b", 3.0),
        (r"\bdobierz\b", 2.0),
        (r"\bprzyporządkowani\w*", 2.0),
        (r"\bdo\s+każde\w*\b.*\bprzypisz\b", 2.0),
        (r"\bprzypisz\b", 1.5),
    ],
    Category.CLOSED_CHOICE: [
        (r"\bzaznacz\b", 1.5),
        (r"\bwybierz\b", 1.0),
        (r"\bpodkreśl\b", 1.0),
        (r"(^|\n)\s*A\.\s.+\n\s*B\.\s", 2.5),
        (r"(^|\n)\s*A\)\s.+\n\s*B\)\s", 2.5),
        (r"\bpoprawne\s+dokończenie\b", 2.5),
        (r"\bodpowied\w*\s+spośród\b", 2.0),
    ],
    Category.SOURCE_ANALYSIS: [
        (r"\bźródł\w*", 1.5),
        (r"\bna\s+podstawie\s+(tekstu|mapy|tabeli|ilustracji|fragmentu|źródła|wykresu)", 2.0),
        (r"\bfragment\w*\b", 0.8),
        (r"\bautor\w*\s+(tekstu|źródła)", 1.5),
        (r"\bmap\w*\b", 0.8),
        (r"\bplakat\w*\b|\bkarykatur\w*\b|\bilustracj\w*\b", 1.0),
    ],
    Category.SHORT_OPEN: [
        (r"\bpodaj\b", 1.2),
        (r"\bwyjaśnij\b", 1.2),
        (r"\bwymień\b", 1.2),
        (r"\bnazw(ij|ę|isko)\b", 1.0),
        (r"\bokreśl\b", 1.0),
        (r"\bsformułuj\b", 1.0),
        (r"\buzasadnij\b", 0.8),
        (r"\bw\s+którym\s+roku\b|\bkiedy\b", 0.8),
    ],
}

_COMPILED = {
    cat: [(re.compile(p, re.IGNORECASE | re.DOTALL), w) for p, w in pats]
    for cat, pats in RULES.items()
}


class RuleClassifier:
    """Scores every category by summing matched pattern weights."""

    def __init__(self, min_score: float = 1.0, min_margin: float = 0.5):
        self.min_score = min_score
        self.min_margin = min_margin

    def classify(self, question: str, context: str = "") -> Classification:
        # The instruction usually sits in the question; long quoted sources in the
        # context would otherwise drown it, so context only feeds SOURCE_ANALYSIS.
        scores: dict[str, float] = {}
        for cat, pats in _COMPILED.items():
            text = question + ("\n" + context if cat is Category.SOURCE_ANALYSIS else "")
            scores[cat.value] = sum(w for rx, w in pats if rx.search(text))
        if context.strip():
            scores[Category.SOURCE_ANALYSIS.value] += 1.0
        # Open tasks that look closed (dev-paper misroutes, 2026-09-26): "Rozstrzygnij, który fragment
        # jest chronologicznie późniejszy … uzasadnij" (a verdict + justification, not an ordering) and
        # tables filled with names ("uzupełnij tabelę – wpisz … nazwiska"), whose A./B. rows read as choices.
        if re.match(r"\s*rozstrzygnij\b", question, re.I) or re.search(
                r"\buzupełnij\s+tabelę\b.{0,80}\bwpisz\b.{0,60}\b(nazw|nazwisk|imi)", question, re.I | re.S):
            for c in (Category.CHRONOLOGY, Category.CLOSED_CHOICE, Category.MATCHING):
                scores[c.value] = 0.0

        # A clear closed-format instruction beats "it has a source": P/F or A-D
        # tasks based on a source are still answered in the closed format, so the
        # source score is left out of the ranking for them.
        closed = {Category.TRUE_FALSE.value, Category.CHRONOLOGY.value,
                  Category.MATCHING.value, Category.CLOSED_CHOICE.value}
        best_closed = max(closed, key=lambda c: scores[c])
        ranking = scores
        if scores[best_closed] >= 2.5:
            ranking = {c: s for c, s in scores.items()
                       if c != Category.SOURCE_ANALYSIS.value}

        ranked = sorted(ranking.items(), key=lambda kv: kv[1], reverse=True)
        (top, top_s), (_, second_s) = ranked[0], ranked[1]

        total = sum(s for s in scores.values()) or 1.0
        confidence = top_s / total
        if top_s < self.min_score or (top_s - second_s) < self.min_margin:
            return Classification(Category.GENERAL, confidence, scores, "rules")
        return Classification(Category(top), confidence, scores, "rules")


LLM_PROMPT = """Jesteś klasyfikatorem zadań z matury z historii. Przypisz zadanie do jednej kategorii.
Kategorie:
- closed_choice: wybór odpowiedzi A/B/C/D
- true_false: ocena prawdziwości zdań (P/F)
- matching: przyporządkowanie elementów
- chronology: uporządkowanie wydarzeń chronologicznie
- source_analysis: odpowiedź na podstawie tekstu źródłowego, mapy, tabeli lub ilustracji
- short_open: krótka odpowiedź otwarta (podaj, wyjaśnij, wymień)
- essay: wypracowanie
Odpowiedz tylko nazwą kategorii.

Zadanie:
{question}

Kategoria:"""


class LLMClassifier:
    """Asks a model for a label. `generate` is any fn(prompt) -> str."""

    def __init__(self, generate: Callable[[str], str]):
        self.generate = generate

    def classify(self, question: str, context: str = "") -> Classification:
        text = (context + "\n\n" + question).strip()
        out = self.generate(LLM_PROMPT.format(question=text[:4000])).strip().lower()
        for cat in Category.specialised():
            if cat.value in out:
                return Classification(cat, 0.8, {}, "llm")
        return Classification(Category.GENERAL, 0.0, {}, "llm")


class Classifier:
    """Rules first, optional LLM second, GENERAL if both are unsure."""

    def __init__(self, rules: Optional[RuleClassifier] = None,
                 llm: Optional[LLMClassifier] = None):
        self.rules = rules or RuleClassifier()
        self.llm = llm

    def classify(self, question: str, context: str = "") -> Classification:
        result = self.rules.classify(question, context)
        if result.category is Category.GENERAL and self.llm is not None:
            llm_result = self.llm.classify(question, context)
            llm_result.scores = result.scores
            return llm_result
        return result
