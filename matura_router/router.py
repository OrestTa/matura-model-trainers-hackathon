"""Classify a question, pick its adapter, generate, post-process."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from .backends import Backend, GenerationParams, make_backend
from .categories import Category
from .classifier import Classifier, LLMClassifier, RuleClassifier
from .prompts import build_messages, postprocess, strip_think
from .rag import BM25Retriever, format_knowledge

log = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "routes.yaml"


@dataclass
class Route:
    adapter: Optional[str]
    params: GenerationParams


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

    def to_dict(self) -> dict:
        return asdict(self)


class Router:
    def __init__(self, backend: Backend, routes: dict[Category, Route],
                 classifier: Optional[Classifier] = None,
                 retriever: Optional[BM25Retriever] = None, rag: Optional[dict] = None):
        self.backend = backend
        self.routes = routes
        self.classifier = classifier or Classifier()
        self.retriever = retriever
        self.rag = rag or {}
        self._available = backend.available_adapters()

    @classmethod
    def from_config(cls, path: str | Path = DEFAULT_CONFIG,
                    backend: Optional[Backend] = None) -> "Router":
        cfg = yaml.safe_load(Path(path).read_text())
        backend = backend or make_backend(cfg.get("backend", {}))
        routes = {}
        for name, r in cfg.get("routes", {}).items():
            r = dict(r)
            adapter = r.pop("adapter", None)
            routes[Category(name)] = Route(adapter, GenerationParams(**r))
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
                retriever = BM25Retriever.load(kb)
                log.info("RAG: %d passages from %s", len(retriever.passages), kb)
            else:
                log.warning("RAG knowledge base %s not built yet (scripts/build_kb.py); running without", kb)
        return cls(backend, routes, classifier, retriever, rag)

    def knowledge(self, category: Category, question: str, context: str) -> tuple[str, tuple]:
        """Retrieved passages for this question, or ("", ()) when RAG is off for it."""
        cats = self.rag.get("categories")
        if self.retriever is None or (cats and category.value not in cats):
            return "", ()
        # The command carries the topic; a long source would drown it, so only its start counts.
        hits = self.retriever.search(f"{question}\n{context[:400]}", k=int(self.rag.get("k", 4)))
        text = format_knowledge(hits, int(self.rag.get("max_chars", 3000)))
        return text, tuple(p.title for p in hits)

    def resolve_adapter(self, category: Category) -> Optional[str]:
        route = self.routes.get(category) or self.routes[Category.GENERAL]
        adapter = route.adapter
        if adapter and self._available is not None and adapter not in self._available:
            log.warning("adapter %r not loaded, using base model for %s", adapter, category.value)
            return None
        return adapter

    def answer(self, question: str, context: str = "",
               category: Optional[Category] = None, mode: str = "adapters") -> RoutedAnswer:
        """mode: "adapters" (full harness: adapters + RAG), "rag" (per-type prompts + RAG,
        base model), "routed" (per-type prompts, base model only) or "raw" (one generic
        prompt, base model, no post-processing) for baselines."""
        t0 = time.perf_counter()
        if category is None:
            c = self.classifier.classify(question, context)
            category, confidence, method = c.category, c.confidence, c.method
        else:
            confidence, method = 1.0, "forced"

        route = self.routes.get(category) or self.routes[Category.GENERAL]
        if mode == "raw":
            # The bare-model baseline must not inherit the closed types' tiny token caps.
            route = self.routes[Category.GENERAL]
        adapter = self.resolve_adapter(category) if mode == "adapters" else None
        prompt_cat = Category.GENERAL if mode == "raw" else category
        knowledge, retrieved = self.knowledge(category, question, context) \
            if mode in ("adapters", "rag") else ("", ())
        full_context = f"{knowledge}\n\n{context}".strip() if knowledge else context
        messages = build_messages(prompt_cat, question, full_context, fill_template=mode != "raw")
        try:
            raw = self.backend.chat(messages, adapter, route.params)
        except Exception:
            if adapter is None:
                raise
            # A broken adapter shouldn't cost the question: retry on the base model.
            log.exception("adapter %r failed, retrying on base model", adapter)
            adapter = None
            raw = self.backend.chat(messages, None, route.params)

        answer = strip_think(raw) if mode == "raw" else postprocess(category, raw)
        return RoutedAnswer(answer=answer, raw=raw,
                            category=category.value, adapter=adapter,
                            confidence=round(confidence, 3), method=method,
                            latency_s=round(time.perf_counter() - t0, 3), retrieved=retrieved)
