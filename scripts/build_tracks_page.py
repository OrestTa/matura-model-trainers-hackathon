"""One results page with a tab per prize track: best score, best progress, smallest >= 35%.

    python scripts/build_tracks_page.py            # -> results/tracks/index.html

Reads results/tracks.json (curated rows, track status, candidates), every
runs/baselines/*/*/summary.json and results/**/summary.json (run_baselines output,
added automatically), and the job table in docs/STATUS.md (each job goes to the
tracks whose `job_match` regex it matches). Writes one self-contained HTML file
(inline SVG charts, no images), so it can be committed and published as is.

Eval labels: headline = held-out May 2023-2026 papers with a judge (240 pts);
headline-auto = same papers, auto-scorable items only (no judge);
contaminated = older papers (also training data); dev = not the matura.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_LIMIT_GB, TRAINED_LIMIT_GB, SMALL_BAR = 8.0, 8.8, 35.0
MATURA = ("headline", "headline-auto")
EVAL_LABEL = {
    "headline": "Held-out 2023–26, judged",
    "headline-auto": "Held-out 2023–26, auto-scored items only",
    "contaminated": "Older papers (contaminated)",
    "dev": "Not the matura",
}
STAGE_LABEL = {"base": "Base", "harness": "Base + harness", "trained": "Trained"}
MODE_STAGE = {"raw": "base", "routed": "harness", "rag": "harness", "adapters": "trained"}
MODE_METHOD = {"raw": "plain prompt (untouched)", "routed": "router prompts",
               "rag": "router prompts + RAG", "adapters": "router + RAG + LoRA"}

CEST = timezone(timedelta(hours=2), "CEST")  # the whole hackathon is in summer time


def cest(stamp) -> str:
    """'YYYY-MM-DD HH:MM[ UTC]' in UTC -> the same in CEST; anything else is returned as is."""
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})(?: UTC)?", str(stamp or "").strip())
    if not m:
        return "" if stamp is None else str(stamp)
    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return t.astimezone(CEST).strftime("%Y-%m-%d %H:%M CEST")


esc = lambda v: html.escape("" if v is None else str(v))  # noqa: E731


# ---------------------------------------------------------------- data

def eval_kind(path: str, judged: bool) -> str:
    if "matura_all" in path:
        return "contaminated"
    if "matura" in path:
        return "headline" if judged else "headline-auto"
    return "dev"


def deck_sizes() -> dict:
    """model key -> (reference GB, source label) from the configs' deck_size_gb (scripts/model_size.py)."""
    import sys
    import yaml
    sys.path.insert(0, str(ROOT / "scripts"))
    from model_size import deck_size
    out = {}
    for cfg in ("configs/small_models.yaml", "configs/models.yaml"):  # models.yaml wins on shared keys
        try:
            models = yaml.safe_load((ROOT / cfg).read_text())["models"]
        except (OSError, KeyError, TypeError):
            continue
        out.update({k: deck_size(v) for k, v in models.items()})
    return out


def load_summaries() -> list[dict]:
    deck = deck_sizes()
    files = sorted((ROOT / "runs/baselines").glob("*/*/summary.json"))
    files += sorted((ROOT / "results").glob("**/summary.json"))
    rows = []
    for f in files:
        try:
            s = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if s.get("pct") is None or "model" not in s:
            continue
        mode = s.get("mode", "raw")
        run = f.parent.parent.name
        judged = bool(s.get("judge"))
        # With a judge the score is over all 240 points: rows the judge left unscored count as 0
        # (`pct` alone divides by the scored rows only and would overstate the result).
        pct = s.get("pct_all_rows") if judged and s.get("pct_all_rows") is not None else s["pct"]
        # The organisers' deck size is shown next to ours; pass/fail still uses disk_gb (pending Orest).
        deck_gb, size_src = deck.get(s["model"], (None, "not in deck"))
        rows.append({
            "size_src": f"deck {deck_gb:.2f} GB ({size_src[5:]})" if deck_gb is not None else "not in deck",
            "id": f"{run}/{s['model']}/{mode}", "run": run, "model": s["model"],
            "stage": MODE_STAGE.get(mode, "harness"), "mode": mode,
            "method": MODE_METHOD.get(mode, mode),
            "eval": eval_kind(str(s.get("eval", "")), judged),
            "pct": pct, "pct_text_only": s.get("pct_text_only"),
            "earned": s.get("earned"), "max": s.get("max"),
            "disk_gb": s.get("disk_gb"),
            "by": "Claude threads", "verified": True,
            "date": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "note": f"run {run}",
        })
    # Trained / harness rows compare against the untouched raw row of the same model and run.
    raw = {(r["run"], r["model"], r["eval"]): r["id"] for r in rows if r["mode"] == "raw"}
    for r in rows:
        if r["mode"] != "raw":
            r["base"] = raw.get((r["run"], r["model"], r["eval"]))
    return rows


def load_jobs() -> list[dict]:
    path = ROOT / "docs/STATUS.md"
    if not path.exists():
        return []
    jobs, head = [], None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if head is None:
            head = cells
        elif not set("".join(cells)) <= set("-: "):
            jobs.append(dict(zip(head, cells)))
    return jobs


def job_state(state: str) -> str:
    s = state.lower()
    if "cancel" in s or "fail" in s or "supersed" in s:
        return "stopped"
    if s.startswith("completed") or s.startswith("done"):
        return "done"
    if s.startswith("running") or s.startswith("active"):
        return "running"
    return "queued"


def legal(r: dict) -> bool:
    gb = r.get("disk_gb")
    limit = TRAINED_LIMIT_GB if r.get("stage") == "trained" else BASE_LIMIT_GB
    return gb is not None and gb <= limit


# ---------------------------------------------------------------- pieces

def pill(kind: str, text: str) -> str:
    return f'<span class="pill {kind}">{esc(text)}</span>'


def result_cells(r: dict) -> str:
    pts = f"{r['earned']:g} / {r['max']:g}" if r.get("earned") is not None and r.get("max") else "–"
    gb = f"{r['disk_gb']:.2f}" if r.get("disk_gb") is not None else "–"
    size_flag = "" if r.get("disk_gb") is None or legal(r) else ' <span class="over">over</span>'
    if r.get("disk_gb") is not None:
        size_flag += f"<div class='sub'>{esc(r.get('size_src') or 'not in deck')}</div>"
    src = pill("ok", "ours") if r.get("verified") else pill("warn", "unverified")
    txt = f"{r['pct_text_only']:.1f}" if r.get("pct_text_only") is not None else "–"
    return (f"<td class='l'><b>{esc(r['model'])}</b><div class='sub'>{esc(r.get('method'))}</div></td>"
            f"<td class='l'>{esc(STAGE_LABEL.get(r.get('stage'), r.get('stage')))}</td>"
            f"<td class='n'><b>{r['pct']:.1f}%</b></td><td class='n'>{txt}</td><td class='n'>{pts}</td>"
            f"<td class='n'>{gb}{size_flag}</td>"
            f"<td class='l'>{src}<div class='sub'>{esc(r.get('by'))} · {esc(cest(r.get('date')))}</div></td>"
            f"<td class='l note'>{esc(r.get('note'))}</td>")


RESULT_HEAD = ("<tr><th class='l'>Model</th><th class='l'>Stage</th><th>Score</th><th>Text-only</th>"
               "<th>Points</th><th>GB on disk</th><th class='l'>Source</th><th class='l'>Note</th></tr>")


def results_by_eval(rows: list[dict], order=("headline", "headline-auto", "contaminated", "dev")) -> str:
    out = []
    for kind in order:
        group = sorted([r for r in rows if r["eval"] == kind], key=lambda r: -r["pct"])
        if not group:
            continue
        cls = "" if kind in MATURA else " muted"
        out.append(f"<h4 class='evalhead{cls}'>{esc(EVAL_LABEL[kind])} <span>{len(group)}</span></h4>"
                   f"<div class='scroll'><table class='{cls.strip()}'>{RESULT_HEAD}"
                   + "".join(f"<tr>{result_cells(r)}</tr>" for r in group) + "</table></div>")
    return "".join(out) or "<p class='empty'>No results yet.</p>"


def bar_chart(rows: list[dict], marker: float | None = None) -> str:
    rows = sorted(rows, key=lambda r: -r["pct"])[:12]
    if not rows:
        return "<p class='empty'>No held-out scores yet.</p>"
    lw, w, bh, gap = 230, 640, 22, 8
    h = len(rows) * (bh + gap) + 28
    x = lambda v: lw + (w - lw - 50) * v / 100  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Scores on held-out papers">']
    for t in (0, 25, 50, 75, 100):
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="0" y2="{h - 20}" class="grid"/>'
                     f'<text x="{x(t):.1f}" y="{h - 6}" class="tick" text-anchor="middle">{t}%</text>')
    if marker is not None:
        parts.append(f'<line x1="{x(marker):.1f}" x2="{x(marker):.1f}" y1="0" y2="{h - 20}" class="bar35"/>')
    for i, r in enumerate(rows):
        y = i * (bh + gap) + 4
        cls = "b-ok" if legal(r) else "b-over"
        if not r.get("verified"):
            cls += " b-unv"
        name = r["model"] if len(r["model"]) <= 34 else r["model"][:33] + "…"
        parts.append(f'<text x="{lw - 8}" y="{y + bh / 2 + 4}" class="lab" text-anchor="end">{esc(name)}</text>'
                     f'<rect x="{lw}" y="{y}" width="{max(1, x(r["pct"]) - lw):.1f}" height="{bh}" rx="3" class="{cls}"/>'
                     f'<text x="{x(r["pct"]) + 6:.1f}" y="{y + bh / 2 + 4}" class="val">{r["pct"]:.1f}%</text>')
    parts.append("</svg>")
    return "".join(parts)


def dumbbell(pairs: list[tuple[dict, dict]]) -> str:
    if not pairs:
        return "<p class='empty'>No base → trained pairs on the held-out papers yet.</p>"
    lw, w, rh = 230, 640, 34
    h = len(pairs) * rh + 28
    x = lambda v: lw + (w - lw - 50) * v / 100  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Base versus trained score">']
    for t in (0, 25, 50, 75, 100):
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="0" y2="{h - 20}" class="grid"/>'
                     f'<text x="{x(t):.1f}" y="{h - 6}" class="tick" text-anchor="middle">{t}%</text>')
    for i, (b, t) in enumerate(pairs):
        y = i * rh + 16
        d = t["pct"] - b["pct"]
        cls = "up" if d >= 0 else "down"
        name = t["model"] if len(t["model"]) <= 34 else t["model"][:33] + "…"
        parts.append(f'<text x="{lw - 8}" y="{y + 4}" class="lab" text-anchor="end">{esc(name)}</text>'
                     f'<line x1="{x(b["pct"]):.1f}" x2="{x(t["pct"]):.1f}" y1="{y}" y2="{y}" class="link {cls}"/>'
                     f'<circle cx="{x(b["pct"]):.1f}" cy="{y}" r="5" class="dot-base"/>'
                     f'<circle cx="{x(t["pct"]):.1f}" cy="{y}" r="6" class="dot-{cls}"/>'
                     f'<text x="{max(x(b["pct"]), x(t["pct"])) + 10:.1f}" y="{y + 4}" class="val {cls}">'
                     f'{d:+.1f} pts</text>')
    parts.append("</svg>")
    return "".join(parts)


def size_scatter(rows: list[dict], candidates: list[dict]) -> str:
    w, h, l, b, top = 640, 300, 48, 36, 12
    xmax = 16.0
    x = lambda v: l + (w - l - 16) * min(v, xmax) / xmax  # noqa: E731
    y = lambda v: top + (h - top - b) * (1 - v / 100)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Size on disk versus score">',
             f'<rect x="{x(BASE_LIMIT_GB):.1f}" y="{top}" width="{x(xmax) - x(BASE_LIMIT_GB):.1f}" '
             f'height="{h - top - b}" class="overzone"/>',
             f'<text x="{x(BASE_LIMIT_GB) + 6:.1f}" y="{top + 14}" class="tick">over the 8.0 GB base limit</text>']
    for t in (0, 25, 50, 75, 100):
        parts.append(f'<line x1="{l}" x2="{w - 16}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/>'
                     f'<text x="{l - 6}" y="{y(t) + 4:.1f}" class="tick" text-anchor="end">{t}%</text>')
    for g in (0, 2, 4, 6, 8, 10, 12, 14, 16):
        parts.append(f'<text x="{x(g):.1f}" y="{h - b + 16}" class="tick" text-anchor="middle">{g}</text>')
    parts.append(f'<text x="{(l + w) / 2:.0f}" y="{h - 4}" class="tick" text-anchor="middle">GB on disk</text>')
    parts.append(f'<line x1="{l}" x2="{w - 16}" y1="{y(SMALL_BAR):.1f}" y2="{y(SMALL_BAR):.1f}" class="bar35"/>'
                 f'<text x="{l + 6}" y="{y(SMALL_BAR) - 6:.1f}" class="tick b35">35% bar</text>')
    for c in candidates:  # not yet scored: ticks on the x axis
        parts.append(f'<line x1="{x(c["disk_gb"]):.1f}" x2="{x(c["disk_gb"]):.1f}" y1="{h - b - 8}" '
                     f'y2="{h - b}" class="cand"><title>{esc(c["model"])} (not scored yet)</title></line>')
    for r in rows:
        if r.get("disk_gb") is None:
            continue
        cls = "pass" if r["pct"] >= SMALL_BAR and legal(r) else "fail"
        parts.append(f'<circle cx="{x(r["disk_gb"]):.1f}" cy="{y(r["pct"]):.1f}" r="6" class="pt {cls}">'
                     f'<title>{esc(r["model"])}: {r["pct"]:.1f}%, {r["disk_gb"]:.2f} GB</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


def jobs_table(jobs: list[dict]) -> str:
    if not jobs:
        return "<p class='empty'>No jobs for this track in docs/STATUS.md.</p>"
    order = {"running": 0, "queued": 1, "done": 2, "stopped": 3}
    jobs = sorted(jobs, key=lambda j: (order[job_state(j.get("state", ""))], j.get("updated", "")))
    rows = "".join(
        f"<tr><td class='l'><b>{esc(j.get('job'))}</b><div class='sub'>{esc(j.get('owner'))}</div></td>"
        f"<td class='l'>{pill(job_state(j.get('state', '')), job_state(j.get('state', '')))}"
        f"<div class='sub'>{esc(j.get('state'))}</div></td>"
        f"<td class='l mono'>{esc(cest(j.get('updated')))}</td></tr>" for j in jobs)
    return ("<div class='scroll'><table><tr><th class='l'>Job</th><th class='l'>State</th>"
            f"<th class='l'>Updated</th></tr>{rows}</table></div>")


def stat(label: str, value: str, sub: str, tone: str = "") -> str:
    return (f"<div class='stat {tone}'><div class='k'>{esc(label)}</div>"
            f"<div class='v'>{value}</div><div class='s'>{esc(sub)}</div></div>")


def status_block(t: dict) -> str:
    nxt = "".join(f"<li>{esc(n)}</li>" for n in t.get("next", []))
    blk = "".join(f"<li>{esc(n)}</li>" for n in t.get("blockers", []))
    cands = "".join(f"<tr><td class='l'>{esc(c['model'])}</td><td class='n'>{c['disk_gb']:.2f}</td>"
                    f"<td class='l note'>{esc(c.get('note'))}</td></tr>" for c in t.get("candidates", []))
    return (f"<div class='cols'><div><h3>Where it stands</h3><p>{esc(t['status'])}</p>"
            f"<h3>Next</h3><ol>{nxt}</ol>"
            + (f"<h3>Needs a decision or access</h3><ul class='blockers'>{blk}</ul>" if blk else "")
            + f"</div><div><h3>Candidates</h3><div class='scroll'><table><tr><th class='l'>Model</th>"
            f"<th>GB</th><th class='l'>Note</th></tr>{cands}</table></div>"
            f"<p class='sub'>Thread: {esc(t['thread'])}</p></div></div>")


# ---------------------------------------------------------------- tabs

def tab_score(t, rows, jobs):
    mat = [r for r in rows if r["eval"] in MATURA]
    ok = [r for r in mat if legal(r)]
    best = max(ok, key=lambda r: (r["eval"] == "headline", r["pct"]), default=None)
    judged = [r for r in ok if r["eval"] == "headline"]
    bj = max(judged, key=lambda r: r["pct"], default=None)
    stats = (stat("Best legal, held-out", f"{best['pct']:.1f}%" if best else "–",
                  f"{best['model']} · {EVAL_LABEL[best['eval']].lower()}" if best else "nothing yet")
             + stat("Best judged on all 240 pts", f"{bj['pct']:.1f}%" if bj else "–",
                    bj["model"] if bj else "needs the judge run (score-shootout)", "" if bj else "pending")
             + stat("Size limits", "8.0 / 8.8 GB", "base / trained, weights on disk"))
    return (f"<div class='stats'>{stats}</div>"
            f"<h3>Held-out papers, every model</h3><div class='chart'>{bar_chart(mat)}</div>"
            "<p class='legend'><i class='sw ok'></i>within the size limit <i class='sw over'></i>over the limit "
            "<i class='sw unv'></i>hatched: not measured by us</p>"
            + status_block(t) + "<h3>Jobs</h3>" + jobs_table(jobs)
            + "<h3>All results</h3>" + results_by_eval(rows))


def progress_pairs(rows):
    by_id = {r["id"]: r for r in rows}
    pairs = [(by_id[r["base"]], r) for r in rows if r.get("base") in by_id and r["stage"] == "trained"]
    return pairs


def tab_progress(t, rows, jobs):
    pairs = progress_pairs(rows)
    mat = [(b, r) for b, r in pairs if r["eval"] in MATURA and legal(r)]
    best = max(mat, key=lambda p: p[1]["pct"] - p[0]["pct"], default=None)
    untouched = [r for r in rows if r.get("mode") == "raw" and r["eval"] in MATURA]
    stats = (stat("Best gain, held-out", f"{best[1]['pct'] - best[0]['pct']:+.1f} pts" if best else "–",
                  f"{best[1]['model']}: {best[0]['pct']:.1f}% → {best[1]['pct']:.1f}%" if best else "nothing yet")
             + stat("Untouched bases scored", str(len(untouched)),
                    "plain prompt, no harness" if untouched else "none yet; Grok bases ran with router prompts",
                    "" if untouched else "pending")
             + stat("Proposed base", "Bielik-11B-v2", "pretrained, no chat tuning, ~6.7 GB"))
    pair_rows = "".join(
        f"<tr><td class='l'><b>{esc(r['model'])}</b><div class='sub'>{esc(EVAL_LABEL[r['eval']])}</div></td>"
        f"<td class='n'>{b['pct']:.1f}%</td><td class='n'>{r['pct']:.1f}%</td>"
        f"<td class='n'><b class='{'up' if r['pct'] >= b['pct'] else 'down'}'>{r['pct'] - b['pct']:+.1f}</b></td>"
        f"<td class='l'>{pill('ok', 'ours') if r.get('verified') else pill('warn', 'unverified')}</td>"
        f"<td class='l note'>{esc(r.get('note'))}</td></tr>"
        for b, r in sorted(pairs, key=lambda p: (p[1]["eval"] not in MATURA, -(p[1]["pct"] - p[0]["pct"]))))
    table = ("<div class='scroll'><table><tr><th class='l'>Trained model</th><th>Base</th><th>Trained</th>"
             f"<th>Gain (pts)</th><th class='l'>Source</th><th class='l'>Note</th></tr>{pair_rows}</table></div>"
             if pairs else "<p class='empty'>No pairs yet.</p>")
    return (f"<div class='stats'>{stats}</div>"
            f"<h3>Base → trained on held-out papers</h3><div class='chart'>{dumbbell(mat)}</div>"
            "<p class='legend'><i class='sw base'></i>base <i class='sw up'></i>trained, gain "
            "<i class='sw down'></i>trained, loss</p>"
            "<h3>Every base → trained pair</h3><p class='sub'>Rows below the held-out ones are practice or "
            "dev sets and do not count for the prize.</p>" + table
            + status_block(t) + "<h3>Jobs</h3>" + jobs_table(jobs)
            + "<h3>All results</h3>" + results_by_eval(rows))


def tab_small(t, rows, jobs):
    mat = [r for r in rows if r["eval"] in MATURA and r.get("disk_gb") is not None]
    passing = [r for r in mat if r["pct"] >= SMALL_BAR and legal(r)]
    best = min(passing, key=lambda r: r["disk_gb"], default=None)
    norm = lambda s: re.sub(r"[^a-z0-9.]", "", s.lower())  # noqa: E731
    scored = [norm(r["model"]) for r in mat]
    cands = [c for c in t.get("candidates", [])
             if not any(norm(c["model"]).startswith(m) or m.startswith(norm(c["model"])) for m in scored)]
    smallest = min(mat, key=lambda r: r["disk_gb"], default=None)
    stats = (stat("Smallest at ≥35%", f"{best['disk_gb']:.2f} GB" if best else "–",
                  f"{best['model']}, {best['pct']:.1f}%" if best else "nothing passes yet")
             + stat("Smallest scored", f"{smallest['disk_gb']:.2f} GB" if smallest else "–",
                    f"{smallest['model']}, {smallest['pct']:.1f}%" if smallest else "")
             + stat("Tiny models waiting", str(len(cands)), "scoring on the shared GPU and CPU",
                    "pending" if cands else ""))
    return (f"<div class='stats'>{stats}</div>"
            f"<h3>Size vs score, held-out papers</h3><div class='chart'>{size_scatter(mat, cands)}</div>"
            "<p class='legend'><i class='sw pass'></i>≥35% and within the limit <i class='sw fail'></i>below "
            "35% or over the limit <i class='sw cand'></i>tick on the axis: candidate not scored yet</p>"
            + status_block(t) + "<h3>Jobs</h3>" + jobs_table(jobs)
            + "<h3>All results</h3>" + results_by_eval(sorted(rows, key=lambda r: r.get("disk_gb") or 99)))


TABS = {"score": tab_score, "progress": tab_progress, "small": tab_small}


# ---------------------------------------------------------------- page

CSS = """
:root{--bg:#f6f7f8;--panel:#ffffff;--ink:#16191d;--ink2:#4b525b;--ink3:#7d858f;--line:#dfe3e7;
--accent:#b3261e;--accent-soft:#f6e3e1;--ok:#1d7a4f;--ok-soft:#dcefe5;--warn:#9a6200;--warn-soft:#f7ecd4;
--bad:#b3261e;--bar:#2f5d8a;--bar-over:#b9c2cc;--run:#2f5d8a;--run-soft:#e0e9f3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121417;--panel:#1a1d21;
--ink:#eceef0;--ink2:#b3bac2;--ink3:#838b95;--line:#2c3137;--accent:#ff8a80;--accent-soft:#3a2220;--ok:#5fcf97;
--ok-soft:#173327;--warn:#e7b454;--warn-soft:#3a2e15;--bad:#ff8a80;--bar:#7fb0e0;--bar-over:#4a525c;--run:#7fb0e0;--run-soft:#1c2a3a}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121417;--panel:#1a1d21;--ink:#eceef0;--ink2:#b3bac2;--ink3:#838b95;
--line:#2c3137;--accent:#ff8a80;--accent-soft:#3a2220;--ok:#5fcf97;--ok-soft:#173327;--warn:#e7b454;--warn-soft:#3a2e15;
--bad:#ff8a80;--bar:#7fb0e0;--bar-over:#4a525c;--run:#7fb0e0;--run-soft:#1c2a3a}
body{background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding-inline:16px;padding-block:28px 64px}
header h1{font:600 30px/1.15 "Source Serif 4",Georgia,serif;margin:0 0 6px;text-wrap:balance}
header p{margin:0;color:var(--ink2);max-width:70ch}
.meta{font:12px "IBM Plex Mono",ui-monospace,monospace;color:var(--ink3);margin-top:8px}
nav{display:flex;gap:4px;margin:24px 0 0;border-bottom:1px solid var(--line);overflow-x:auto}
nav button{font:inherit;font-weight:600;background:none;border:0;border-bottom:3px solid transparent;color:var(--ink2);
padding:10px 14px;cursor:pointer;white-space:nowrap}
nav button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
nav button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
nav small{display:block;font:400 11px "IBM Plex Mono",monospace;color:var(--ink3)}
section{padding-top:22px}
.goal{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;margin-bottom:16px}
.goal h2{font:600 22px "Source Serif 4",Georgia,serif;margin:0}
.goal p{margin:0;color:var(--ink2);flex-basis:100%}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.stat .k{font:600 11px "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3)}
.stat .v{font:600 28px "IBM Plex Sans",sans-serif;font-variant-numeric:tabular-nums;margin:4px 0 2px}
.stat .s{color:var(--ink2);font-size:13px}
.stat.pending .v{color:var(--ink3)}
h3{font:600 16px "Source Serif 4",Georgia,serif;margin:26px 0 8px}
h4.evalhead{font:600 12px "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.05em;margin:18px 0 6px;color:var(--ink)}
h4.evalhead span{color:var(--ink3)} h4.muted{color:var(--ink3)}
.chart{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px;overflow-x:auto}
.chart svg{display:block;width:100%;min-width:520px;height:auto}
svg text{font:12px "IBM Plex Sans",sans-serif;fill:var(--ink2)} svg .tick{font-size:11px;fill:var(--ink3)}
svg .val{font-weight:600;fill:var(--ink);font-variant-numeric:tabular-nums} svg .lab{fill:var(--ink)}
svg .grid{stroke:var(--line);stroke-width:1} svg .bar35{stroke:var(--accent);stroke-dasharray:4 3;stroke-width:1.5}
svg .b35{fill:var(--accent)} .b-ok{fill:var(--bar)} .b-over{fill:var(--bar-over)} .b-unv{fill-opacity:.55;stroke:var(--bar);stroke-dasharray:3 2}
svg .link{stroke-width:3} svg .link.up{stroke:var(--ok)} svg .link.down{stroke:var(--bad)}
.dot-base{fill:var(--ink3)} .dot-up{fill:var(--ok)} .dot-down{fill:var(--bad)} svg .val.up{fill:var(--ok)} svg .val.down{fill:var(--bad)}
.overzone{fill:var(--line);fill-opacity:.5} .pt.pass{fill:var(--ok)} .pt.fail{fill:var(--ink3)} .cand{stroke:var(--warn);stroke-width:2}
.legend{font-size:12px;color:var(--ink3);display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center;margin:8px 0 0}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
.sw.ok{background:var(--bar)}.sw.over{background:var(--bar-over)}.sw.unv{background:var(--bar);opacity:.5}
.sw.base{background:var(--ink3);border-radius:50%}.sw.up,.sw.pass{background:var(--ok);border-radius:50%}
.sw.down{background:var(--bad);border-radius:50%}.sw.fail{background:var(--ink3);border-radius:50%}.sw.cand{background:var(--warn);width:3px}
.cols{display:grid;grid-template-columns:1.2fr 1fr;gap:24px}
@media (max-width:760px){.cols{grid-template-columns:1fr}}
.cols p{max-width:65ch} ol,ul{padding-left:20px;margin:0} li{margin:3px 0}
.blockers li::marker{color:var(--accent)}
.scroll{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px}
th{font:600 11px "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.04em;color:var(--ink3);text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}
.l{text-align:left}td.l:first-child{min-width:190px}.n{white-space:nowrap}.note{color:var(--ink2);min-width:180px}.mono{font-family:"IBM Plex Mono",monospace;font-size:12px;white-space:nowrap}
table.muted td{color:var(--ink3)} table.muted b{font-weight:500}
.sub{font-size:12px;color:var(--ink3)}
.over{font:600 10px "IBM Plex Mono",monospace;color:var(--bad);text-transform:uppercase}
.up{color:var(--ok)}.down{color:var(--bad)}
.pill{display:inline-block;font:600 10.5px "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.05em;padding:2px 7px;border-radius:99px;white-space:nowrap}
.pill.ok,.pill.done{background:var(--ok-soft);color:var(--ok)}.pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.running{background:var(--run-soft);color:var(--run)}.pill.queued,.pill.waiting{background:var(--warn-soft);color:var(--warn)}
.pill.stopped{background:var(--line);color:var(--ink3)}
.empty{color:var(--ink3);font-style:italic}
.key{margin-top:40px;border-top:1px solid var(--line);padding-top:16px;font-size:13px;color:var(--ink2)}
.key dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0}.key dt{font-weight:600;color:var(--ink)}
@media (max-width:520px){.key dl{grid-template-columns:1fr}.key dd{margin:0 0 6px}}
"""

JS = """
(function(){var tabs=[].slice.call(document.querySelectorAll('nav button'));
function show(id){tabs.forEach(function(b){var on=b.dataset.tab===id;b.setAttribute('aria-selected',on);
document.getElementById('tab-'+b.dataset.tab).hidden=!on;});
try{localStorage.setItem('tracktab',id)}catch(e){}}
tabs.forEach(function(b){b.addEventListener('click',function(){show(b.dataset.tab);
try{history.replaceState(null,'','#'+b.dataset.tab)}catch(e){}})});
var h=(location.hash||'').slice(1),s=null;try{s=localStorage.getItem('tracktab')}catch(e){}
var ids=tabs.map(function(b){return b.dataset.tab});show(ids.indexOf(h)>=0?h:(ids.indexOf(s)>=0?s:ids[0]));})();
"""


def build(data: dict, rows: list[dict], jobs: list[dict]) -> str:
    tracks = data["tracks"]
    nav, secs = [], []
    for t in tracks:
        rx = re.compile(t.get("job_match", "$^"), re.I)
        tj = [j for j in jobs if rx.search(" ".join(j.get(k, "") for k in ("job", "what", "owner")))]
        nav.append(f'<button role="tab" data-tab="{t["id"]}" aria-selected="false">{esc(t["name"])}'
                   f'<small>{esc(t.get("short", ""))}</small></button>')
        secs.append(f'<section id="tab-{t["id"]}" role="tabpanel"><div class="goal"><h2>{esc(t["name"])}</h2>'
                    f'{pill(t.get("state", "waiting"), t.get("state", "waiting"))}<p>{esc(t["goal"])}</p></div>'
                    + TABS[t["id"]](t, rows, tj) + "</section>")
    key = "".join(f"<dt>{esc(v)}</dt><dd>{esc(d)}</dd>" for v, d in [
        (EVAL_LABEL["headline"], "May 2023–2026 CKE papers (154 items, 240 pts), open answers graded by the local judge. "
                                 "This is the headline number."),
        (EVAL_LABEL["headline-auto"], "Same papers, only the items scored without a judge (about 60 items, 70 pts). "
                                      "The percentage is of those points, not of the whole exam."),
        (EVAL_LABEL["contaminated"], "Older papers (2015–2022, mocks). Used as training data, so they overstate trained models."),
        (EVAL_LABEL["dev"], "Practice geography exam and the 90-question MCQ set. Several adapters were trained on these."),
        ("Unverified", "Measured by the Grok bot in its own runs; the raw outputs are not in this repo."),
        ("Size", "Weights on disk. Base at most 8.0 GB, trained model (base + adapters) at most 8.8 GB."),
    ])
    now = datetime.now(CEST).strftime("%Y-%m-%d %H:%M CEST")
    return f"""<title>Matura Prize Tracks</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header><h1>Matura prize tracks</h1>
<p>Tarasiuk Lab at Warsaw Model Trainers: every score, baseline and job for the three prizes. Headline numbers come
from the held-out May 2023–2026 historia papers; older papers are marked as contaminated.</p>
<div class="meta">Built {now} · data updated {esc(cest(data.get('updated')))} · {len(rows)} results · exam starts 2026-09-27 11:00 CEST</div></header>
<nav role="tablist">{''.join(nav)}</nav>
{''.join(secs)}
<div class="key"><h3>How to read the numbers</h3><dl>{key}</dl>
<p class="sub">Generated by scripts/build_tracks_page.py from results/tracks.json, run summaries and docs/STATUS.md.</p></div>
</div>
<script>{JS}</script>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=str(ROOT / "results/tracks.json"))
    p.add_argument("--out", default=str(ROOT / "results/tracks/index.html"))
    args = p.parse_args()
    data = json.loads(Path(args.data).read_text())
    curated = data.get("results", [])
    seen = {r["id"] for r in curated}
    rows = curated + [r for r in load_summaries() if r["id"] not in seen]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(data, rows, load_jobs()), encoding="utf-8")
    print(f"{len(rows)} results, {len(data['tracks'])} tracks -> {out}")


if __name__ == "__main__":
    main()
