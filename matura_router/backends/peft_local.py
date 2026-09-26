"""In-process backend: transformers + PEFT, all adapters loaded on one base model.

Needs `pip install -e .[peft]`. Loading in 4-bit keeps an ~11B base under 8 GB;
adapters are a few tens of MB each and don't count toward the limit.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from .base import Backend, GenerationParams


class PeftBackend(Backend):
    def __init__(self, base_model: str, adapters: Optional[dict[str, str]] = None,
                 load_in_4bit: bool = True, device_map: str = "auto", **_):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(base_model)
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                                   bnb_4bit_quant_type="nf4") if load_in_4bit else None
        model = AutoModelForCausalLM.from_pretrained(
            base_model, quantization_config=quant, device_map=device_map,
            torch_dtype=torch.bfloat16)

        self.adapters: set[str] = set()
        present = {n: p for n, p in (adapters or {}).items() if Path(p).exists()}
        if present:
            first, *rest = present.items()
            model = PeftModel.from_pretrained(model, first[1], adapter_name=first[0])
            for name, path in rest:
                model.load_adapter(path, adapter_name=name)
            self.adapters = set(present)
        self.model = model.eval()
        self._lock = threading.Lock()

    def available_adapters(self) -> Optional[set[str]]:
        return self.adapters

    def chat(self, messages, adapter, params: GenerationParams) -> str:
        ids = self.tok.apply_chat_template(messages, add_generation_prompt=True,
                                           return_tensors="pt").to(self.model.device)
        gen_kwargs = dict(max_new_tokens=params.max_tokens,
                          do_sample=params.temperature > 0,
                          pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        if params.temperature > 0:
            gen_kwargs.update(temperature=params.temperature, top_p=params.top_p)

        # set_adapter mutates the shared model; the server and evaluate() call us from threads.
        with self._lock, self.torch.inference_mode():
            if adapter and adapter in self.adapters:
                self.model.set_adapter(adapter)
                out = self.model.generate(ids, **gen_kwargs)
            elif self.adapters:
                with self.model.disable_adapter():
                    out = self.model.generate(ids, **gen_kwargs)
            else:
                out = self.model.generate(ids, **gen_kwargs)
        return self.tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
