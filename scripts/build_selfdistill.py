"""Self-distilled LoRA training data (docs/LORA_ROOT_CAUSE.md, recipe step 1).

The base model answers each training question itself, with thinking on and the exam's raw prompt. Only
samples that match the reference answer are kept, with their reasoning, so training reinforces the
base's own correct answers in the exact exam format instead of teaching a new style or length.

    # llama-server with the base q4_0 GGUF (no LoRA), --jinja, e.g. -np 8 -c 65536
    python scripts/build_selfdistill.py --url http://127.0.0.1:8080 \
        --input /mnt/project-files/data/train/past_papers.jsonl train_data/claude_synth.jsonl \
                train_data/open_claude_synth.jsonl \
        --samples 4 -o data/train/selfdistill.jsonl
    # then: python scripts/train_lora.py --model gemma4-12b-think --category selfdistill \
    #          --data-dir data/train --think --lr 5e-5 --epochs 1 --rank 16

Rows in: gen_synthetic's schema {category, question, context, answer}. Essays are skipped (the essay goes
to the base with no adapter). history_ext_synth.jsonl is not used (templated filler, see the doc).
Matching: closed types need the same letters/P-F sequence as the key; open types need at least
--min-recall of the key's content words (5+ letters, first 5 letters compared, so Polish inflection
matches). The open-answer check is a heuristic, not a grader.
Rows out: {"messages": [system, user, {"role": "assistant", "content": answer, "reasoning_content": thought}], ...}
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from matura_router.categories import Category  # noqa: E402
from matura_router.prompts import build_messages  # noqa: E402

CLOSED = {"closed_choice", "true_false", "matching", "chronology"}


def closed_key(s: str) -> list[str]:
    s = s.replace("*", "")
    return re.findall(r"\b([A-H]|P|F|prawda|fałsz)\b", s)


def stems(s: str) -> set[str]:
    return {w[:5] for w in re.findall(r"\w+", s.lower()) if len(w) >= 5}


def correct(cat: str, answer: str, gold: str, min_recall: float) -> float:
    if cat in CLOSED:
        return 1.0 if closed_key(answer) and closed_key(answer) == closed_key(gold) else 0.0
    g = stems(gold)
    return len(g & stems(answer)) / len(g) if g and len(g & stems(answer)) / len(g) >= min_recall else 0.0


def ask(url: str, msgs: list, max_tokens: int, temperature: float) -> tuple[str, str]:
    body = {"messages": msgs, "max_tokens": max_tokens, "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": True}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        m = json.loads(r.read())["choices"][0]["message"]
    return (m.get("reasoning_content") or "").strip(), (m.get("content") or "").strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080")
    p.add_argument("--input", nargs="+", required=True)
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--samples", type=int, default=4, help="tries per question; the best correct one is kept")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=4000, help="thinking + answer, as the exam's raw cap")
    p.add_argument("--min-recall", type=float, default=0.5)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=0, help="first N rows only (smoke run)")
    a = p.parse_args()

    rows, seen = [], set()
    for f in a.input:
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            key = (r["question"].strip(), r["answer"].strip())
            if r.get("category") == "essay" or key in seen:
                continue
            seen.add(key)
            rows.append(r)
    rows = rows[: a.limit] if a.limit else rows
    print(f"{len(rows)} questions x {a.samples} samples", flush=True)

    def one(r):
        # The exam's raw prompt (router.py mode "raw": GENERAL system prompt, no template help).
        msgs = build_messages(Category.GENERAL, r["question"], r.get("context", ""), fill_template=False)
        best = None
        for _ in range(a.samples):
            try:
                thought, ans = ask(a.url, msgs, a.max_tokens, a.temperature)
            except Exception as e:  # noqa: BLE001 - a failed sample is just not kept
                print("request failed:", e, file=sys.stderr)
                continue
            if not thought or not ans:   # ran out of thinking budget: not an exam-like sample
                continue
            s = correct(r.get("category", ""), ans, r["answer"], a.min_recall)
            if s and (best is None or s > best[0]):
                best = (s, thought, ans)
            if s == 1.0:
                break
        if best is None:
            return None
        return {"messages": msgs + [{"role": "assistant", "content": best[2], "reasoning_content": best[1]}],
                "category": r.get("category"), "match": round(best[0], 2)}

    kept = 0
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as out, cf.ThreadPoolExecutor(a.workers) as ex:
        for i, res in enumerate(ex.map(one, rows), 1):
            if res:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                kept += 1
            if i % 50 == 0:
                print(f"{i}/{len(rows)} done, {kept} kept", flush=True)
    print(f"kept {kept} of {len(rows)} -> {a.out}")


if __name__ == "__main__":
    main()
