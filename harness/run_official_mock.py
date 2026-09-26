#!/usr/bin/env python3
"""Fill history pack answers.json using local HF CausalLM (Qwen etc.).

Works for the official gauge and any pack under data/history_extended/.
Default pack remains history-2023-mock-v1. Use --dry-run to smoke-test pack
loading without GPU / model weights.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from pathlib import Path

# Allow `python harness/run_official_mock.py` from repo root or harness/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from history_pack import (  # noqa: E402
    DEFAULT_PACK_DIR,
    add_pack_cli,
    answers_payload,
    build_user_prompt,
    categorize,
    clean_answer,
    inventory_images,
    is_essay,
    load_ocr_cache,
    load_pack,
    max_tokens_for,
    resolve_pack_dir,
    write_answers,
)

SYSTEM = (
    "Jesteś ekspertem od historii Polski i powszechnej, rozwiązującym arkusz matury "
    "z historii CKE. Odpowiadaj WYŁĄCZNIE po polsku. Podaj tylko finalną odpowiedź "
    "zgodną z formatem (bez rozumowania, bez meta-komentarzy). Gdy brakuje danych, "
    "odpowiedz najlepiej jak potrafisz na podstawie dostępnego tekstu i opisów ilustracji."
)


def dry_run(pack_dir: Path, exam: dict, template: dict, out_path: Path) -> int:
    """Write empty answers.json from template; report image loadability."""
    inv = inventory_images(exam, pack_dir)
    answers_by_id = {a["id"]: a.get("answer", "") for a in template["answers"]}
    payload = answers_payload(exam["exam_id"], template, answers_by_id)
    write_answers(out_path, payload)

    # Build one sample prompt (first image item if any) to prove OCR path wiring.
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
        description="Fill history pack answers.json (HF transformers). Default: official mock gauge."
    )
    add_pack_cli(ap)
    ap.add_argument("--model", default=None, help="HF model id/path (required unless --dry-run)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    pack_dir = resolve_pack_dir(args.pack_dir, args.exam_dir)
    exam, template = load_pack(pack_dir, args.exam_id)
    out_path = Path(args.out)

    if args.dry_run:
        return dry_run(pack_dir, exam, template, out_path)

    if not args.model:
        raise SystemExit("--model is required unless --dry-run")

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

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[args.dtype]
    print(f"Loading model {args.model} dtype={args.dtype} pack={pack_dir} …", flush=True)
    t_load = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    print(f"loaded in {time.perf_counter()-t_load:.1f}s device={model.device}", flush=True)

    cache = load_ocr_cache(pack_dir)
    print(f"OCR cache entries: {len(cache)}", flush=True)
    image_notes: dict[str, str] = {}
    answers_by_id = {a["id"]: a.get("answer", "") for a in template["answers"]}
    answers_by_id.update(done)
    item_by_id = {it["id"]: it for it in exam["items"]}

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
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(prompt, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        mnt = max_tokens_for(item)
        t1 = time.perf_counter()
        err = None
        gen = ""
        try:
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=mnt,
                    do_sample=False,
                    pad_token_id=tok.eos_token_id,
                )
            gen = tok.decode(out[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
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
            "max_new_tokens": mnt,
            "answer_len": len(ans),
            "answer_words": words,
            "n_images": len(item.get("images") or []),
            "error": err,
            "raw_preview": gen[:400],
        }
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"[{i+1}/{len(items)}] {iid} cat={cat} {lat:.1f}s words={words} "
            f"imgs={rec['n_images']} err={err} | {ans[:100]!r}",
            flush=True,
        )
        write_answers(out_path, answers_payload(exam["exam_id"], template, answers_by_id))

    cat_stats = {
        k: {"n": 0, "nonempty": 0, "ids": []}
        for k in ("text_open", "text_closed", "image_open", "image_closed", "essay")
    }
    essay_words = 0
    for a in template["answers"]:
        it = item_by_id[a["id"]]
        cat = categorize(it)
        ans = answers_by_id.get(a["id"], "")
        cat_stats[cat]["n"] += 1
        cat_stats[cat]["ids"].append(a["id"])
        if ans:
            cat_stats[cat]["nonempty"] += 1
        if cat == "essay":
            essay_words = len(re.findall(r"\w+", ans, flags=re.UNICODE))

    wall = time.perf_counter() - t0
    nonempty = sum(1 for a in template["answers"] if answers_by_id.get(a["id"]))
    summary = {
        "exam_id": exam["exam_id"],
        "pack_dir": str(pack_dir),
        "model": args.model,
        "dtype": args.dtype,
        "backend": "transformers-hf",
        "n_items": len(template["answers"]),
        "nonempty": nonempty,
        "wall_s": round(wall, 1),
        "images_ocr_cache": len(cache),
        "vision_pixels_fed": False,
        "ocr_fallback": True,
        "out": str(out_path),
        "categories": {
            k: {
                "n": v["n"],
                "nonempty": v["nonempty"],
                "ids": v["ids"],
                **({"words": essay_words} if k == "essay" else {}),
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
