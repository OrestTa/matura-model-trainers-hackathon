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
from .prompts import build_messages, postprocess

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

    def to_dict(self) -> dict:
        return asdict(self)


class Router:
    def __init__(self, backend: Backend, routes: dict[Category, Route],
                 classifier: Optional[Classifier] = None):
        self.backend = backend
        self.routes = routes
        self.classifier = classifier or Classifier()
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
        return cls(backend, routes, classifier)

    def resolve_adapter(self, category: Category) -> Optional[str]:
        route = self.routes.get(category) or self.routes[Category.GENERAL]
        adapter = route.adapter
        if adapter and self._available is not None and adapter not in self._available:
            log.warning("adapter %r not loaded, using base model for %s", adapter, category.value)
            return None
        return adapter

    def answer(self, question: str, context: str = "",
               category: Optional[Category] = None) -> RoutedAnswer:
        t0 = time.perf_counter()
        if category is None:
            c = self.classifier.classify(question, context)
            category, confidence, method = c.category, c.confidence, c.method
        else:
            confidence, method = 1.0, "forced"

        route = self.routes.get(category) or self.routes[Category.GENERAL]
        adapter = self.resolve_adapter(category)
        messages = build_messages(category, question, context)
        try:
            raw = self.backend.chat(messages, adapter, route.params)
        except Exception:
            if adapter is None:
                raise
            # A broken adapter shouldn't cost the question: retry on the base model.
            log.exception("adapter %r failed, retrying on base model", adapter)
            adapter = None
            raw = self.backend.chat(messages, None, route.params)

        return RoutedAnswer(answer=postprocess(category, raw), raw=raw,
                            category=category.value, adapter=adapter,
                            confidence=round(confidence, 3), method=method,
                            latency_s=round(time.perf_counter() - t0, 3))
