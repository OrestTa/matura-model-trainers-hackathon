import json
import subprocess
import sys
from pathlib import Path

import pytest

from matura_router.backends import EchoBackend
from matura_router.categories import Category
from matura_router.evaluate import evaluate, load_rows
from matura_router.router import Router
from matura_router.scoring import score_closed, score_keywords, score_row

ROOT = Path(__file__).resolve().parent.parent


def test_closed_scoring():
    assert score_closed(Category.CLOSED_CHOICE, "B", "B") == 1
    assert score_closed(Category.CLOSED_CHOICE, "A, C", "C, A") == 1
    assert score_closed(Category.CLOSED_CHOICE, "A", "A, C") == 0
    assert score_closed(Category.TRUE_FALSE, "1. P\n2. P", "P, F") == 0.5
    assert score_closed(Category.TRUE_FALSE, "prawda, fałsz", "P, F") == 1
    assert score_closed(Category.MATCHING, "1 – A\n2 – C", "1-A, 2-B") == 0.5
    assert score_closed(Category.CHRONOLOGY, "B, D, A, C", "B, D, A, C") == 1
    assert score_closed(Category.CHRONOLOGY, "B, A, D, C", "B, D, A, C") == 0


def test_keyword_and_row_scoring():
    assert score_keywords("Konstytucja 3 maja, 1791", [["konstytucj"], ["1791"], ["1795"]]) == 2 / 3
    row = {"question": "q", "category": "essay", "gold": "wzór", "points": 4}
    assert score_row(row, "cokolwiek") is None
    assert score_row(row, "x", judge=lambda p: "3 pkt") == 3
    assert score_row(row, "x", judge=lambda p: "9") == 0
    assert score_row(row, "x", judge=lambda p: "Punkty: 2") == 2
    assert score_row(row, "x", judge=lambda p: "Sejm w 1791 roku uchwalił...") == 0


def test_router_modes():
    backend = EchoBackend()
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=backend)
    q = "Napisz wypracowanie o unii lubelskiej."
    assert router.answer(q, mode="raw").adapter is None
    assert "wypracowanie:" not in backend.calls[-1][1][0]["content"]  # generic prompt
    assert router.answer(q, mode="routed").adapter is None
    assert router.answer(q, mode="adapters").adapter == "essay"


def test_evaluate_summary():
    class Perfect(EchoBackend):
        def chat(self, messages, adapter, params):
            return {"Unia w Krewie": "A"}.get(next(
                (k for k in ["Unia w Krewie"] if k in messages[-1]["content"]), ""), "nie wiem")
    rows = load_rows(ROOT / "examples/sample_questions.jsonl")
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=Perfect())
    results, s = evaluate(router, rows, mode="routed", concurrency=4)
    assert s["n"] == len(rows) and s["scored"] == len(rows)
    assert s["by_category"]["closed_choice"]["pct"] == 100.0
    assert s["routing_accuracy"] == 100.0
    assert 0 < s["pct"] < 100


def test_plot_report(tmp_path):
    pytest.importorskip("matplotlib")
    for model, pct, gb in [("a", 60.0, 6.5), ("b", 30.0, 2.0)]:
        d = tmp_path / "runs" / model / "raw"
        d.mkdir(parents=True)
        (d / "summary.json").write_text(json.dumps({
            "model": model, "mode": "raw", "pct": pct, "disk_gb": gb, "n": 2, "scored": 2,
            "by_category": {"essay": {"pct": pct}, "true_false": {"pct": None}}}))
    subprocess.run([sys.executable, str(ROOT / "scripts/plot_baselines.py"),
                    "--runs", str(tmp_path / "runs"), "--out", str(tmp_path / "report")], check=True)
    for f in ["overall.png", "by_category.png", "size_vs_score.png", "index.html", "baselines.csv"]:
        assert (tmp_path / "report" / f).stat().st_size > 0


ROZ = ("Rozstrzygnij, czy źródło dotyczy epoki paleolitu czy neolitu. Odpowiedź uzasadnij.\n"
       "Rozstrzygnięcie: …\nUzasadnienie: …")


def test_answer_template_found_and_only_outside_raw():
    from matura_router.categories import Category
    from matura_router.prompts import answer_template, build_messages
    assert answer_template(ROZ) == ["Rozstrzygnięcie: …", "Uzasadnienie: …"]
    assert answer_template("Podaj datę bitwy pod Grunwaldem.") == []
    assert "Rozstrzygnięcie: …" in build_messages(Category.SOURCE_ANALYSIS, ROZ)[0]["content"]
    raw = build_messages(Category.GENERAL, ROZ, fill_template=False)[0]["content"]
    assert "szablon" not in raw


def test_verdict_gate():
    from matura_router.prompts import verdict_matches
    assert verdict_matches("**Rozstrzygnięcie:** neolit\nUzasadnienie: osady", "neolitu")
    assert not verdict_matches("Rozstrzygnięcie: paleolitu", "neolitu")
    assert verdict_matches("Rozstrzygnięcie: Nie, nie jest zgodne", "Nie")
    assert not verdict_matches("Rozstrzygnięcie: Tak", "nie")
    assert not verdict_matches("Rozstrzygnięcie: przeciwników", "przed")
    row = {"category": "source_analysis", "points": 1, "question": ROZ, "gold": "Rozstrzygnięcie: neolitu",
           "decision": "neolitu"}
    assert score_row(row, "Rozstrzygnięcie: paleolitu", judge=lambda p: "1") == 0.0
    assert score_row(row, "Rozstrzygnięcie: neolitu", judge=lambda p: "1") == 1.0
