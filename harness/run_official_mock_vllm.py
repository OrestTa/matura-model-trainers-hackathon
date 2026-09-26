#!/usr/bin/env python3
"""Fill history pack answers.json via OpenAI-compatible vLLM HTTP API.

Works for the official gauge and any pack under data/history_extended/.
Uses OCR captions for images (text-only models). Does not load local HF weights.
Default pack remains history-2023-mock-v1. Use --dry-run to smoke-test pack
loading without contacting the vLLM server.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from history_pack import (  # noqa: E402
    add_pack_cli,
    answers_payload,
    build_user_prompt,
    categorize,
    clean_answer,
    inventory_images,
    load_ocr_cache,
    load_pack,
    max_tokens_for,
    resolve_pack_dir,
    write_answers,
)

SYSTEM = (
    "Jesteś ekspertem od historii Polski i powszechnej, rozwiązującym arkusz matury "
    "z historii CKE. Odpowiadaj WYŁĄCZNIE po polsku. Podaj tylko finalną odpowiedź "
    "zgodną z formatem (bez rozumowania, bez meta-komentarzy, bez znaczników <think>). "
    "Gdy brakuje danych, odpowiedz najlepiej jak potrafisz na podstawie dostępnego tekstu "
    "i opisów ilustracji."
)


def chat_completion(
    base_url: str, model: str, messages: list, max_tokens: int, temperature: float = 0.0
) -> str:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"] or ""


def wait_ready(base_url: str, timeout_s: float = 600) -> dict:
    url = base_url.rstrip("/") + "/v1/models"
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(3)
    raise RuntimeError(f"vLLM not ready at {base_url}: {last}")


def dry_run(pack_dir: Path, exam: dict, template: dict, out_path: Path) -> int:
    inv = inventory_images(exam, pack_dir)
    answers_by_id = {a["id"]: a.get("answer", "") for a in template["answers"]}
    payload = answers_payload(exam["exam_id"], template, answers_by_id)
    write_answers(out_path, payload)

    image_notes: dict[str, str] = {}
    cache = load_ocr_cache(pack_dir)
    sample_prompt_chars = 0
    sample_id = None
    for it in exam["items"]:
        if it.get("images"):
            sample_id = it["id"]
            prompt = build_user_prompt(it, pack_dir, image_notes, cache)
            sample_prompt_chars = len(prompt)
            break

    cats = {k: 0 for k in ("text_open", "text_closed", "image_open", "image_closed", "essay")}
    for it in exam["items"]:
        cats[categorize(it)] += 1

    summary = {
        "dry_run": True,
        "exam_id": exam["exam_id"],
        "pack_dir": str(pack_dir),
        "n_items": len(template["answers"]),
        "max_points": exam.get("max_points"),
        "categories": cats,
        "images": inv,
        "sample_image_item": sample_id,
        "sample_prompt_chars": sample_prompt_chars,
        "ocr_cache_entries": len(cache),
        "out": str(out_path),
        "gauge_note": "Only history-2023-mock-v1 submissions count as the official gauge.",
    }
    out_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"dry-run wrote {out_path} ({len(payload['answers'])} empty answers)", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fill history pack answers.json via vLLM HTTP. Default: official mock gauge."
    )
    add_pack_cli(ap)
    ap.add_argument("--base-url", default="http://127.0.0.1:8110")
    ap.add_argument("--model", default="awq7b", help="served-model-name (base, not LoRA id)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--wait-s", type=float, default=600)
    args = ap.parse_args()

    pack_dir = resolve_pack_dir(args.pack_dir, args.exam_dir)
    exam, template = load_pack(pack_dir, args.exam_id)
    out_path = Path(args.out)

    if args.dry_run:
        return dry_run(pack_dir, exam, template, out_path)

    items = list(exam["items"])
    if args.limit:
        items = items[: args.limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.with_suffix(".runlog.jsonl")

    done: dict[str, str] = {}
    if args.resume and out_path.exists():
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        for a in prev.get("answers", []):
            if a.get("answer"):
                done[a["id"]] = a["answer"]
        print(f"resume: {len(done)} non-empty", flush=True)

    print(f"Waiting for {args.base_url} pack={pack_dir} …", flush=True)
    models = wait_ready(args.base_url, timeout_s=args.wait_s)
    print(f"ready models={json.dumps(models)[:300]}", flush=True)

    cache = load_ocr_cache(pack_dir)
    image_notes: dict[str, str] = {}
    answers_by_id: dict[str, str] = {a["id"]: a.get("answer", "") for a in template["answers"]}
    answers_by_id.update(done)
    item_by_id = {it["id"]: it for it in exam["items"]}

    cat_stats = {
        "text_open": {"n": 0, "nonempty": 0, "ids": []},
        "text_closed": {"n": 0, "nonempty": 0, "ids": []},
        "image_open": {"n": 0, "nonempty": 0, "ids": []},
        "image_closed": {"n": 0, "nonempty": 0, "ids": []},
        "essay": {"n": 0, "nonempty": 0, "ids": [], "words": 0},
    }

    t0 = time.perf_counter()
    for i, item in enumerate(items):
        iid = item["id"]
        cat = categorize(item)
        if done.get(iid):
            print(f"[{i+1}/{len(items)}] {iid} SKIP resume cat={cat}", flush=True)
            continue
        user = build_user_prompt(item, pack_dir, image_notes, cache)
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ]
        mnt = max_tokens_for(item, essay=1400, closed=64, open_=400)
        t1 = time.perf_counter()
        err = None
        gen = ""
        try:
            gen = chat_completion(args.base_url, args.model, messages, mnt, temperature=0.0)
            ans = clean_answer(gen)
            if not ans and gen:
                messages2 = [
                    {"role": "system", "content": SYSTEM + " /no_think"},
                    {"role": "user", "content": user + "\n\n/no_think"},
                ]
                gen = chat_completion(args.base_url, args.model, messages2, mnt, temperature=0.0)
                ans = clean_answer(gen)
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            ans = ""
            traceback.print_exc()
        lat = time.perf_counter() - t1
        answers_by_id[iid] = ans
        words = len(re.findall(r"\w+", ans, flags=re.UNICODE))
        rec = {
            "id": iid,
            "category": cat,
            "latency_s": round(lat, 3),
            "max_tokens": mnt,
            "answer_len": len(ans),
            "answer_words": words,
            "n_images": len(item.get("images") or []),
            "error": err,
            "raw_preview": (gen or "")[:400],
        }
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"[{i+1}/{len(items)}] {iid} cat={cat} {lat:.1f}s words={words} "
            f"imgs={rec['n_images']} err={err} | {ans[:100]!r}",
            flush=True,
        )
        write_answers(out_path, answers_payload(exam["exam_id"], template, answers_by_id))

    for a in template["answers"]:
        it = item_by_id[a["id"]]
        cat = categorize(it)
        ans = answers_by_id.get(a["id"], "")
        cat_stats[cat]["n"] += 1
        cat_stats[cat]["ids"].append(a["id"])
        if ans:
            cat_stats[cat]["nonempty"] += 1
        if cat == "essay":
            cat_stats[cat]["words"] = len(re.findall(r"\w+", ans, flags=re.UNICODE))

    wall = time.perf_counter() - t0
    nonempty = sum(1 for a in template["answers"] if answers_by_id.get(a["id"]))
    summary = {
        "exam_id": exam["exam_id"],
        "pack_dir": str(pack_dir),
        "base_url": args.base_url,
        "model": args.model,
        "n_items": len(template["answers"]),
        "nonempty": nonempty,
        "wall_s": round(wall, 1),
        "images_ocr_notes": len(image_notes),
        "vision_pixels_fed": False,
        "ocr_fallback": True,
        "out": str(out_path),
        "categories": {
            k: {
                "n": v["n"],
                "nonempty": v["nonempty"],
                "ids": v["ids"],
                **({"words": v["words"]} if k == "essay" else {}),
            }
            for k, v in cat_stats.items()
        },
        "overall": {"n": len(template["answers"]), "nonempty": nonempty},
        "gauge_note": "Only history-2023-mock-v1 submissions count as the official gauge.",
    }
    out_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
