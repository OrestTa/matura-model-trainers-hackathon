"""Charts and an HTML report from runs/baselines/*/*/summary.json.

    python scripts/plot_baselines.py                   # -> runs/report/
    python scripts/plot_baselines.py --runs s3dir --out report

Writes overall.png (score per model, raw vs routed), by_category.png (model x
question type heatmap), size_vs_score.png (shipped size vs score, with the 8.9 GB
limit and the 35% small-model bar), baselines.csv and index.html.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Validated reference palette (dataviz skill): categorical slots 1-2, blue ramp.
SURFACE, INK, INK_2, INK_3, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
MODE_COLORS = {"raw": "#2a78d6", "routed": "#eb6834", "adapters": "#1baf7a"}
MODE_LABELS = {"raw": "Base model, plain prompt", "routed": "Base model + router prompts",
               "adapters": "Router + LoRA adapters"}
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
SMALL_MODEL_BAR, SIZE_LIMIT_GB = 35.0, 8.9
CATEGORY_ORDER = ["closed_choice", "true_false", "matching", "chronology",
                  "source_analysis", "short_open", "essay", "general"]


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.title.set_color(INK)


def load(runs: Path) -> list[dict]:
    out = []
    for f in sorted(runs.glob("*/*/summary.json")):
        s = json.loads(f.read_text())
        if s.get("pct") is not None:
            out.append(s)
    return out


def plot_overall(summaries, out: Path):
    modes = [m for m in MODE_COLORS if any(s["mode"] == m for s in summaries)]
    best = {}
    for s in summaries:
        best[s["model"]] = max(best.get(s["model"], 0), s["pct"])
    models = sorted(best, key=best.get)  # best at the top
    h = 0.8 / len(modes)
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(models) * len(modes) + 1.6), facecolor=SURFACE)
    style(ax)
    for i, mode in enumerate(modes):
        pct = {s["model"]: s["pct"] for s in summaries if s["mode"] == mode}
        ys = [y - (i - (len(modes) - 1) / 2) * h for y in range(len(models))]  # first mode on top
        vals = [pct.get(m, 0) for m in models]
        bars = ax.barh(ys, vals, height=h * 0.85, color=MODE_COLORS[mode],
                       label=MODE_LABELS[mode], edgecolor=SURFACE, linewidth=2)
        for b, v, m in zip(bars, vals, models):
            if m in pct:
                ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
                        va="center", fontsize=8, color=INK_2)
    ax.axvline(SMALL_MODEL_BAR, color=INK_3, lw=1, ls="--")
    ax.text(SMALL_MODEL_BAR, len(models) - 0.45, " 35% small-model bar", color=INK_3, fontsize=8)
    ax.set_yticks(range(len(models)), models, color=INK)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Matura score (%)", color=INK_2, fontsize=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Baseline matura score per model", loc="left", fontsize=12, pad=12)
    ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK_2)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)


def plot_by_category(summaries, mode: str, out: Path):
    rows = sorted([s for s in summaries if s["mode"] == mode], key=lambda s: -s["pct"])
    if not rows:
        return False
    cats = [c for c in CATEGORY_ORDER if any(c in s["by_category"] for s in rows)]
    cats += sorted({c for s in rows for c in s["by_category"]} - set(cats))
    grid = [[(s["by_category"].get(c) or {}).get("pct") for c in cats] for s in rows]

    fig, ax = plt.subplots(figsize=(1.1 * len(cats) + 2.5, 0.5 * len(rows) + 1.8), facecolor=SURFACE)
    style(ax)
    masked = [[v if v is not None else float("nan") for v in r] for r in grid]
    ax.imshow(masked, cmap=BLUES, vmin=0, vmax=100, aspect="auto")
    for i, r in enumerate(grid):
        for j, v in enumerate(r):
            ax.text(j, i, "–" if v is None else f"{v:.0f}", ha="center", va="center", fontsize=9,
                    color=INK_3 if v is None else ("white" if v >= 55 else INK))
    ax.set_xticks(range(len(cats)), [c.replace("_", "\n") for c in cats], fontsize=8)
    ax.set_yticks(range(len(rows)), [s["model"] for s in rows], color=INK)
    ax.set_xticks([x - 0.5 for x in range(1, len(cats))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(rows))], minor=True)
    ax.grid(which="minor", color=SURFACE, lw=2)
    ax.tick_params(which="minor", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title(f"Score by question type (%), {MODE_LABELS.get(mode, mode).lower()}",
                 loc="left", fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return True


def plot_size(summaries, mode: str, out: Path):
    rows = [s for s in summaries if s["mode"] == mode and s.get("disk_gb")]
    if not rows:
        return False
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    style(ax)
    xmax = max(max(s["disk_gb"] for s in rows) * 1.15, SIZE_LIMIT_GB * 1.3)
    ax.axvspan(SIZE_LIMIT_GB, xmax, color=GRID, alpha=0.5, lw=0)
    ax.text(SIZE_LIMIT_GB + 0.2, 97, f"over the {SIZE_LIMIT_GB:g} GB limit", color=INK_3, fontsize=8, va="top")
    ax.axhline(SMALL_MODEL_BAR, color=INK_3, lw=1, ls="--")
    ax.text(xmax, SMALL_MODEL_BAR + 1, "35% small-model bar ", color=INK_3, fontsize=8, ha="right")
    ax.scatter([s["disk_gb"] for s in rows], [s["pct"] for s in rows], s=70,
               color=MODE_COLORS.get(mode, "#2a78d6"), edgecolor=SURFACE, linewidth=2, zorder=3)
    for s in rows:
        ax.annotate(f"{s['model']}  {s['pct']:.1f}%", (s["disk_gb"], s["pct"]),
                    xytext=(7, 4), textcoords="offset points", fontsize=8, color=INK_2)
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Shipped model size on disk (GB)", color=INK_2, fontsize=9)
    ax.set_ylabel("Matura score (%)", color=INK_2, fontsize=9)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title(f"Size vs score, {MODE_LABELS.get(mode, mode).lower()}", loc="left",
                 fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return True


def write_table(summaries, out_dir: Path):
    cats = sorted({c for s in summaries for c in s["by_category"]},
                  key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99)
    head = ["model", "mode", "pct", "pct_text_only", "disk_gb", "quantization", "scored", "n",
            "routing_accuracy", "latency_p50_s"] + cats
    rows = []
    for s in sorted(summaries, key=lambda s: (-s["pct"], s["mode"])):
        rows.append([s.get(k) for k in head[:10]] +
                    [(s["by_category"].get(c) or {}).get("pct") for c in cats])
    with open(out_dir / "baselines.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)
    return head, rows


def write_html(head, rows, images, out_dir: Path):
    cell = lambda v: "–" if v is None else html.escape(str(v))  # noqa: E731
    table = "<table><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in head) + "</tr>"
    table += "".join("<tr>" + "".join(f"<td>{cell(v)}</td>" for v in r) + "</tr>" for r in rows)
    table += "</table>"
    imgs = "".join(f'<img src="{i}" alt="{i}">' for i in images)
    (out_dir / "index.html").write_text(f"""<!doctype html><meta charset="utf-8">
<title>Matura baselines</title>
<style>
body{{font:14px system-ui,sans-serif;background:{SURFACE};color:{INK};max-width:1100px;margin:24px auto;padding:0 16px}}
img{{max-width:100%;display:block;margin:16px 0}}
table{{border-collapse:collapse;font-size:12px;display:block;overflow-x:auto}}
th,td{{padding:4px 8px;border-bottom:1px solid {GRID};text-align:right;white-space:nowrap}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}
</style>
<h1>Matura baselines</h1>{imgs}<h2>All runs</h2>{table}
""", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", default=str(ROOT / "runs/baselines"))
    p.add_argument("--out", default=str(ROOT / "runs/report"))
    p.add_argument("--mode", default="raw", help="mode for the heatmap and size charts")
    args = p.parse_args()

    summaries = load(Path(args.runs))
    if not summaries:
        raise SystemExit(f"no summary.json files under {args.runs}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    images = ["overall.png"]
    plot_overall(summaries, out / "overall.png")
    if plot_by_category(summaries, args.mode, out / "by_category.png"):
        images.append("by_category.png")
    if plot_size(summaries, args.mode, out / "size_vs_score.png"):
        images.append("size_vs_score.png")
    head, rows = write_table(summaries, out)
    write_html(head, rows, images, out)
    print(f"{len(summaries)} runs -> {out}/index.html")


if __name__ == "__main__":
    main()
