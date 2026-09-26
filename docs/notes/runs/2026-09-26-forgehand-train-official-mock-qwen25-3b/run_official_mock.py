#!/usr/bin/env python3
"""Fill official mock answers.json using local Qwen2.5-3B-Instruct (HF)."""
from __future__ import annotations

import argparse
import json
import re
import time
import traceback
from pathlib import Path

SYSTEM = (
    "Jesteś ekspertem od historii Polski i powszechnej, rozwiązującym arkusz matury "
    "z historii CKE. Odpowiadaj WYŁĄCZNIE po polsku. Podaj tylko finalną odpowiedź "
    "zgodną z formatem (bez rozumowania, bez meta-komentarzy). Gdy brakuje danych, "
    "odpowiedz najlepiej jak potrafisz na podstawie dostępnego tekstu i opisów ilustracji."
)

OCR_CACHE_PATH = Path("/workspace/hackathon/runs/official_mock_3b/ocr_cache.json")


def load_ocr_cache() -> dict:
    if OCR_CACHE_PATH.exists():
        try:
            return json.loads(OCR_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def ocr_image(path: Path, cache: dict) -> str:
    rel = f"images/{path.name}"
    if rel in cache:
        c = cache[rel]
        if c.get("error"):
            return f"[Ilustracja {path.name}: blad OCR: {c['error']}]"
        o = (c.get("ocr") or "").strip()
        wh = f"{c.get('w', '?')}x{c.get('h', '?')}px"
        if not o:
            return (
                f"[Ilustracja {path.name}: {wh}, OCR pusty - "
                "tresc wizualna niedostepna dla modelu tekstowego]"
            )
        return f"[Ilustracja {path.name}: {wh}]\nOCR:\n{o}"
    try:
        from PIL import Image
        import pytesseract
    except Exception as e:
        return f"[OCR niedostepne: {e}]"
    try:
        img = Image.open(path)
        w, h = img.size
        text = pytesseract.image_to_string(img, lang="pol+eng")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return f"[Ilustracja {path.name}: {w}x{h}px, OCR pusty]"
        if len(text) > 2500:
            text = text[:2500] + "..."
        return f"[Ilustracja {path.name}: {w}x{h}px]\nOCR:\n{text}"
    except Exception as e:
        return f"[Ilustracja {path.name}: blad OCR: {e}]"


def is_closed(item: dict) -> bool:
    fmt = (item.get("answer_format") or "").strip()
    q = item.get("question") or ""
    if item["id"] == "26":
        return False
    if re.fullmatch(r"[A-D]", fmt):
        return True
    if re.search(r"^\d+[.:]\s*[APFABCD]\b", fmt, re.M):
        return True
    if "Zaznacz P" in q or "Zaznacz właściwą" in q or "Dokończ zdania" in q:
        return True
    if re.match(r"^[A-D]:\s*\d", fmt):
        return True
    return False


def categorize(item: dict) -> str:
    if item["id"] == "26":
        return "essay"
    has_img = bool(item.get("images"))
    closed = is_closed(item)
    if has_img and closed:
        return "image_closed"
    if has_img and not closed:
        return "image_open"
    if closed:
        return "text_closed"
    return "text_open"


def build_user_prompt(item: dict, exam_dir: Path, image_notes: dict, cache: dict) -> str:
    parts = [
        f"Zadanie id={item['id']} (max_points={item.get('max_points')})",
        "",
        "POLECENIE:",
        item.get("question") or "",
    ]
    src = (item.get("source_text") or "").strip()
    if src:
        parts += ["", "MATERIAL ZRODLOWY (tekst):", src]
    imgs = item.get("images") or []
    if imgs:
        parts += ["", "OPISY ILUSTRACJI (OCR/caption - model nie widzi pikseli):"]
        for im in imgs:
            rel = im["path"]
            if rel not in image_notes:
                p = exam_dir / rel
                image_notes[rel] = ocr_image(p, cache) if p.exists() else f"[Brak pliku: {rel}]"
            parts += [image_notes[rel], ""]
    fmt = (item.get("answer_format") or "").strip()
    if fmt:
        parts += ["FORMAT ODPOWIEDZI (skladnia, NIE gotowe rozwiazanie):", fmt]
    parts.append("")
    if item["id"] == "26":
        parts.append(
            "Napisz wypracowanie: najpierw numer tematu (1, 2 lub 3), potem pelny tekst. "
            "MINIMUM 300 wyrazow. Styl maturalny, argumentacja historyczna."
        )
    else:
        parts.append(
            "Podaj wylacznie tresc odpowiedzi (elementy wymagane w poleceniu). "
            "Bez wstepu typu 'Odpowiedz:'."
        )
    return "\n".join(parts)


def max_tokens_for(item: dict) -> int:
    if item["id"] == "26":
        return 1200
    if is_closed(item):
        return 64
    return 384


def clean_answer(text: str) -> str:
    t = text.strip()
    t = re.sub(r"<think>[\s\S]*?</think>", "", t, flags=re.I).strip()
    t = re.sub(r"^(Odpowiedź|Odpowiedz|Answer|Finalna odpowiedź)\s*:\s*", "", t, flags=re.I)
    t = t.strip().strip("`").strip()
    if len(t) > 100_000:
        t = t[:100_000]
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exam-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    exam_dir = Path(args.exam_dir)
    exam = json.loads((exam_dir / "exam.json").read_text(encoding="utf-8"))
    template = json.loads((exam_dir / "answers-template.json").read_text(encoding="utf-8"))
    items = list(exam["items"])
    if args.limit:
        items = items[: args.limit]

    out_path = Path(args.out)
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
    print(f"Loading model {args.model} dtype={args.dtype} ...", flush=True)
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

    cache = load_ocr_cache()
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
        user = build_user_prompt(item, exam_dir, image_notes, cache)
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
        payload = {
            "exam_id": exam["exam_id"],
            "answers": [
                {"id": a["id"], "answer": answers_by_id.get(a["id"], "")}
                for a in template["answers"]
            ],
        }
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

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
    }
    out_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
