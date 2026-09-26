"""Model backends. All share one base model and switch LoRA adapters per request."""

from .base import Backend, GenerationParams
from .echo import EchoBackend


def make_backend(cfg: dict) -> Backend:
    kind = cfg.get("kind", "openai")
    if kind == "echo":
        return EchoBackend()
    if kind == "openai":
        from .openai_compat import OpenAICompatBackend
        return OpenAICompatBackend(**{k: v for k, v in cfg.items() if k != "kind"})
    if kind == "peft":
        from .peft_local import PeftBackend
        return PeftBackend(**{k: v for k, v in cfg.items() if k != "kind"})
    raise ValueError(f"unknown backend kind: {kind}")


__all__ = ["Backend", "GenerationParams", "EchoBackend", "make_backend"]
