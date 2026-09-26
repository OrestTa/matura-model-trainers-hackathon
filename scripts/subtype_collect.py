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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

N = os.path.expanduser("~/.nebius/bin/nebius")


def nb(*a):
    return subprocess.run([N, *a], capture_output=True, text=True).stdout


def job_log(jid, since, until, cap=100):
    """`nebius ai job logs` returns at most ~100 lines per call, so page through time windows,
    halving a window whenever it comes back full."""
    fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
    out, t = [], since
    while t < until:
        step = timedelta(seconds=120)
        while True:
            lines = nb("ai", "job", "logs", jid, "--since", fmt(t), "--until", fmt(min(t + step, until))).splitlines()
            if len(lines) < cap or step <= timedelta(seconds=2):
                break
            step /= 2
        out += lines
        t += step
    return "\n".join(out)


ap = argparse.ArgumentParser()
ap.add_argument("--prefix", required=True)
ap.add_argument("--project", default="project-e00r07hbpr00483g1ant9w")
ap.add_argument("--out", required=True)
a = ap.parse_args()
jobs = json.loads(nb("ai", "job", "list", "--parent-id", a.project, "--format", "json") or "{}").get("items", [])
jobs = [j for j in jobs if j["metadata"]["name"].startswith(a.prefix)]
rows = defaultdict(dict)
def fetch(j):
    t0 = datetime.fromisoformat(j["metadata"]["created_at"].replace("Z", "+00:00"))
    fin = j["status"].get("finished_at")
    t1 = datetime.fromisoformat(fin.replace("Z", "+00:00")) + timedelta(seconds=60) if fin else datetime.now(timezone.utc)
    return j, job_log(j["metadata"]["id"], t0, t1)


with ThreadPoolExecutor(16) as pool:
    fetched = list(pool.map(fetch, sorted(jobs, key=lambda j: j["metadata"]["name"])))
for j, log in fetched:
    n = ok = 0
    for line in log.splitlines():
        if line.startswith("ANS\t"):
            try:
                r = json.loads(line[4:])
            except json.JSONDecodeError:
                continue
            key, rid = (r.pop("group"), r.pop("candidate")), str(r["id"])
            old = rows[key].get(rid)
            if old is None or not (old.get("answer") or "").strip():  # a real answer beats a crashed one
                rows[key][rid] = r
            n += 1
            ok += bool((r.get("answer") or "").strip())
    tail = [l for l in log.splitlines() if l.startswith("==") or "rror" in l][-1:]
    print(f"{j['metadata']['name']}\t{j['status'].get('state')}\t{n} answers ({ok} non-empty)\t{tail[0][:100] if tail else ''}")
for (g, c), rs in rows.items():
    d = Path(a.out) / g / c
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "answers.jsonl", "w", encoding="utf-8") as fh:
        for r in sorted(rs.values(), key=lambda r: r["id"]):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{sum(len(v) for v in rows.values())} answers in {len(rows)} runs -> {a.out}")
