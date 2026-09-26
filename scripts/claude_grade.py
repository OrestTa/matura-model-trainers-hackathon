#!/usr/bin/env python3
"""Grades the open answers of judge-less baseline runs with Claude, then rescores the runs.

Since 2026-09-26 15:26 CEST the GPU box serves no judge model (JUDGE_HF=""), so every row that
run_baselines.py would have sent to the judge is saved with score=None. This fills those rows in:

    python scripts/claude_grade.py prep RUN_DIR... --out GRADE_DIR
        # finds every answers.jsonl under the run dirs, collects the ungraded open rows
        # (score None), drops answers already in the grade cache, and writes one batch per
        # exam item (all runs' answers to that item together, so they're graded consistently)
    # a Claude session writes GRADE_DIR/batch_NNN.grades.json = {"<answer key>": points, ...}
    python scripts/claude_grade.py merge RUN_DIR... --out GRADE_DIR
        # adds the batch grades to the cache, then for every run writes answers.claude.jsonl and
        # summary.claude.json next to its answers.jsonl, and a copy under results/claude-graded/

The grading is the pipeline's own: matura_router.scoring.JUDGE_PROMPT, the CKE rubric and the
item's point scale. Auto-scored rows (closed, true/false, matching, keywords, wrong verdict on a
"Rozstrzygnij" item) keep the scores the run gave them. Summaries are made by
matura_router.evaluate.summarise, so the headline is the held-out May 2023-2026 papers and older
papers sit under "trained_on_papers". Every summary says judge = "claude": don't mix these with
the Qwen3-14B-judged runs from before 15:26 CEST.

The cache (results/claude-graded/grades.jsonl: item id, answer hash, points) is committed, so an
answer identical to one graded before is never graded twice.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from matura_router.evaluate import summarise  # noqa: E402
from matura_router.scoring import JUDGE_PROMPT  # noqa: E402

CACHE = ROOT / "results/claude-graded/grades.jsonl"
JUDGE = "claude (Claude session, scripts/claude_grade.py, JUDGE_PROMPT + CKE rubric)"
EVALS = [ROOT / "data/eval/matura_all.jsonl", ROOT / "data/eval/matura.jsonl",
         Path("/mnt/project-files/data/eval/matura_all.jsonl"),
         Path("/mnt/project-files/data/eval/matura.jsonl")]


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def eval_rows():
    rows = {}
    for p in EVALS:  # matura_all first; the headline set has the same ids and text
        if p.exists():
            for r in load(p):
                rows.setdefault(r["id"], r)
    if not rows:
        sys.exit("no eval set: run scripts/fetch_matura.py --papers all or copy it from /mnt/project-files")
    return rows


def key(item_id, answer):
    return hashlib.sha1(f"{item_id}\x00{answer}".encode()).hexdigest()[:16]


def load_cache():
    return {g["key"]: g["points"] for g in load(CACHE)} if CACHE.exists() else {}


def runs(dirs):
    for d in dirs:
        for a in sorted(Path(d).rglob("answers.jsonl")):
            yield a


def prep(args):
    rows, cache = eval_rows(), load_cache()
    todo = {}
    for a in runs(args.runs):
        for r in load(a):
            if r.get("score") is not None or r["id"] not in rows:
                continue
            k = key(r["id"], r.get("answer") or "")
            if k in cache:
                continue
            todo.setdefault(r["id"], {})[k] = (r.get("answer") or "").strip()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    batch, size = [], 0
    for iid in sorted(todo):
        row = rows[iid]
        pts = int(float(row.get("points", 1)))
        answers = {k: v for k, v in todo[iid].items() if v}
        empty = [k for k, v in todo[iid].items() if not v]
        if empty:  # an empty answer is 0 without asking anyone
            (out / f"auto_empty_{iid}.grades.json").write_text(json.dumps({k: 0 for k in empty}))
        if not answers:
            continue
        question = row["question"]
        if row.get("context"):
            question = f"{row['context'][:3000]}\n\n{question}"
        gold = row.get("gold") or ""
        rubric = row.get("rubric") or "brak – oceń według przykładu"
        batch.append({"item": iid, "max_points": pts,
                      "prompt": JUDGE_PROMPT.format(question=question, rubric=rubric,
                                                    gold=gold if gold != rubric else "(patrz zasady oceniania)",
                                                    answer="<ODPOWIEDŹ>", points=pts),
                      "answers": [{"key": k, "answer": v[:8000]} for k, v in sorted(answers.items())]})
        size += len(answers)
        if size >= args.size:
            (out / f"batch_{n:03d}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1))
            n, batch, size = n + 1, [], 0
    if batch:
        (out / f"batch_{n:03d}.json").write_text(json.dumps(batch, ensure_ascii=False, indent=1))
        n += 1
    total = sum(len(v) for v in todo.values())
    print(f"{total} ungraded answers over {len(todo)} items -> {n} batches in {out}")


def merge(args):
    rows = eval_rows()
    cache = load_cache()
    new = {}
    for f in sorted(Path(args.out).glob("*.grades.json")):
        new.update(json.loads(f.read_text()))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with open(CACHE, "a", encoding="utf-8") as fh:
        for k, v in new.items():
            if k not in cache:
                fh.write(json.dumps({"key": k, "points": float(v)}) + "\n")
                cache[k] = float(v)
                added += 1
    print(f"cache: +{added} grades, {len(cache)} total")
    report = []
    for a in runs(args.runs):
        res, missing = [], 0
        for r in load(a):
            if r.get("score") is None and r["id"] in rows:
                k = key(r["id"], r.get("answer") or "")
                if k in cache:
                    mx = float(rows[r["id"]].get("points", 1))
                    r = {**r, "score": max(0.0, min(mx, float(cache[k]))), "graded_by": "claude"}
                else:
                    missing += 1
            res.append(r)
        s = summarise(res)
        old = a.parent / "summary.json"
        meta = json.loads(old.read_text()) if old.exists() else {}
        for k in ("model", "mode", "eval", "served", "hf_id", "params_b", "disk_gb", "quantization"):
            if k in meta:
                s[k] = meta[k]
        s.setdefault("model", a.parent.parent.name)
        s.setdefault("mode", a.parent.name)
        s.update(judge=JUDGE, judge_kind="claude", ungraded_open=missing,
                 source=str(a))
        with open(a.parent / "answers.claude.jsonl", "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in res)
        (a.parent / "summary.claude.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))
        # results/claude-graded/<job>/<model>/<mode>/summary.json (job = dir above "baselines")
        parts = a.parent.parts
        job = parts[parts.index("baselines") - 1] if "baselines" in parts else a.parent.parent.parent.name
        dest = ROOT / "results/claude-graded" / job / s["model"] / s["mode"]
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=2))
        tr = s.get("trained_on_papers", {})
        report.append((job, s["model"], s["mode"], s.get("pct_all_rows"), s.get("earned"),
                       sum(r["points"] for r in res if r.get("paper") in HEAD), missing,
                       tr.get("pct_all_rows")))
    print("job | model | mode | headline % (all pts) | earned/max | ungraded | contaminated %")
    for j, m, mo, p, e, mx, miss, c in report:
        print(f"{j} | {m} | {mo} | {p} | {e}/{mx:g} | {miss} | {c}")


HEAD = {"2023-05", "2024-05", "2025-05", "2026-05"}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["prep", "merge"])
    p.add_argument("runs", nargs="+", help="run dirs; every answers.jsonl below them is graded")
    p.add_argument("--out", required=True, help="grading work dir (batches and their grades)")
    p.add_argument("--size", type=int, default=60, help="answers per batch")
    args = p.parse_args()
    prep(args) if args.cmd == "prep" else merge(args)
