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

import json
import urllib.request
from typing import Optional

from .base import Backend, GenerationParams


class OpenAICompatBackend(Backend):
    def __init__(self, base_url: str = "http://localhost:8000/v1",
                 base_model: str = "base", adapter_mode: str = "model_name",
                 llamacpp_lora_ids: Optional[dict[str, int]] = None,
                 api_key: str = "none", timeout: float = 300.0):
        if adapter_mode not in ("model_name", "llamacpp"):
            raise ValueError("adapter_mode must be 'model_name' or 'llamacpp'")
        self.base_url = base_url.rstrip("/")
        self.base_model = base_model
        self.adapter_mode = adapter_mode
        self.lora_ids = llamacpp_lora_ids or {}
        self.api_key = api_key
        self.timeout = timeout

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
                "top_p": params.top_p}
        if self.adapter_mode == "model_name":
            if adapter:
                body["model"] = adapter
        else:
            # llama.cpp keeps every loaded adapter at scale 0 unless listed here.
            body["lora"] = [{"id": i, "scale": 1.0 if name == adapter else 0.0}
                            for name, i in self.lora_ids.items()]
        return body

    def chat(self, messages, adapter, params: GenerationParams) -> str:
        out = self._post("/chat/completions", self.request_body(messages, adapter, params))
        return out["choices"][0]["message"]["content"]

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
