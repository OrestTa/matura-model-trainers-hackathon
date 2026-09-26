"""Step 0 of docs/LORA_ROOT_CAUSE.md: two cheap checks on a trained Gemma 4 LoRA.

1. `think`: does the adapter shorten Gemma 4's thinking? Same llama-server, same prompts (raw mode,
   thinking on), LoRA scale 0 (= base) vs scale 1. Prints reasoning length, answer words, finish reason.
       llama-server -m gemma-4-12b-it-qat-q4_0.gguf --lora-init-without-apply --lora A1/adapter.gguf ...
       python scripts/probe_lora.py think --url http://127.0.0.1:8080 --eval data/eval/matura.jsonl

2. `convert`: is the GGUF adapter on q4_0 the same adapter as PEFT on bf16? Greedy, thinking off,
   base and adapter on both runtimes. If llama.cpp+LoRA is far from PEFT+LoRA while the two bases agree,
   the conversion (or scale) is wrong.
       python scripts/probe_lora.py convert --url http://127.0.0.1:8080 --adapter-dir A1/gemma4-12b/all \
           --hf-id google/gemma-4-12B-it-qat-q4_0-unquantized --eval data/eval/matura.jsonl

Writes one JSON line per request to --out (default stdout summary only).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from matura_router.categories import Category  # noqa: E402
from matura_router.prompts import build_messages  # noqa: E402


def pick(eval_path: str, n_short: int, essay: bool) -> list[dict]:
    rows = [json.loads(l) for l in open(eval_path, encoding="utf-8")]
    short = [r for r in rows if not r.get("needs_image") and r["category"] != "essay"][:n_short]
    return short + ([next(r for r in rows if r["category"] == "essay")] if essay else [])


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read())


def ask(url, r, scale, think, max_tokens):
    msgs = build_messages(Category.GENERAL, r["question"], r.get("context", ""), fill_template=False)
    body = {"messages": msgs, "max_tokens": max_tokens, "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": think}, "lora": [{"id": 0, "scale": scale}]}
    out = post(url, body)
    m = out["choices"][0]["message"]
    return {"id": r["id"], "scale": scale, "think": think,
            "reasoning_chars": len(m.get("reasoning_content") or ""),
            "answer_words": len((m.get("content") or "").split()),
            "completion_tokens": out.get("usage", {}).get("completion_tokens"),
            "finish": out["choices"][0].get("finish_reason"), "answer": m.get("content") or ""}


def cmd_think(a):
    rows, log = pick(a.eval, a.n, True), []
    for r in rows:
        for scale in (0.0, 1.0):
            res = ask(a.url, r, scale, True, 6000 if r["category"] == "essay" else 4000)
            log.append(res)
            print(f"{r['id']:<14} {'LoRA' if scale else 'base':<4} reasoning {res['reasoning_chars']:>6} chars  "
                  f"answer {res['answer_words']:>4} words  tokens {res['completion_tokens']}  {res['finish']}", flush=True)
    return log


def cmd_convert(a):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    rows, log = pick(a.eval, a.n, False), []
    gguf = {(r["id"], s): ask(a.url, r, s, False, a.tokens)["answer"] for r in rows for s in (0.0, 1.0)}
    tok = AutoTokenizer.from_pretrained(a.hf_id)
    model = AutoModelForCausalLM.from_pretrained(a.hf_id, dtype=torch.bfloat16, device_map="cuda")
    model = PeftModel.from_pretrained(model, a.adapter_dir)

    def gen(r, use_lora):
        msgs = build_messages(Category.GENERAL, r["question"], r.get("context", ""), fill_template=False)
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False,
                                      return_tensors="pt", return_dict=True).to("cuda")
        ctx = model.disable_adapter() if not use_lora else torch.no_grad()
        with ctx, torch.no_grad():
            out = model.generate(**ids, max_new_tokens=a.tokens, do_sample=False)
        return tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)

    def overlap(x, y):  # share of words in common at the same position
        x, y = x.split(), y.split()
        return sum(p == q for p, q in zip(x, y)) / max(1, min(len(x), len(y)))
    for r in rows:
        hb, hl = gen(r, False), gen(r, True)
        gb, gl = gguf[(r["id"], 0.0)], gguf[(r["id"], 1.0)]
        res = {"id": r["id"], "base_hf_vs_gguf": overlap(hb, gb), "lora_hf_vs_gguf": overlap(hl, gl),
               "lora_effect_hf": 1 - overlap(hb, hl), "lora_effect_gguf": 1 - overlap(gb, gl),
               "hf_base": hb, "hf_lora": hl, "gguf_base": gb, "gguf_lora": gl}
        log.append(res)
        print(f"{r['id']:<14} same-position words: base HF~GGUF {res['base_hf_vs_gguf']:.2f}  "
              f"LoRA HF~GGUF {res['lora_hf_vs_gguf']:.2f} | LoRA changes HF {res['lora_effect_hf']:.2f}, "
              f"GGUF {res['lora_effect_gguf']:.2f}", flush=True)
    return log


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["think", "convert"])
    p.add_argument("--url", default="http://127.0.0.1:8080")
    p.add_argument("--eval", default="data/eval/matura.jsonl")
    p.add_argument("--n", type=int, default=5, help="short text-only items (think adds one essay)")
    p.add_argument("--tokens", type=int, default=96, help="convert: greedy tokens per answer")
    p.add_argument("--adapter-dir")
    p.add_argument("--hf-id", default="google/gemma-4-12B-it-qat-q4_0-unquantized")
    p.add_argument("--out")
    a = p.parse_args()
    log = cmd_think(a) if a.cmd == "think" else cmd_convert(a)
    if a.out:
        Path(a.out).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in log))


if __name__ == "__main__":
    main()
