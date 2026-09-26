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
    assert fm.alts("[Ignacy] Łukasiewicz") == ["Łukasiewicz", "Ignacy Łukasiewicz"]
    assert "Jan II Kazimierz" in fm.alts("Jan [II] Kazimierz [Waza]")
    assert fm.alts("Hanza [hanza niemiecka, związek hanzeatycki]") == ["Hanza", "hanza niemiecka", "związek hanzeatycki"]
    assert fm.alts("abdykacja / zrzeczenie się tronu") == ["abdykacja", "zrzeczenie się tronu"]


def test_image_needed_follows_source_numbers():
    ctx = f"Źródło 1. Mapa\n{fm.IMG}\nŹródło 2. Fragment tekstu\nTekst."
    assert fm.image_needed(ctx, "Podaj nazwę bitwy opisanej w źródle 1.")
    assert not fm.image_needed(ctx, "Podaj nazwisko autora źródła 2.")


def test_train_answers_use_the_first_model_answer():
    spec2 = importlib.util.spec_from_file_location(
        "build_train", Path(__file__).resolve().parent.parent / "scripts/build_train_from_papers.py")
    bt = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(bt)
    row = {"category": "source_analysis", "decision": "Nie",
           "question": "Rozstrzygnij, czy … Odpowiedź uzasadnij.\nRozstrzygnięcie: …\nUzasadnienie: …",
           "gold": "Rozstrzygnięcie: Nie\nPrzykładowe uzasadnienia:\n• Pierwszy powód.\n• Drugi powód."}
    assert bt.answer_for(row) == "Rozstrzygnięcie: Nie\nUzasadnienie: Pierwszy powód."
    assert bt.answer_for({"category": "true_false", "gold": "P, F", "question": ""}) == "1. P\n2. F"
    assert bt.clean_open("[Ignacy] Łukasiewicz / Łukasiewicz Ignacy") == "Łukasiewicz"


def test_formula2005_shared_sources_follow_the_intro_line():
    lines = ["CZĘŚĆ II", "Źródło A", "Tekst źródła A.", "Źródło B", "Tekst źródła B.",
             "na podstawie źródeł A i B", "Zadanie 16. (1 pkt)", "Wyjaśnij, o co chodzi.",
             "Zadanie17. (2 pkt)", "Podaj dwa powody.",
             "na podstawie źródła B", "Zadanie 18. (1 pkt)", "Podaj nazwę."]
    items = fm.paper_items05(lines)
    assert [(i["task"], i["points"]) for i in items] == [("16", 1), ("17", 2), ("18", 1)]
    assert items[0]["context"] == ["Źródło A", "Tekst źródła A.", "Źródło B", "Tekst źródła B."]
    assert items[0]["question"] == ["Na podstawie źródeł A i B:", "Wyjaśnij, o co chodzi."]
    assert items[1]["context"] == items[0]["context"]          # covered by the intro above task 16
    assert items[2]["context"] == ["Źródło B", "Tekst źródła B."]


def test_formula2005_text_key_parts_and_points_line():
    key = fm.key_text05(["Zadanie 8.", "A.", "Korzystanie z informacji", "0–1",
                         "Zdający otrzymuje 1 punkt za podanie nazwy wojny.", "Poprawna odpowiedź:",
                         "wojna trzydziestoletnia", "B.", "Korzystanie z informacji", "0–1",
                         "Zdający otrzymuje 1 punkt za podanie nazwy kraju.", "Poprawna odpowiedź:", "Czechy",
                         "Zadanie 9. (0–1)", "Schemat punktowania", "1 p. – za poprawną odpowiedź.",
                         "Poprawna odpowiedź", "B."])
    assert key["8"]["points"] == 2
    assert key["8"]["solution"] == "A. wojna trzydziestoletnia\nB. Czechy"
    assert key["9"]["solution"] == "B."
