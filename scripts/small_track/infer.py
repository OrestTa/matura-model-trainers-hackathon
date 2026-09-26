#!/usr/bin/env python3
"""Bounded, resumable candidate-only inference against our own model server.

Never sends grading keys. Metadata/hash fields make results auditable by the configured evaluator.
Uses stdlib only, so the same runner works on every GPU provider.
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.request

FORBIDDEN = {"gold", "gold_keywords", "rubric", "official_solution", "reference", "solution", "answer", "answers"}
SYSTEM = "Odpowiedz po polsku na zadanie maturalne z historii. Podaj odpowiedź zgodnie z poleceniem."
GROUNDED = SYSTEM + " Uzasadnienia opieraj na podanych źródłach. Nie wymyślaj treści niewidocznych ilustracji. W wypracowaniu napisz co najmniej 350 słów i rozwiń wszystkie wymagane aspekty."


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def messages(row, mode="bare", images=False, root=Path("."), system_prompt=None):
    bad = FORBIDDEN.intersection(row)
    if bad:
        raise ValueError(f"Candidate input contains grading fields: {sorted(bad)}")
    question = str(row.get("question", ""))
    if not question.strip():
        raise ValueError("Empty candidate question")
    text = "\n\n".join(str(row[k]) for k in ("context", "question") if row.get(k))
    content = [{"type": "text", "text": text}]
    if images:
        for name in row.get("page_images", []):
            path = Path(name)
            if not path.is_absolute():
                path = root / path
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()}})
    return [{"role": "system", "content": system_prompt if system_prompt is not None else (SYSTEM if mode == "bare" else GROUNDED)},
            {"role": "user", "content": content if images else text}]


def answer(row, args, config_hash):
    start = time.monotonic()
    prompt = messages(row, args.mode, args.images, Path(args.image_root), getattr(args, 'system_prompt', None))
    if getattr(args,"user_suffix",None):
        if isinstance(prompt[-1]["content"],str):prompt[-1]["content"] += "\n\n"+args.user_suffix
        else:prompt[-1]["content"][0]["text"] += "\n\n"+args.user_suffix
    if getattr(args,"offline",False):
        from urllib.parse import urlparse
        if urlparse(args.base_url).hostname not in {"127.0.0.1","localhost","::1"}:raise ValueError("offline inference requires loopback endpoint")
    essay = row.get("category") == "essay" or float(row.get("points", 0)) >= 12
    payload = {"model": args.model, "messages": prompt, "temperature": getattr(args,"temperature",0), "seed":getattr(args,"seed",42),
               "max_tokens": args.essay_tokens if essay else args.max_tokens,
               "chat_template_kwargs": {"enable_thinking": False}}
    if getattr(args,"lora",None) is not None:
        payload["lora"] = args.lora
    out = {"id": row["id"], "paper_id": row.get("paper", row.get("paper_id")),
           "task_id": row.get("task", row["id"]), "model": args.model,
           "config_sha256": config_hash, "input_sha256": sha(row),
           "request_sha256": sha(payload), "answer": "", "error": None}
    try:
        headers = {"Content-Type": "application/json"}
        token = os.getenv("SMALL_TRACK_SERVER_KEY")
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(args.base_url.rstrip("/") + "/chat/completions",
                                     data=json.dumps(payload).encode(), headers=headers)
        opener=urllib.request.urlopen
        if getattr(args,'offline',False):
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs):raise ValueError('offline redirects disabled')
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open
        with opener(req, timeout=args.timeout) as response:
            result = json.load(response)
        choice = result["choices"][0]
        out["answer"] = choice["message"].get("content") or ""
        out["finish_reason"] = choice.get("finish_reason")
        out["usage"] = result.get("usage")
        if not out["answer"].strip():
            out["error"] = "empty_answer"
    except Exception as exc:
        # Avoid copying response bodies / credentials into logs.
        out["error"] = type(exc).__name__
    out["answer_sha256"] = hashlib.sha256(out["answer"].encode()).hexdigest()
    out["latency_s"] = round(time.monotonic() - start, 3)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--base-url", required=True, help="Our own model server's /v1 URL")
    p.add_argument("--model", required=True)
    p.add_argument("--mode", choices=["bare", "grounded"], default="bare")
    p.add_argument("--images", action="store_true")
    p.add_argument("--image-root", default=".")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--max-tokens", type=int, default=768)
    p.add_argument("--essay-tokens", type=int, default=2400)
    p.add_argument("--limit", type=int)
    p.add_argument("--artifact-manifest", help="Measured weight hashes/bytes supplied by cloud worker")
    args = p.parse_args()
    if not 1 <= args.concurrency <= 32:
        p.error("concurrency must be 1..32")
    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    if len({str(row["id"]) for row in rows}) != len(rows):
        p.error("duplicate candidate IDs")
    for row in rows:
        messages(row, args.mode, False)
    if args.limit:
        rows = rows[:args.limit]
    config = {"model": args.model, "mode": args.mode, "images": args.images,
              "max_tokens": args.max_tokens, "essay_tokens": args.essay_tokens,
              "input_file_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if args.artifact_manifest:
        config["artifact"] = json.loads(Path(args.artifact_manifest).read_text())
    config_hash = sha(config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            old = json.loads(line)
            if old["config_sha256"] != config_hash:
                p.error("refusing to mix configurations in output")
            done.add(str(old["id"]))
    output.with_suffix(".manifest.json").write_text(json.dumps(config, indent=2))
    pending = [r for r in rows if str(r["id"]) not in done]
    with output.open("a") as out, ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        jobs = [pool.submit(answer, row, args, config_hash) for row in pending]
        for future in as_completed(jobs):
            result = future.result()
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()
            print(json.dumps({"id": result["id"], "error": result["error"], "latency_s": result["latency_s"]}), flush=True)


if __name__ == "__main__":
    main()
