#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat server for a GGUF model on CPU (llama-cpp-python).

Used by the small-model track to score tiny models without a GPU. Renders the model's own
chat template (from the GGUF metadata) with jinja2, so `chat_template_kwargs` such as
Qwen3's `enable_thinking: false` work like they do in vLLM. Requests are served one at a
time (llama.cpp uses every core for one sequence anyway).

    pip install llama-cpp-python fastapi uvicorn jinja2
    python scripts/cpu_serve.py models/qwen3-0.6b/Qwen3-0.6B-Q8_0.gguf --port 8000
    python scripts/run_baselines.py --models qwen3-0.6b --base-url http://localhost:8000/v1 ...
"""
import argparse
import threading
import time
import uuid

import jinja2
import uvicorn
from fastapi import FastAPI, Request
from llama_cpp import Llama

p = argparse.ArgumentParser()
p.add_argument("gguf")
p.add_argument("--port", type=int, default=8000)
p.add_argument("--ctx", type=int, default=6144)
p.add_argument("--threads", type=int, default=0)
p.add_argument("--template", help="jinja chat template file (default: the GGUF's own)")
args = p.parse_args()

llm = Llama(model_path=args.gguf, n_ctx=args.ctx, n_threads=args.threads or None,
            verbose=False)
tmpl_src = (open(args.template).read() if args.template
            else llm.metadata.get("tokenizer.chat_template"))
env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True,
                         extensions=["jinja2.ext.loopcontrols"])
env.globals["raise_exception"] = lambda m: (_ for _ in ()).throw(ValueError(m))
env.globals["strftime_now"] = lambda f: time.strftime(f)
template = env.from_string(tmpl_src)
bos = llm.detokenize([llm.token_bos()]).decode("utf-8", "ignore") if llm.token_bos() >= 0 else ""
eos = llm.detokenize([llm.token_eos()]).decode("utf-8", "ignore")
lock = threading.Lock()
app = FastAPI()


def render(messages, kwargs):
    if "gemma" in args.gguf.lower():  # Gemma templates reject a system role
        sys_msgs = [m["content"] for m in messages if m["role"] == "system"]
        messages = [m for m in messages if m["role"] != "system"]
        if sys_msgs and messages:
            messages[0] = {**messages[0], "content": "\n\n".join(sys_msgs + [messages[0]["content"]])}
    text = template.render(messages=messages, add_generation_prompt=True, bos_token=bos,
                           eos_token=eos, **kwargs)
    return text


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "base", "object": "model"}]}


@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    prompt = render(body["messages"], body.get("chat_template_kwargs") or {})
    n = int(body.get("n") or 1)
    choices = []
    with lock:
        for i in range(n):
            out = llm.create_completion(
                prompt, max_tokens=int(body.get("max_tokens") or 512),
                temperature=float(body.get("temperature") or 0.0),
                top_p=float(body.get("top_p") or 1.0), stop=body.get("stop") or None,
                seed=int(body.get("seed", i)) if body.get("temperature") else None)
            choices.append({"index": i, "finish_reason": out["choices"][0]["finish_reason"],
                            "message": {"role": "assistant", "content": out["choices"][0]["text"]}})
    return {"id": "chatcmpl-" + uuid.uuid4().hex, "object": "chat.completion",
            "created": int(time.time()), "model": "base", "choices": choices,
            "usage": out.get("usage", {})}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
