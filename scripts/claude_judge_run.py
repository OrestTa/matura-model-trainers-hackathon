#!/usr/bin/env python3
"""Claude grading of one run on all four held-out papers (May 2023-2026), one grader per paper.

    python scripts/claude_judge_run.py dump  <answers.jsonl> --work <dir>
        # writes <dir>/<paper>.txt (question, rubric, gold, answer per item) for each paper present
    # a grader per paper writes <dir>/<paper>.grades.json = {"<item id>": points}
    python scripts/claude_judge_run.py score <answers.jsonl> --work <dir> --out results/judged/<run> --model "<model>"
        # writes results/judged/<run>/<paper>/claude_score.json per graded paper and summary.json with the /240

Wraps scripts/claude_judge_official.py (per-paper dump/score) and scripts/deck_breakdown.py.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ["2023-05", "2024-05", "2025-05", "2026-05"]
KLUCZ = {
    "2023-05": "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2023/Historia/MHIP-R0-100-2305-zasady.pdf",
    "2024-05": "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2024/Historia/MHIP-R0-100-2405-zasady.pdf",
    "2025-05": "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2025/zasady_oceniania/MHIP-R0-100-2505-zasady.pdf",
    "2026-05": "https://cke.gov.pl/images/_EGZAMIN_MATURALNY_OD_2023/Arkusze_egzaminacyjne/2026/Historia/MHIP-R0-100-2605-zasady.pdf",
}
JUDGE = [sys.executable, str(ROOT / "scripts/claude_judge_official.py")]


def papers_in(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return [p for p in PAPERS if any(r["id"].startswith(p + "-z") for r in rows)]


def dump(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    for p in papers_in(a.answers):
        out = subprocess.run(JUDGE + ["dump", a.answers, "--paper", p], capture_output=True, text=True, check=True).stdout
        (work / f"{p}.txt").write_text(out)
        print(work / f"{p}.txt", out.count("====="), "items")


def score(a):
    work, out = Path(a.work), Path(a.out)
    summary = {"answers": a.answers, "model": a.model, "judge": "claude", "papers": {}}
    for p in papers_in(a.answers):
        g = work / f"{p}.grades.json"
        if not g.exists():
            print(f"{p}: no grades yet")
            continue
        dest = out / p / "claude_score.json"
        subprocess.run(JUDGE + ["score", a.answers, "--paper", p, "--grades", str(g), "--out", str(dest),
                                "--model", a.model, "--klucz", KLUCZ[p], "--note", a.note], check=True)
        s = json.loads(dest.read_text())
        summary["papers"][p] = {"total": s["total"], "max": s["max"], "pct": s["pct"], "klucz": KLUCZ[p]}
        subprocess.run([sys.executable, str(ROOT / "scripts/deck_breakdown.py"), str(dest)], check=True)
    t = sum(v["total"] for v in summary["papers"].values())
    m = sum(v["max"] for v in summary["papers"].values())
    summary.update(total=t, max=m, pct=round(100 * t / m, 1) if m else None)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"{a.model}: " + ", ".join(f"{p} {v['total']:g}/{v['max']:g}" for p, v in summary["papers"].items())
          + f" | overall {t:g}/{m:g} = {summary['pct']}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dump", "score"])
    ap.add_argument("answers")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out")
    ap.add_argument("--model", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    dump(a) if a.cmd == "dump" else score(a)
