from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class GenerationParams:
    max_tokens: int = 256
    temperature: float = 0.0
    top_p: float = 1.0


class Backend(ABC):
    """One base model; `adapter=None` means the untouched base model."""

    @abstractmethod
    def chat(self, messages: list[dict], adapter: Optional[str],
             params: GenerationParams) -> str: ...

    def available_adapters(self) -> Optional[set[str]]:
        """Adapters the backend can serve, or None if it can't tell."""
        return None
