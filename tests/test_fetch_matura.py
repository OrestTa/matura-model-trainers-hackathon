import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "fetch_matura", Path(__file__).resolve().parent.parent / "scripts/fetch_matura.py")
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)


def test_splits_groups_and_subtasks():
    lines = ["Zadanie 1.", "Źródło 1. Fragment dokumentu", "Tekst źródła.",
             "Zadanie 1.1. (0–1)", "Podaj nazwę dokumentu.",
             "Zadanie 1.2. (0–2)", "Oceń prawdziwość poniższych stwierdzeń. Zaznacz P, jeśli jest prawdziwe, albo F – jeśli jest fałszywe.",
             "Zadanie 2. (0–1)", "Fragment opracowania", "Inny tekst.", "Na podstawie: X, Warszawa 2000.",
             "Wyjaśnij, o co chodzi."]
    items = fm.paper_items(lines)
    assert [(i["task"], i["points"]) for i in items] == [("1.1", 1), ("1.2", 2), ("2", 1)]
    assert items[0]["context"] == ["Źródło 1. Fragment dokumentu", "Tekst źródła."]
    assert items[2]["question"] == ["Wyjaśnij, o co chodzi."]


def test_closed_gold_formats():
    assert fm.closed_gold("true_false", "1. – F\n2. – P") == "F, P"
    assert fm.closed_gold("true_false", "FF") == "F, F"
    assert fm.closed_gold("closed_choice", "C") == "C"
    assert fm.closed_gold("matching", "1 – B\n2 – C") == "1 – B, 2 – C"


def test_keyword_alternatives():
    assert fm.alts("[Ignacy] Łukasiewicz") == ["Łukasiewicz"]
    assert fm.alts("Hanza [hanza niemiecka, związek hanzeatycki]") == ["Hanza", "hanza niemiecka", "związek hanzeatycki"]
    assert fm.alts("abdykacja / zrzeczenie się tronu") == ["abdykacja", "zrzeczenie się tronu"]


def test_image_needed_follows_source_numbers():
    ctx = f"Źródło 1. Mapa\n{fm.IMG}\nŹródło 2. Fragment tekstu\nTekst."
    assert fm.image_needed(ctx, "Podaj nazwę bitwy opisanej w źródle 1.")
    assert not fm.image_needed(ctx, "Podaj nazwisko autora źródła 2.")
