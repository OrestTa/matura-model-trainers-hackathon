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
        self._lora_probed = adapter_mode == "llamacpp"
        self._all_lora_ids: Optional[list] = None

    def _probe_llamacpp_loras(self) -> None:
        """A llama-server started with --lora-init-without-apply (serve_exam.sh LORA_ROUTED=1) holds
        several GGUF LoRAs at scale 0: switch to per-request `lora` with ids named after each adapter's
        directory (adapters/<name>/adapter.gguf -> <name>). A server that applies its LoRA to every
        request (scale > 0) is left alone, so single-adapter evals keep their adapter."""
        self._lora_probed = True
        try:
            root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
            with urllib.request.urlopen(root + "/lora-adapters", timeout=10) as r:
                loras = json.loads(r.read())
        except Exception:  # noqa: BLE001 - vLLM or an older llama-server: nothing to probe
            return
        if loras and all(float(a.get("scale", 0)) == 0 for a in loras):
            from pathlib import Path
            self.adapter_mode = "llamacpp"
            self.lora_ids = {Path(a["path"]).parent.name: a["id"] for a in loras}
            log.info("llama.cpp routed LoRAs: %s", self.lora_ids)

    def _list_lora_ids(self) -> list:
        try:
            root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
            with urllib.request.urlopen(root + "/lora-adapters", timeout=10) as r:
                return [a["id"] for a in json.loads(r.read())]
        except Exception:  # noqa: BLE001 - vLLM: the base model name already means no adapter
            return []

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def request_body(self, messages, adapter, params: GenerationParams) -> dict:
        if not self._lora_probed:
            self._probe_llamacpp_loras()
        body = {"model": self.base_model, "messages": messages,
                "max_tokens": params.max_tokens, "temperature": params.temperature,
                "top_p": params.top_p, **self.extra_body}
        for k, v in (params.extra or {}).items():  # per-request settings win over the backend's
            body[k] = {**body[k], **v} if isinstance(v, dict) and isinstance(body.get(k), dict) else v
        if adapter == "__base__":   # router.BASE_ONLY: switch every loaded LoRA off for this request
            if self._all_lora_ids is None:
                self._all_lora_ids = self._list_lora_ids()
            if self._all_lora_ids:
                body["lora"] = [{"id": i, "scale": 0.0} for i in self._all_lora_ids]
            return body
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
        body = self.request_body(messages, adapter, params)
        try:
            out = self._post("/chat/completions", body)
        except OSError as e:  # socket timeout / connection error (urllib raises URLError, an OSError)
            if not self._fallback(body):
                raise
            log.warning("request failed (%s); retrying once with thinking off", e)
            return self._no_think(body)
        choice = out["choices"][0]
        content = choice["message"].get("content") or ""
        if not content.strip() and choice["message"].get("reasoning_content"):
            # A thinking model spent the whole max_tokens reasoning (the server keeps that apart).
            log.warning("empty answer: max_tokens=%d went to reasoning (finish_reason=%s); "
                        "turn thinking off (chat_template_kwargs.enable_thinking) or set think_tokens",
                        params.max_tokens, choice.get("finish_reason"))
            if self._fallback(body):
                log.warning("retrying once with thinking off (THINK_FALLBACK=1)")
                return self._no_think(body)
        return content

    @staticmethod
    def _fallback(body: dict) -> bool:
        # THINK_FALLBACK=1: an answer lost to runaway thinking (empty content or a timeout) is asked
        # again once with thinking off, so it scores something instead of 0. Off by default so
        # graded comparisons stay like-for-like; on for the exam (docs/EXAM_DAY_BEST_SCORE.md).
        kw = body.get("chat_template_kwargs") or {}
        return os.environ.get("THINK_FALLBACK") == "1" and kw.get("enable_thinking", True) is not False

    def _no_think(self, body: dict) -> str:
        body = {**body, "chat_template_kwargs": {**(body.get("chat_template_kwargs") or {}),
                                                 "enable_thinking": False}}
        out = self._post("/chat/completions", body)
        return out["choices"][0]["message"].get("content") or ""

    def available_adapters(self) -> Optional[set[str]]:
        if not self._lora_probed:
            self._probe_llamacpp_loras()
        if self.adapter_mode == "llamacpp":
            return set(self.lora_ids)
        try:
            req = urllib.request.Request(self.base_url + "/models",
                                         headers={"Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return {m["id"] for m in json.loads(r.read())["data"]}
        except Exception:
            return None
