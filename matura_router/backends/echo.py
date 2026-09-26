from __future__ import annotations

from typing import Optional

from .base import Backend, GenerationParams


class EchoBackend(Backend):
    """No model. Returns which adapter would have answered; for tests and dry runs."""

    def __init__(self):
        self.calls: list[tuple[Optional[str], list[dict]]] = []

    def chat(self, messages, adapter, params: GenerationParams) -> str:
        self.calls.append((adapter, messages))
        content = messages[-1]["content"]
        if isinstance(content, list):  # text + image parts
            content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        return f"[{adapter or 'base'}] {content[:80]}"
