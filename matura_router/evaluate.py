"""Runs an eval set through the router and summarises the score per question type."""

from __future__ import annotations

import collections
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from .prompts import verdict_matches
from .router import Router
from .scoring import score_row


def load_rows(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                row = json.loads(line)
                row.setdefault("id", i)
                rows.append(row)
    return rows


def evaluate(router: Router, rows: list[dict], mode: str = "adapters",
             concurrency: int = 16, judge: Optional[Callable[[str], str]] = None,
             use_gold_category: bool = False) -> tuple[list[dict], dict]:
    """Answers every row, scores it, returns (per-row results, summary).

    use_gold_category skips the classifier, to separate routing mistakes from
    model mistakes.
    """
    from .categories import Category

    def one(row):
        forced = Category(row["category"]) if use_gold_category and row.get("category") else None
        try:
            # Vision models get the item's PNGs (fetch_matura.py --images); the context already
            # holds a placeholder per picture for text models (OCR text replaces it with backend.ocr).
            images = tuple(row.get("images") or ()) if (router.vision or router.ocr) else ()
            res = router.answer(row["question"], row.get("context", ""), category=forced, mode=mode,
                                images=images)
            out = {"id": row["id"], **res.to_dict()}
        except Exception as e:  # noqa: BLE001 - one bad row shouldn't kill a baseline run
            out = {"id": row["id"], "answer": "", "raw": "", "category": None,
                   "adapter": None, "error": str(e), "latency_s": 0.0}
        out["gold_category"] = row.get("category")
        out["needs_image"] = bool(row.get("needs_image"))
        out["paper"] = row.get("paper")
        out["points"] = float(row.get("points", 1))
        out["score"] = score_row(row, out["answer"], judge)
        if row.get("decision"):
            out["decision_ok"] = verdict_matches(out["answer"], row["decision"])
        return out

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(one, rows))
    return results, summarise(results, time.perf_counter() - t0)


# The held-out papers (scripts/fetch_matura.py HEADLINE). Every other paper in matura_all.jsonl
# is adapter training data (scripts/build_train_from_papers.py), so its score after training
# is contaminated and must never be the headline.
HEADLINE_PAPERS = {"2023-05", "2024-05", "2025-05", "2026-05"}


def summarise(results: list[dict], wall_s: float = 0.0) -> dict:
    """Headline numbers cover only the held-out papers; trained-on papers are reported apart."""
    trained = [r for r in results if r.get("paper") and r["paper"] not in HEADLINE_PAPERS]
    if trained and len(trained) < len(results):
        held = [r for r in results if r not in trained]
        out = _summarise(held, wall_s)
        out["trained_on_papers"] = {k: v for k, v in _summarise(trained).items()
                                    if k in ("n", "scored", "earned", "max", "pct", "pct_all_rows")}
        out["trained_on_papers"]["note"] = ("training data for the adapters: contaminated after training, "
                                            "not part of the headline")
        return out
    out = _summarise(results, wall_s)
    if trained:
        out["warning"] = "no held-out paper in this set: every paper here is adapter training data"
    return out


def _summarise(results: list[dict], wall_s: float = 0.0) -> dict:
    by_cat = collections.defaultdict(lambda: {"n": 0, "scored": 0, "earned": 0.0, "max": 0.0})
    for r in results:
        cat = r.get("gold_category") or r.get("category") or "unknown"
        b = by_cat[cat]
        b["n"] += 1
        if r["score"] is not None:
            b["scored"] += 1
            b["earned"] += r["score"]
            b["max"] += r["points"]
    for b in by_cat.values():
        b["pct"] = round(100 * b["earned"] / b["max"], 1) if b["max"] else None

    earned = sum(b["earned"] for b in by_cat.values())
    maximum = sum(b["max"] for b in by_cat.values())
    all_max = sum(r["points"] for r in results)
    labelled = [r for r in results if r.get("gold_category") and r.get("category")]
    # Items whose source is a photo/map/chart can't be answered from text alone;
    # the text-only score is the fairer measure of the model itself.
    text = [r for r in results if not r.get("needs_image") and r["score"] is not None]
    text_max = sum(r["points"] for r in text)
    dec = [r for r in results if "decision_ok" in r]
    lat = [r["latency_s"] for r in results if r.get("latency_s")]
    return {
        "n": len(results),
        "scored": sum(b["scored"] for b in by_cat.values()),
        "errors": sum(1 for r in results if r.get("error")),
        "earned": round(earned, 2),
        "max": maximum,
        "pct": round(100 * earned / maximum, 1) if maximum else None,
        "pct_text_only": round(100 * sum(r["score"] for r in text) / text_max, 1) if text_max else None,
        # Earned over the points of ALL rows (unscored count as 0): comparable with an exam score.
        "pct_all_rows": round(100 * earned / all_max, 1) if all_max else None,
        # Judge-free signal on the "Rozstrzygnij" items: share of right verdicts.
        "decision_acc": round(100 * sum(r["decision_ok"] for r in dec) / len(dec), 1) if dec else None,
        "unscored": sum(1 for r in results if r["score"] is None),
        "routing_accuracy": round(100 * sum(r["category"] == r["gold_category"] for r in labelled)
                                  / len(labelled), 1) if labelled else None,
        "latency_p50_s": round(statistics.median(lat), 3) if lat else None,
        "wall_s": round(wall_s, 1),
        "by_category": dict(sorted(by_cat.items())),
    }
