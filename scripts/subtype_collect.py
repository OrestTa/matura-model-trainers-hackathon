#!/usr/bin/env python3
"""Collects subtype-sweep answers from Nebius job logs ('ANS\\t<json>' lines, subtype_sweep.py --emit)
into <out>/<group>/<candidate>/answers.jsonl, deduplicated by (group, candidate, id). No bucket needed:

    NEBIUS_IAM_TOKEN=... python scripts/subtype_collect.py --prefix subtype-x --out results/subtype/dev
Prints per job state and answer counts, so it doubles as the watch loop's progress check.
"""
import argparse
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

N = os.path.expanduser("~/.nebius/bin/nebius")


def nb(*a):
    return subprocess.run([N, *a], capture_output=True, text=True).stdout


ap = argparse.ArgumentParser()
ap.add_argument("--prefix", required=True)
ap.add_argument("--project", default="project-e00r07hbpr00483g1ant9w")
ap.add_argument("--out", required=True)
a = ap.parse_args()
jobs = json.loads(nb("ai", "job", "list", "--parent-id", a.project, "--format", "json") or "{}").get("items", [])
jobs = [j for j in jobs if j["metadata"]["name"].startswith(a.prefix)]
rows = defaultdict(dict)
for j in sorted(jobs, key=lambda j: j["metadata"]["name"]):
    log = nb("ai", "job", "logs", j["metadata"]["id"])
    n = 0
    for line in log.splitlines():
        if line.startswith("ANS\t"):
            try:
                r = json.loads(line[4:])
            except json.JSONDecodeError:
                continue
            rows[(r.pop("group"), r.pop("candidate"))][str(r["id"])] = r
            n += 1
    tail = [l for l in log.splitlines() if l.startswith("==") or "rror" in l][-1:]
    print(f"{j['metadata']['name']}\t{j['status'].get('state')}\t{n} answers\t{tail[0][:100] if tail else ''}")
for (g, c), rs in rows.items():
    d = Path(a.out) / g / c
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "answers.jsonl", "w", encoding="utf-8") as fh:
        for r in sorted(rs.values(), key=lambda r: r["id"]):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{sum(len(v) for v in rows.values())} answers in {len(rows)} runs -> {a.out}")
