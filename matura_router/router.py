"""Classify a question, pick its adapter, generate, post-process."""

from __future__ import annotations

import collections
import logging
import os
import re
import dataclasses
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from .backends import Backend, GenerationParams, make_backend
from .categories import Category
from .classifier import Classifier, LLMClassifier, RuleClassifier
from .prompts import build_messages, keyed_format, postprocess, strip_think
from .rag import BM25Retriever, SQLiteRetriever, format_knowledge, load_retriever
from .subtypes import DEFAULT_SUBTYPES, Profile, load_profiles, subtype_of

log = logging.getLogger(__name__)

BASE_ONLY = "__base__"   # adapter name meaning "no LoRA for this request" (LORA_NO_ESSAY=1)

# Essay length (Orest 22:14 CEST): CKE scores an essay under 300 words 0, and the base writes 305-369.
# ESSAY_TARGET_WORDS=550 asks for that length in the essay prompt; ESSAY_MIN_WORDS=350 re-asks a shorter one.
ESSAY_TARGET_TEXT = "Wypracowanie powinno mieć około {} słów (minimum 300; krótsze otrzymuje 0 punktów)."
ESSAY_RETRY_TEXT = ("Twoje wypracowanie ma tylko {} słów, a musi mieć co najmniej 300 (krótsze otrzymuje 0 punktów). "
                    "Napisz je od nowa, w całości, na ten sam temat, około {} słów: rozbuduj każdy argument "
                    "o konkretne fakty, daty i postacie, nie powtarzaj zdań. Zacznij od tej samej linii z numerem tematu.")
_ESSAY_HEADER = re.compile(r"^\W*(wypracowanie|na temat nr\s*\d+|temat( nr)?\s*\d+\.?|historia|poziom rozszerzony)\W*$", re.I)


def essay_min_words() -> int:
    return int(os.environ.get("ESSAY_MIN_WORDS") or 0)


def essay_target() -> int:
    return int(os.environ.get("ESSAY_TARGET_WORDS") or 0)


def essay_best_of() -> int:
    return int(os.environ.get("ESSAY_BEST_OF") or 1)


def open_best_of() -> int:
    """OPEN_BEST_OF=N: self-consistency on open short answers (N answers, the model picks the most complete)."""
    return int(os.environ.get("OPEN_BEST_OF") or 1)


def picture_describe() -> bool:
    """PICTURE_DESCRIBE=1: before a picture question, ask the model to describe the attached pictures."""
    return os.environ.get("PICTURE_DESCRIBE") == "1"


OPEN_CATS = {Category.SHORT_OPEN, Category.SOURCE_ANALYSIS, Category.GENERAL}

OPEN_PICK_TEXT = (
    "Powyżej jest zadanie i {n} wersje odpowiedzi. Wybierz tę, która jest merytorycznie poprawna i "
    "najpełniej wykonuje polecenie: podaje wszystko, o co pytano (każdy element polecenia), opiera się "
    "na źródle, gdy polecenie tego wymaga, i nie zawiera błędów rzeczowych. Nie oceniaj długości. "
    "Odpowiedz tylko jedną linią: \"Najlepsza: K\".")

PICTURE_DESCRIBE_TEXT = (
    "Zanim odpowiesz na polecenie, opisz dokładnie każdą dołączoną ilustrację: co przedstawia, "
    "wszystkie widoczne napisy, podpisy, daty, nazwy, symbole, postaci i elementy mapy lub wykresu. "
    "Nie odpowiadaj jeszcze na polecenie. Podaj tylko opis.")


# Our own writing checklist for picking the best of several essays (no klucz / CKE criteria text).
ESSAY_PICK_TEXT = (
    "Poniżej są {n} wersje wypracowania na ten sam temat. Oceń każdą od 0 do 10 pod względem: "
    "czy odpowiada dokładnie na polecenie tematu i ma jasne stanowisko; czy argumenty opierają się na "
    "konkretnych, prawdziwych faktach, datach i postaciach z właściwego okresu; czy nie ma błędów "
    "rzeczowych ani powtórzeń; czy ma przemyślaną kompozycję (wstęp, rozwinięcie, zakończenie z wnioskiem). "
    "Każdy błąd rzeczowy obniża ocenę. Odpowiedz tylko liniami w formacie \"Wersja K: X\", po jednej na wersję.")


def essay_words(text: str) -> int:
    """Words in the essay body: header lines ("WYPRACOWANIE", "na temat nr 1", "Temat nr 2", ...) not counted."""
    body = [ln for ln in text.replace("*", "").splitlines() if not _ESSAY_HEADER.match(ln.strip())]
    return len(re.findall(r"\w+", " ".join(body)))

# Closed types: post-processed answers are comparable strings, so they can be voted on.
VOTABLE = {Category.CLOSED_CHOICE, Category.TRUE_FALSE, Category.MATCHING, Category.CHRONOLOGY}

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "routes.yaml"


@dataclass
class Route:
    adapter: Optional[str]
    params: GenerationParams
    votes: int = 1                # >1: majority vote over this many answers (closed types)
    vote_temperature: float = 0.7


def _with_text(content, extra: str):
    """Append a text instruction to a message's content (plain string or VLM parts list)."""
    if isinstance(content, str):
        return f"{content}\n\n{extra}"
    return [*content, {"type": "text", "text": extra}]


@dataclass
class RoutedAnswer:
    answer: str
    raw: str
    category: str
    adapter: Optional[str]
    confidence: float
    method: str
    latency_s: float
    retrieved: tuple = ()
    subtype: Optional[str] = None
    profile: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class Router:
    def __init__(self, backend: Backend, routes: dict[Category, Route],
                 classifier: Optional[Classifier] = None,
                 retriever: Optional[BM25Retriever | SQLiteRetriever] = None, rag: Optional[dict] = None):
        self.backend = backend
        self.routes = routes
        self.classifier = classifier or Classifier()
        self.retriever = retriever
        self.rag = rag or {}
        # A vision model gets the exam's PNGs; a text model gets a placeholder per picture,
        # the same one our eval set uses.
        self.vision = False
        # A text model can instead get the pictures' printed text via offline OCR
        # (matura_router/ocr.py, `backend.ocr: true`); never in raw mode.
        self.ocr = False
        self._available = backend.available_adapters()
        # mode "subtype": per-subtype setups (configs/subtypes.yaml, matura_router/subtypes.py)
        self.profiles: dict[str, Profile] = {}
        self.think_added: dict[Category, int] = {}  # apply_model's reasoning budget per route

    @classmethod
    def from_config(cls, path: str | Path = DEFAULT_CONFIG,
                    backend: Optional[Backend] = None) -> "Router":
        cfg = yaml.safe_load(Path(path).read_text())
        backend = backend or make_backend(cfg.get("backend", {}))
        routes = {}
        for name, r in cfg.get("routes", {}).items():
            r = dict(r)
            adapter = r.pop("adapter", None)
            votes, vote_t = int(r.pop("votes", 1)), float(r.pop("vote_temperature", 0.7))
            routes[Category(name)] = Route(adapter, GenerationParams(**r), votes, vote_t)
        routes.setdefault(Category.GENERAL, Route(None, GenerationParams(max_tokens=512)))

        ccfg = cfg.get("classifier", {})
        llm = None
        if ccfg.get("llm_fallback"):
            llm = LLMClassifier(lambda p: backend.chat(
                [{"role": "user", "content": p}], None,
                GenerationParams(max_tokens=8, temperature=0.0)))
        classifier = Classifier(RuleClassifier(ccfg.get("min_score", 1.0),
                                               ccfg.get("min_margin", 0.5)), llm)
        rag = cfg.get("rag") or {}
        retriever = None
        if rag.get("path"):
            kb = Path(rag["path"])
            kb = kb if kb.is_absolute() else Path(path).resolve().parent.parent / kb
            if kb.exists():
                retriever = load_retriever(kb)
                log.info("RAG: %d passages from %s", len(retriever.passages), kb)
            else:
                log.warning("RAG knowledge base %s not built yet (scripts/build_kb.py); running without", kb)
        router = cls(backend, routes, classifier, retriever, rag)
        sub = cfg.get("subtypes_path")
        sub = Path(sub) if sub else DEFAULT_SUBTYPES
        sub = sub if sub.is_absolute() else Path(path).resolve().parent.parent / sub
        if sub.exists():
            router.profiles = load_profiles(sub)
        router.vision = bool(cfg.get("backend", {}).get("vision", False))
        router.ocr = bool(cfg.get("backend", {}).get("ocr", False)) and not router.vision
        if router.ocr:
            from . import ocr
            if not ocr.available():
                log.warning("backend.ocr is on but tesseract isn't installed; pictures stay placeholders")
                router.ocr = False
        return router

    def knowledge(self, category: Category, question: str, context: str) -> tuple[str, tuple]:
        """Retrieved passages for this question, or ("", ()) when RAG is off for it."""
        cats = self.rag.get("categories")
        if self.retriever is None or (cats and category.value not in cats):
            return "", ()
        # The command carries the topic; a long source would drown it, so only its start counts.
        hits = self.retriever.search(f"{question}\n{context[:400]}", k=int(self.rag.get("k", 4)))
        text = format_knowledge(hits, int(self.rag.get("max_chars", 3000)))
        return text, tuple(p.title for p in hits)

    def apply_model(self, spec: dict) -> "Router":
        """Per-model settings from a configs/models.yaml entry: `vision` (send the exam's
        pictures), `ocr` (a text model gets the pictures' OCR text), `extra_body` (sent with every request) and `think_tokens` (a thinking model's reasoning budget, added to every
        route's max_tokens so short closed answers aren't cut off mid-thought)."""
        if "vision" in spec:
            self.vision = bool(spec["vision"])
            if self.vision:
                self.ocr = False  # a vision model reads the pictures itself (from_config sets ocr only for text models)
        if spec.get("ocr") and not self.vision:
            # A text-only entry that reads the pictures' printed text (matura_router/ocr.py).
            from . import ocr
            self.ocr = ocr.available()
            if not self.ocr:
                log.warning("model wants ocr but tesseract isn't installed; pictures stay placeholders")
        if spec.get("extra_body") and hasattr(self.backend, "extra_body"):
            # e.g. chat_template_kwargs.enable_thinking; run_exam.py builds its backend from
            # routes.yaml, so without this the stage harness would drop the model's switch.
            self.backend.extra_body = {**self.backend.extra_body, **spec["extra_body"]}
        extra = int(spec.get("think_tokens") or 0)
        by_type = spec.get("think_tokens_by_type") or {}   # e.g. {essay: 16384}: the essay thinks longer
        if extra or by_type:
            for cat, r in self.routes.items():
                add = int(by_type.get(getattr(cat, "value", cat), extra))
                r.params.max_tokens += add
                self.think_added[cat] = self.think_added.get(cat, 0) + add
        return self

    def resolve_adapter(self, category: Category) -> Optional[str]:
        route = self.routes.get(category) or self.routes[Category.GENERAL]
        adapter = route.adapter
        if adapter and self._available is not None and adapter not in self._available:
            log.warning("adapter %r not loaded, using base model for %s", adapter, category.value)
            return None
        return adapter

    def _lengthen_essay(self, answer: str, raw: str, messages, adapter, params):
        """ESSAY_MIN_WORDS=N: an essay whose body (header lines not counted) is under N words is asked for
        again, whole and longer, up to twice; the longest version wins. CKE gives 0 points under 300 words,
        and the base's essays land at 305-369 (docs/LORA_ROOT_CAUSE.md)."""
        best, best_raw, n = answer, raw, essay_words(answer)
        for _ in range(2):
            if n >= essay_min_words():
                break
            log.warning("essay body %d words < ESSAY_MIN_WORDS=%d: asking for a longer one", n, essay_min_words())
            retry = messages + [{"role": "assistant", "content": best},
                                {"role": "user", "content": ESSAY_RETRY_TEXT.format(n, essay_target() or 550)}]
            try:
                r = self.backend.chat(retry, adapter, params)
            except Exception:  # noqa: BLE001 - keep what we have
                log.exception("essay retry failed")
                break
            a = strip_think(r)
            if essay_words(a) > n:
                best, best_raw, n = a, r, essay_words(a)
        return best, best_raw

    def _best_essay(self, answer: str, raw: str, messages, adapter, params):
        """ESSAY_BEST_OF=N: write N-1 more essays (sampled, in parallel), keep those with >= 300 body words,
        and let the same model score them against our own writing checklist; the top score wins, ties go
        to the first (greedy) essay. Every call failing leaves the greedy essay."""
        n = essay_best_of()
        sp = dataclasses.replace(params, temperature=0.8, top_p=0.95)

        def one(_):
            try:
                r = self.backend.chat(messages, adapter, sp)
                a = strip_think(r)
                if essay_min_words():
                    a, r = self._lengthen_essay(a, r, messages, adapter, params)
                return a, r
            except Exception:  # noqa: BLE001
                log.exception("essay sample failed")
                return "", ""

        with ThreadPoolExecutor(max_workers=n - 1) as pool:
            cands = [(answer, raw), *pool.map(one, range(n - 1))]
        cands = [c for c in cands if essay_words(c[0]) >= 300] or [(answer, raw)]
        if len(cands) == 1:
            return cands[0]
        body = "\n\n".join(f"=== Wersja {i} ===\n{a}" for i, (a, _) in enumerate(cands, 1))
        topic = messages[-1]["content"]
        topic = topic if isinstance(topic, str) else " ".join(p.get("text", "") for p in topic if isinstance(p, dict))
        judge = [{"role": "user", "content": f"{topic}\n\n{body}\n\n{ESSAY_PICK_TEXT.format(n=len(cands))}"}]
        try:
            jp = dataclasses.replace(params, temperature=0.0)
            verdict = strip_think(self.backend.chat(judge, None, jp))
        except Exception:  # noqa: BLE001
            log.exception("essay pick failed")
            return cands[0]
        scores = {int(k): float(v) for k, v in re.findall(r"Wersja\s*(\d+)\s*:\s*(\d+(?:[.,]\d+)?)", verdict.replace(",", "."))}
        best = max(range(1, len(cands) + 1), key=lambda i: (scores.get(i, -1), -i))
        log.info("essay best-of-%d scores %s -> version %d", len(cands), scores, best)
        return cands[best - 1]

    def _best_open(self, answer: str, raw: str, messages, adapter, params):
        """OPEN_BEST_OF=N: N-1 more sampled answers in parallel; the same model picks the most complete
        correct one. Duplicates collapse; a failed pick keeps the greedy answer."""
        n = open_best_of()
        sp = dataclasses.replace(params, temperature=0.7, top_p=0.95)

        def one(_):
            try:
                r = self.backend.chat(messages, adapter, sp)
                return strip_think(r), r
            except Exception:  # noqa: BLE001
                log.exception("open sample failed")
                return "", ""

        with ThreadPoolExecutor(max_workers=n - 1) as pool:
            cands = [(answer, raw), *pool.map(one, range(n - 1))]
        seen, uniq = set(), []
        for a, r in cands:
            k = " ".join(a.split()).lower()
            if a.strip() and k not in seen:
                seen.add(k); uniq.append((a, r))
        if len(uniq) <= 1:
            return (uniq or [(answer, raw)])[0]
        body = "\n\n".join(f"=== Wersja {i} ===\n{a}" for i, (a, _) in enumerate(uniq, 1))
        judge = [*messages, {"role": "assistant", "content": body},
                 {"role": "user", "content": OPEN_PICK_TEXT.format(n=len(uniq))}]
        try:
            verdict = strip_think(self.backend.chat(judge, None, dataclasses.replace(params, temperature=0.0)))
        except Exception:  # noqa: BLE001
            log.exception("open pick failed")
            return uniq[0]
        m = re.search(r"Najlepsza\s*:?\s*(\d+)", verdict) or re.search(r"(\d+)", verdict)
        k = int(m.group(1)) if m else 1
        log.info("open best-of-%d -> version %d", len(uniq), k)
        return uniq[k - 1] if 1 <= k <= len(uniq) else uniq[0]

    def _describe_pictures(self, messages, adapter, params) -> list:
        """PICTURE_DESCRIBE=1: one extra turn where the model describes the pictures, then the question again."""
        ask = [*messages[:-1], {"role": "user", "content": _with_text(messages[-1]["content"], PICTURE_DESCRIBE_TEXT)}]
        try:
            desc = strip_think(self.backend.chat(ask, adapter, params)).strip()
        except Exception:  # noqa: BLE001
            log.exception("picture description failed")
            return messages
        if not desc:
            return messages
        return [*ask, {"role": "assistant", "content": desc},
                {"role": "user", "content": "Teraz, korzystając z tego opisu i ilustracji, wykonaj polecenie z zadania."}]

    def _vote(self, greedy: str, messages: list[dict], adapter: Optional[str],
              route: Route, category: Category, keys: Optional[list] = None) -> str:
        """Majority over the greedy answer plus sampled ones; ties go to the greedy answer.
        With `keys` ("key: value" answer lines) the vote is per key."""
        params = dataclasses.replace(route.params, temperature=route.vote_temperature, top_p=0.95)

        def sample(_):
            try:
                return postprocess(category, self.backend.chat(messages, adapter, params), keys)
            except Exception:  # noqa: BLE001 - a failed sample just doesn't vote
                log.exception("vote sample failed")
                return ""

        # In parallel so vLLM batches them: sequential samples made closed items ~5x slower on stage.
        with ThreadPoolExecutor(max_workers=route.votes - 1) as pool:
            answers = [greedy, *pool.map(sample, range(route.votes - 1))]
        if keys:
            rows = [dict(re.findall(r"(?m)^(\S+): (\S+)$", a)) for a in answers]
            rows = [r for r in rows if set(r) == set(keys)]
            if not rows:
                return greedy
            first = rows[0]
            out = []
            for k in keys:
                c = collections.Counter(r[k] for r in rows)
                top = max(c.values())
                out.append(f"{k}: {first[k] if c[first[k]] == top else c.most_common(1)[0][0]}")
            return "\n".join(out)
        if category is Category.TRUE_FALSE:
            # Vote per statement: whole-string votes on 3-4 statements rarely reach a majority.
            rows = [re.findall(r"\b([PF])\b", a) for a in answers]
            n = len(rows[0])
            if n and all(len(r) == n for r in rows if r):
                marks = []
                for i in range(n):
                    c = collections.Counter(r[i] for r in rows if r)
                    top = max(c.values())
                    marks.append(rows[0][i] if c[rows[0][i]] == top else c.most_common(1)[0][0])
                return "\n".join(f"{i}. {m}" for i, m in enumerate(marks, 1))
        # "A, C" and "C, A" are the same answer.
        key = (lambda a: ", ".join(sorted(a.split(", ")))) if category is Category.CLOSED_CHOICE else (lambda a: a)
        counts = collections.Counter(key(a) for a in answers if a)
        if not counts:
            return greedy
        top = max(counts.values())
        return greedy if counts.get(key(greedy)) == top else next(a for a in answers if a and counts[key(a)] == top)

    def _lengthen(self, answer: str, messages: list[dict], adapter: Optional[str], route: Route,
                  category: Category, min_words: int, tries: int = 2) -> str:
        """Essay length guard: while the answer is under min_words, ask the same model to continue
        it (same topic, no repetition) and append the continuation. Format-only instruction."""
        for _ in range(tries):
            n = len(answer.split())
            if n >= min_words:
                break
            more = [*messages, {"role": "assistant", "content": answer},
                    {"role": "user", "content": (
                        f"Twoja wypowiedź ma {n} słów, a musi mieć co najmniej {min_words}. Kontynuuj ją "
                        "od miejsca, w którym się kończy: dopisz kolejne akapity argumentacji z konkretnymi "
                        "faktami, datami i postaciami oraz zakończenie z wnioskiem. Nie powtarzaj tego, co "
                        "już napisano, nie zaczynaj od nowa i nie dodawaj komentarzy. Podaj tylko dalszy tekst.")}]
            try:
                cont = postprocess(category, self.backend.chat(more, adapter, route.params), [])
            except Exception:  # noqa: BLE001 - keep the answer we have
                log.exception("essay continuation failed")
                break
            if not cont.strip():
                break
            answer = f"{answer.rstrip()}\n\n{cont.strip()}"
        return answer

    def profile_route(self, route: Route, p: Profile, category: Category) -> Route:
        """The category's route with a subtype profile's overrides applied. The profile sets the
        reasoning budget itself, so the model entry's think_tokens isn't added twice."""
        answer_tokens = route.params.max_tokens - self.think_added.get(category, 0)
        max_tokens = (p.max_tokens or answer_tokens) + (p.think_tokens if p.think else 0)
        extra = {"chat_template_kwargs": {"enable_thinking": bool(p.think)}, **p.extra}
        params = GenerationParams(max_tokens,
                                  route.params.temperature if p.temperature is None else p.temperature,
                                  route.params.top_p, extra)
        return Route(p.adapter, params, route.votes if p.votes is None else p.votes, p.vote_temperature)

    def answer(self, question: str, context: str = "",
               category: Optional[Category] = None, mode: str = "adapters",
               images: tuple = (), profile: Optional[Profile] = None) -> RoutedAnswer:
        """mode: "adapters" (full harness: adapters + RAG), "rag" (per-type prompts + RAG,
        base model), "routed" (per-type prompts, base model only), "raw" (one generic
        prompt, base model, no post-processing) for baselines, or "subtype" (per-type prompts
        plus the setup configs/subtypes.yaml gives the item's subtype; `profile` forces one)."""
        t0 = time.perf_counter()
        if category is None:
            c = self.classifier.classify(question, context)
            category, confidence, method = c.category, c.confidence, c.method
        else:
            confidence, method = 1.0, "forced"

        subtype = subtype_of(category, bool(images))
        if mode == "subtype" and profile is None:
            profile = self.profiles.get(subtype) or Profile(name="default", think_tokens=16384 if subtype == "essay" else 8192)
        if mode != "subtype":
            profile = None
        guard = profile.min_words if profile is not None else 0
        name = profile.name if profile is not None else None
        if profile is not None and profile.raw:
            # passthrough: exactly the request --mode raw sends (the frozen baseline), plus the length guard
            mode, profile = "raw", None

        route = self.routes.get(category) or self.routes[Category.GENERAL]
        if mode == "raw":
            # The bare-model baseline must not inherit the closed types' tiny token caps, nor a
            # tighter cap than the harness gets (a 512-token essay can fall under the 300-word
            # minimum and score 0, which would inflate our progress number).
            g = self.routes[Category.GENERAL]
            cap = max(r.params.max_tokens for r in self.routes.values())
            route = Route(None, GenerationParams(cap, g.params.temperature, g.params.top_p))
        if profile is not None:
            route = self.profile_route(route, profile, category)
        if mode == "adapters":
            adapter = self.resolve_adapter(category)
        elif profile is not None and profile.adapter:
            adapter = profile.adapter
            if self._available is not None and adapter not in self._available:
                log.warning("adapter %r not loaded, using base model for %s", adapter, subtype)
                adapter = None
        else:
            adapter = None
        if category == Category.ESSAY and os.environ.get("LORA_NO_ESSAY") == "1":
            # Essays go to the untouched base even when the server applies a LoRA to every request
            # (docs/LORA_ROOT_CAUSE.md: every LoRA so far broke the essay). Backend: all LoRA scales 0.
            adapter = BASE_ONLY
        prompt_cat = Category.GENERAL if mode == "raw" else category
        use_rag = mode in ("adapters", "rag") or (profile is not None and profile.rag)
        knowledge, retrieved = self.knowledge(category, question, context) if use_rag else ("", ())
        if images and self.ocr and mode != "raw":
            from .ocr import with_ocr
            context = with_ocr(context, images)
        elif images and not self.vision:
            context = (context + "\n" + "\n".join(
                "[ilustracja – niedostępna w wersji tekstowej]" for _ in images)).strip()
        if images and self.vision:
            # Our eval rows keep the text-only placeholder where a picture sits; a vision model
            # that reads "niedostępna" tends to answer that it can't see the picture. Point it at
            # the attached image instead, numbered in the order they are sent.
            # The organisers' exam.json marks each picture in source_text as "[Obraz: images/Z04-S2.png]":
            # point it at the attached image with that file name (numbered in sending order).
            n = iter(range(1, 1000))
            by_name = {Path(str(im)).name: i for i, im in enumerate(images, 1)}

            def label(m):
                i = by_name.get(Path(m.group(1)).name) if m.group(1) else None
                return f"[ilustracja {i or next(n)} – obraz dołączony do wiadomości]"
            context = re.sub(r"\[ilustracja – niedostępna w wersji tekstowej\]|\[Obraz: ([^\]\n]+)\]", label, context)
            if profile is not None and profile.ocr:
                from . import ocr
                if ocr.available():
                    notes = ocr.ocr_notes(images)
                    context = f"{context}\n\n{notes}".strip() if notes else context
        full_context = f"{knowledge}\n\n{context}".strip() if knowledge else context
        messages = build_messages(prompt_cat, question, full_context, fill_template=mode != "raw",
                                  images=tuple(images) if self.vision else ())
        if profile is not None and profile.prompt_suffix:
            messages[0]["content"] += "\n" + profile.prompt_suffix.strip()
        if category == Category.ESSAY and essay_target():
            messages[0]["content"] += "\n" + ESSAY_TARGET_TEXT.format(essay_target())
        if images and self.vision and picture_describe() and category != Category.ESSAY:
            messages = self._describe_pictures(messages, adapter, route.params)
        try:
            raw = self.backend.chat(messages, adapter, route.params)
        except Exception:
            if adapter is None:
                raise
            # A broken adapter shouldn't cost the question: retry on the base model.
            log.exception("adapter %r failed, retrying on base model", adapter)
            adapter = None
            raw = self.backend.chat(messages, None, route.params)

        keys = keyed_format(question) if mode != "raw" else []
        answer = strip_think(raw) if mode == "raw" else postprocess(category, raw, keys)
        if guard:
            answer = self._lengthen(answer, messages, adapter, route, category, guard)
        if category == Category.ESSAY and essay_min_words():
            answer, raw = self._lengthen_essay(answer, raw, messages, adapter, route.params)
        if category == Category.ESSAY and essay_best_of() > 1:
            answer, raw = self._best_essay(answer, raw, messages, adapter, route.params)
        if category in OPEN_CATS and open_best_of() > 1 and answer.strip():
            answer, raw = self._best_open(answer, raw, messages, adapter, route.params)
        if mode != "raw" and route.votes > 1 and (category in VOTABLE or keys):
            answer = self._vote(answer, messages, adapter, route, category, keys)
        return RoutedAnswer(answer=answer, raw=raw,
                            category=category.value, adapter=adapter,
                            confidence=round(confidence, 3), method=method,
                            latency_s=round(time.perf_counter() - t0, 3), retrieved=retrieved,
                            subtype=subtype, profile=name)
