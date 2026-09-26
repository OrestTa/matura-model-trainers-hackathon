"""Talks to a local OpenAI-compatible server that holds the base model plus adapters.

Two servers are supported, picked with `adapter_mode`:

* "model_name" (vLLM): start with
      vllm serve <base> --enable-lora --max-loras 8 \
          --lora-modules closed_choice=adapters/closed_choice essay=adapters/essay ...
  Each adapter is then addressable as its own model name.

* "llamacpp" (llama.cpp server): start with
      llama-server -m base.gguf --lora-init-without-apply \
          --lora adapters/closed_choice.gguf --lora adapters/essay.gguf ...
  Adapters are applied per request with the `lora` field; ids follow the order of
  --lora flags and are mapped in `llamacpp_lora_ids`.

Only the stdlib is used so the harness runs on a bare exam machine.
"""

from __future__ import annotations
import os

import json
import logging
import urllib.request
from typing import Optional

from .base import Backend, GenerationParams

log = logging.getLogger(__name__)


class OpenAICompatBackend(Backend):
    def __init__(self, base_url: str = "http://localhost:8000/v1",
                 base_model: str = "base", adapter_mode: str = "model_name",
                 llamacpp_lora_ids: Optional[dict[str, int]] = None,
                 api_key: str = "none", timeout: float = 1800.0,
                 extra_body: Optional[dict] = None):
        if adapter_mode not in ("model_name", "llamacpp"):
            raise ValueError("adapter_mode must be 'model_name' or 'llamacpp'")
        self.base_url = base_url.rstrip("/")
        self.base_model = base_model
        self.adapter_mode = adapter_mode
        self.lora_ids = llamacpp_lora_ids or {}
        self.api_key = api_key
        # Thinking runs (gemma4-12b-think8k: up to 16k tokens at ~25 tok/s per slot) need far more than
        # the old 300 s: at 300 s, 4 of 37 May 2023 answers came back blank ("timed out").
        self.timeout = float(os.environ.get("BACKEND_TIMEOUT", timeout))
        # Merged into every request, e.g. {"chat_template_kwargs": {"enable_thinking": false}}
        # to switch off Qwen3's thinking mode.
        self.extra_body = extra_body or {}

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def request_body(self, messages, adapter, params: GenerationParams) -> dict:
        body = {"model": self.base_model, "messages": messages,
                "max_tokens": params.max_tokens, "temperature": params.temperature,
                "top_p": params.top_p, **self.extra_body}
        for k, v in (params.extra or {}).items():  # per-request settings win over the backend's
            body[k] = {**body[k], **v} if isinstance(v, dict) and isinstance(body.get(k), dict) else v
        if self.adapter_mode == "model_name":
            if adapter:
                body["model"] = adapter
        else:
            # llama.cpp keeps every loaded adapter at scale 0 unless listed here.
            # Several route names may share one file (a single adapter for every type): one entry per id.
            on = self.lora_ids.get(adapter) if adapter else None
            body["lora"] = [{"id": i, "scale": 1.0 if i == on else 0.0}
                            for i in sorted(set(self.lora_ids.values()))]
        return body

    def chat(self, messages, adapter, params: GenerationParams) -> str:
        out = self._post("/chat/completions", self.request_body(messages, adapter, params))
        choice = out["choices"][0]
        content = choice["message"].get("content") or ""
        if not content.strip() and choice["message"].get("reasoning_content"):
            # A thinking model spent the whole max_tokens reasoning (the server keeps that apart).
            log.warning("empty answer: max_tokens=%d went to reasoning (finish_reason=%s); "
                        "turn thinking off (chat_template_kwargs.enable_thinking) or set think_tokens",
                        params.max_tokens, choice.get("finish_reason"))
        return content

    def available_adapters(self) -> Optional[set[str]]:
        if self.adapter_mode == "llamacpp":
            return set(self.lora_ids)
        try:
            req = urllib.request.Request(self.base_url + "/models",
                                         headers={"Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return {m["id"] for m in json.loads(r.read())["data"]}
        except Exception:
            return None
