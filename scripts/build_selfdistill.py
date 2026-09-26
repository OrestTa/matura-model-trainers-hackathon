"""Self-distilled LoRA training data from real past papers (docs/LORA_ROOT_CAUSE.md, recipe step 1).

Orest 22:14 CEST: no Grok data; train only on real CKE history papers with their official keys, thinking on,
same format as the exam. The base model answers each past-paper item itself, with thinking on and the
exam's raw prompt (pictures attached, as router.py sends them). Samples whose answer matches the CKE key
are kept with their reasoning. With --rationalize, an item the base never gets right gets one more try
with the key shown as a hint; the kept target is then trained WITHOUT the hint (the key is training data
only, never in an exam prompt). Held-out May 2023-2026 papers are always excluded.

    # base q4_0 GGUF + mmproj on llama-server (no LoRA), --jinja
    python scripts/build_selfdistill.py --url http://127.0.0.1:8080 --source data/eval/matura_all.jsonl \
        --image-root . --dev-papers probny-2026-01 --samples 4 --rationalize -o data/train/sd/selfdistill.jsonl
    python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir data/train/sd \
        --think --vision --lr 5e-5 --epochs 2 --rank 16

Matching: closed types need the key's letters / P-F sequence. Open items need the same verdict
("Rozstrzygnięcie") when the key has one, --min-recall of the key's content words (a prefilter), and then
the base model itself (thinking off) must judge the answer full-marks against the CKE key and rubric.
Not the Claude judge: a cheap filter, so some wrong targets can slip through. Essays are skipped: the key is a
rubric, and the essay goes to the base model with the length guard.
Rows out (TRL VLM format, what train_lora.py --vision --think loads):
  {"messages": [system, user(text + image parts), {"role": "assistant", "content": [text],
   "reasoning_content": thought}], "images": [abs paths], "source": id, "category", "match", "hinted"}
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from matura_router.categories import Category  # noqa: E402
from matura_router.prompts import build_messages, image_part, verdict_matches  # noqa: E402

HELD_OUT = {"2023-05", "2024-05", "2025-05", "2026-05"}
CLOSED = {"closed_choice", "true_false", "matching", "chronology"}
PLACEHOLDER = re.compile(r"\[ilustracja – niedostępna w wersji tekstowej\]")
HINT = ("\n\n(Wskazówka tylko do treningu: zgodnie z kluczem CKE poprawna odpowiedź to: {}. "
        "Rozwiąż zadanie samodzielnie, krok po kroku, tak jakbyś nie znał tej wskazówki, i nie wspominaj o niej.)")


def closed_key(s: str) -> list[str]:
    return re.findall(r"\b([A-H]|P|F|prawda|fałsz)\b", s.replace("*", ""))


def shingles(s: str, n: int = 8) -> set[str]:
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def stems(s: str) -> set[str]:
    return {w[:5] for w in re.findall(r"\w+", s.lower()) if len(w) >= 5}


def match(r: dict, answer: str, min_recall: float) -> float:
    gold = str(r.get("gold") or r.get("reference") or "")
    k = closed_key(gold) if r["category"] in CLOSED and r.get("gold") else []
    if k:
        return 1.0 if closed_key(answer)[-len(k):] == k else 0.0
    # closed items whose key is not a plain letter / P-F list ("reference") are matched like open ones
    if r.get("decision") and not verdict_matches(answer, r["decision"]):
        return 0.0
    g = stems(re.sub(r"(?im)^.*(przykładow|rozstrzygnięcie).*$", "", gold)) or stems(gold)
    rec = len(g & stems(answer)) / len(g) if g else (1.0 if r.get("decision") else 0.0)
    # CKE keys are long sample answers: with a matching verdict, a smaller overlap is enough.
    need = min_recall / 2 if r.get("decision") else min_recall
    return max(rec, 0.01) if rec >= need else 0.0


JUDGE = ("Jesteś egzaminatorem matury z historii. Oceń odpowiedź ucznia według klucza CKE.\n\n"
         "ZADANIE:\n{q}\n\nKLUCZ (przykładowa poprawna odpowiedź):\n{gold}\n\nZASADY OCENIANIA:\n{rubric}\n\n"
         "ODPOWIEDŹ UCZNIA:\n{ans}\n\nCzy odpowiedź ucznia dostaje maksymalną liczbę punktów? "
         "Odpowiedz jednym słowem: TAK albo NIE.")


def judge_ok(url: str, r: dict, ans: str) -> bool:
    """Open items: the base model (thinking off) checks the answer against the CKE key and rubric."""
    msg = JUDGE.format(q=r["question"][:3000], gold=str(r.get("gold") or r.get("reference") or "")[:2000],
                       rubric=str(r.get("rubric") or "")[:1500], ans=ans[:2000])
    body = {"messages": [{"role": "user", "content": msg}], "max_tokens": 4, "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read())["choices"][0]["message"].get("content") or ""
    return out.strip().upper().startswith("TAK")


def exam_messages(r: dict, images: list[str], vision: bool) -> list[dict]:
    """router.py's raw prompt: GENERAL system prompt, placeholders pointed at the attached pictures."""
    n = iter(range(1, 1000))
    ctx = PLACEHOLDER.sub(lambda _: f"[ilustracja {next(n)} – obraz dołączony do wiadomości]", r.get("context", "")) \
        if vision and images else r.get("context", "")
    return build_messages(Category.GENERAL, r["question"], ctx, fill_template=False,
                          images=tuple(images) if vision else ())


def ask(url: str, msgs: list, max_tokens: int, temperature: float) -> tuple[str, str]:
    body = {"messages": msgs, "max_tokens": max_tokens, "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": True}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as resp:
        m = json.loads(resp.read())["choices"][0]["message"]
    return (m.get("reasoning_content") or "").strip(), (m.get("content") or "").strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080")
    p.add_argument("--source", default=str(ROOT / "data/eval/matura_all.jsonl"))
    p.add_argument("--image-root", default=str(ROOT), help="row image paths are relative to this")
    p.add_argument("--held-out", default=str(ROOT / "data/eval/matura.jsonl"),
                   help="held-out eval set: items overlapping it are skipped ('' = no check)")
    p.add_argument("--dev-papers", nargs="*", default=["probny-2026-01"],
                   help="kept out of training for checkpoint selection")
    p.add_argument("--no-vision", action="store_true", help="text-only server: skip picture items")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--samples", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=4000, help="thinking + answer, the exam's raw cap")
    p.add_argument("--min-recall", type=float, default=0.3,
                   help="prefilter for open items (half of it when the verdict already matches)")
    p.add_argument("--no-judge", action="store_true",
                   help="open items: skip the base-model check against the key (word overlap only)")
    p.add_argument("--rationalize", action="store_true", help="one hinted try for items never answered right")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=0, help="first N items only (smoke run)")
    p.add_argument("--only-ids", help="file with item ids, one per line: build just these (a shard)")
    a = p.parse_args()

    # Past papers reuse sources: drop items whose question + sources share >10% of 8-word runs with a held-out item.
    held = [json.loads(l) for l in open(a.held_out, encoding="utf-8")] if a.held_out else []
    H = set().union(*(shingles(r["question"] + " " + r.get("context", "")) for r in held)) if held else set()
    rows = []
    for line in open(a.source, encoding="utf-8"):
        r = json.loads(line)
        if r["paper"] in HELD_OUT or r["paper"] in a.dev_papers or r["category"] == "essay":
            continue
        sh = shingles(r["question"] + " " + r.get("context", ""))
        if H and sh and len(sh & H) / len(sh) > 0.1:
            print(f"skip {r['id']}: overlaps a held-out item", file=sys.stderr)
            continue
        imgs = [str(Path(a.image_root) / i) for i in (r.get("images") or [])]
        if imgs and (a.no_vision or not all(Path(i).exists() for i in imgs)):
            if not a.no_vision:
                print(f"skip {r['id']}: missing image", file=sys.stderr)
            continue
        rows.append((r, imgs))
    if a.only_ids:
        want = {l.strip() for l in open(a.only_ids) if l.strip()}
        rows = [(r, i) for r, i in rows if r["id"] in want]
    rows = rows[: a.limit] if a.limit else rows
    print(f"{len(rows)} items x {a.samples} samples (papers: {sorted({r['paper'] for r, _ in rows})})", flush=True)
    vision = not a.no_vision

    def one(item):
        r, imgs = item
        msgs = exam_messages(r, imgs, vision)
        best, hinted = None, False
        tries = [msgs] * a.samples
        for i, m in enumerate(tries + ([None] if a.rationalize else [])):
            if m is None:
                if best:
                    break
                m = [dict(x) for x in msgs]
                hint = HINT.format(str(r.get("gold") or r.get("reference") or "").strip()[:600])
                c = m[1]["content"]
                m[1]["content"] = c + hint if isinstance(c, str) else [{**c[0], "text": c[0]["text"] + hint}, *c[1:]]
                hinted = True
            try:
                thought, ans = ask(a.url, m, a.max_tokens, a.temperature)
            except Exception as e:  # noqa: BLE001 - a failed sample is just not kept
                print(f"{r['id']}: request failed: {e}", file=sys.stderr)
                continue
            if not thought or not ans or (hinted and re.search(r"wskazówk|klucz", thought + ans, re.I)):
                continue
            s = match(r, ans, a.min_recall)
            if s and not (r["category"] in CLOSED and r.get("gold")) and not a.no_judge:
                try:
                    s = 1.0 if judge_ok(a.url, r, ans) else 0.0
                except Exception as e:  # noqa: BLE001
                    print(f"{r['id']}: judge failed: {e}", file=sys.stderr)
                    s = 0.0
            if s and (best is None or s > best[0]):
                best = (s, thought, ans, hinted)
            if s == 1.0:
                break
        if best is None:
            return None
        # Training copy of the prompt: TRL VLM format, {"type": "image"} per picture (paths in "images").
        text = exam_messages(r, imgs, False) if not (vision and imgs) else None
        if text is None:
            sys_t, user = msgs[0]["content"], msgs[1]["content"]
            user_t = user[0]["text"]
        else:
            sys_t, user_t = text[0]["content"], text[1]["content"]
        out_msgs = [{"role": "system", "content": [{"type": "text", "text": sys_t}]},
                    {"role": "user", "content": [{"type": "text", "text": user_t}, *({"type": "image"} for _ in imgs)]},
                    {"role": "assistant", "content": [{"type": "text", "text": best[2]}], "reasoning_content": best[1]}]
        return {"messages": out_msgs, "images": imgs, "source": r["id"], "category": r["category"],
                "match": round(best[0], 2), "hinted": best[3]}

    kept = hinted = 0
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as out, cf.ThreadPoolExecutor(a.workers) as ex:
        for i, res in enumerate(ex.map(one, rows), 1):
            if res:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                kept += 1
                hinted += res["hinted"]
            if i % 25 == 0:
                print(f"{i}/{len(rows)} done, {kept} kept ({hinted} hinted)", flush=True)
    print(f"kept {kept} of {len(rows)} ({hinted} from a hinted try) -> {a.out}")


if __name__ == "__main__":
    main()
