#!/usr/bin/env python3
"""Runs every candidate setup of configs/subtype_grid.yaml on the items of its subtype.

Orest's five subtypes (matura_router/subtypes.py): closed_text, closed_image, open_text,
open_image, essay. An item's subtype is the one the stage harness would give it: the router's
category (rule classifier, no key needed) plus whether pictures come with it. Each candidate
only answers its own subtype's items, so the whole grid costs about (candidates per subtype) x
(eval set) answers. Every (candidate, item) pair goes into one thread pool, so a llama-server
with many slots stays full.

    python scripts/subtype_sweep.py --base-url http://127.0.0.1:8000/v1 --papers dev --raw \\
        --out runs/subtype-sweep
    # -> runs/subtype-sweep/<subtype>/<candidate>/answers.jsonl (+ summary.json)
    #    runs/subtype-sweep/raw/raw/answers.jsonl   (--raw: the plain single-prompt baseline)

Closed items are scored against the key here; open items and essays come out with score None
for the Claude judge (scripts/claude_grade.py prep/merge on the out dir). Then
scripts/subtype_select.py picks each subtype's setup on the dev papers.

--papers dev = every paper except the held-out May 2023-2026 (formuła 2015 papers, the 2022
demo, the Jan 2026 mock); heldout = those four; all = both.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.evaluate import HEADLINE_PAPERS, load_rows, summarise  # noqa: E402
from matura_router.prompts import verdict_matches  # noqa: E402
from matura_router.router import DEFAULT_CONFIG, Router  # noqa: E402
from matura_router.scoring import score_row  # noqa: E402
from matura_router.subtypes import SUBTYPES, Profile, subtype_of  # noqa: E402


def load_grid(path: Path) -> dict[str, dict[str, Profile]]:
    cfg = yaml.safe_load(path.read_text())
    return {st: {name: Profile.from_dict(name, d) for name, d in (cfg.get(st) or {}).items()}
            for st in SUBTYPES}


def item_images(row: dict) -> tuple[Path, ...]:
    out = []
    for p in row.get("images") or ():
        p = Path(p)
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            out.append(p)
        else:
            print(f"[{row['id']}] missing image {p}", file=sys.stderr)
    return tuple(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--eval", default=str(ROOT / "data/eval/matura_all.jsonl"))
    ap.add_argument("--grid", default=str(ROOT / "configs/subtype_grid.yaml"))
    ap.add_argument("--routes", default=str(DEFAULT_CONFIG))
    ap.add_argument("--model", default="gemma4-12b", help="key in configs/models.yaml (vision, extra_body)")
    ap.add_argument("--papers", default="dev", choices=["dev", "heldout", "all"])
    ap.add_argument("--subtypes", default=",".join(SUBTYPES))
    ap.add_argument("--candidates", default="", help="comma list: only these candidate names")
    ap.add_argument("--raw", action="store_true", help="also the plain single-prompt baseline (mode raw)")
    ap.add_argument("--selected", action="store_true",
                    help="also mode subtype with configs/subtypes.yaml (the chosen setup) as out/selected/selected")
    ap.add_argument("--shard", default="0/1", help="i/n: this job runs every n-th task from i (give each shard its own --out)")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--out", default=str(ROOT / "runs/subtype-sweep"))
    args = ap.parse_args()

    rows = load_rows(args.eval)
    if args.papers == "dev":
        rows = [r for r in rows if r.get("paper") not in HEADLINE_PAPERS]
    elif args.papers == "heldout":
        rows = [r for r in rows if r.get("paper") in HEADLINE_PAPERS]

    router = Router.from_config(args.routes)
    router.backend.base_url = args.base_url.rstrip("/")
    spec = yaml.safe_load((ROOT / "configs/models.yaml").read_text())["models"][args.model]
    router.apply_model(spec)
    router._available = router.backend.available_adapters()

    sub_of = {}
    for r in rows:
        imgs = item_images(r) if (router.vision or router.ocr) else ()
        cat = router.classifier.classify(r["question"], r.get("context", "")).category
        sub_of[r["id"]] = (subtype_of(cat, bool(r.get("images"))), imgs)
    print("items per subtype:", dict(Counter(s for s, _ in sub_of.values())), file=sys.stderr)

    grid = load_grid(Path(args.grid))
    want_sub = set(args.subtypes.split(","))
    want_cand = set(filter(None, args.candidates.split(",")))
    tasks = []  # (group, name, mode, profile, row)
    for r in rows:
        st = sub_of[r["id"]][0]
        if st in want_sub:
            for name, prof in grid[st].items():
                if not want_cand or name in want_cand:
                    tasks.append((st, name, "subtype", prof, r))
        if args.raw:
            tasks.append(("raw", "raw", "raw", None, r))
        if args.selected:
            tasks.append(("selected", "selected", "subtype", None, r))
    i, n = map(int, args.shard.split("/"))
    tasks = tasks[i::n]
    print(f"{len(tasks)} answers to make ({len(rows)} items, papers={args.papers}, shard {args.shard})",
          file=sys.stderr)

    def one(t):
        group, name, mode, prof, row = t
        imgs = sub_of[row["id"]][1]
        try:
            res = router.answer(row["question"], row.get("context", ""), mode=mode, images=imgs, profile=prof)
            out = {"id": row["id"], **res.to_dict()}
        except Exception as e:  # noqa: BLE001 - one failed item shouldn't stop the sweep
            out = {"id": row["id"], "answer": "", "raw": "", "category": None, "error": str(e), "latency_s": 0.0}
        out.update(gold_category=row.get("category"), needs_image=bool(row.get("needs_image")),
                   paper=row.get("paper"), points=float(row.get("points", 1)), subtype=sub_of[row["id"]][0],
                   score=score_row(row, out["answer"], None))
        if row.get("decision"):
            out["decision_ok"] = verdict_matches(out["answer"], row["decision"])
        return group, name, out

    results = defaultdict(list)
    t0, done = time.time(), 0
    Path(args.out).mkdir(parents=True, exist_ok=True)
    partial = open(Path(args.out) / "partial.jsonl", "a", encoding="utf-8")  # survives a crash or timeout
    with ThreadPoolExecutor(args.concurrency) as pool:
        for fut in as_completed([pool.submit(one, t) for t in tasks]):
            g, name, out = fut.result()
            results[(g, name)].append(out)
            partial.write(json.dumps({"group": g, "candidate": name, **out}, ensure_ascii=False) + "\n")
            partial.flush()
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"{done}/{len(tasks)} answers, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)

    for (g, name), res in sorted(results.items()):
        d = Path(args.out) / g / name
        d.mkdir(parents=True, exist_ok=True)
        res.sort(key=lambda r: str(r["id"]))
        with open(d / f"answers.jsonl", "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in res)
        s = summarise(res)
        s.update(model=args.model, mode=f"{g}/{name}", papers=args.papers,
                 errors=sum(1 for r in res if r.get("error")),
                 empty=sum(1 for r in res if not (r.get("answer") or "").strip()))
        (d / f"summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))
        print(f"{g}/{name}: {len(res)} answers, {s['errors']} errors, {s['empty']} empty, "
              f"auto-scored {s.get('scored')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
