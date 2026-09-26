import json
import sys
from pathlib import Path

from matura_router.backends import EchoBackend
from matura_router.categories import Category
from matura_router.rag import BM25Retriever, Passage, format_knowledge
from matura_router.router import Router

ROOT = Path(__file__).resolve().parent.parent
PASSAGES = [
    Passage("1", "Unia lubelska", "Unia lubelska zawarta w 1569 roku połączyła Koronę i Wielkie Księstwo Litewskie."),
    Passage("2", "Bitwa pod Grunwaldem", "W 1410 roku wojska polsko-litewskie pokonały Zakon krzyżacki."),
    Passage("3", "Konstytucja 3 maja", "Ustawa Rządowa uchwalona przez Sejm Czteroletni w 1791 roku."),
]


def test_bm25_finds_the_right_passage_with_inflected_words():
    r = BM25Retriever(PASSAGES)
    assert r.search("Co postanowiono na mocy unii lubelskiej?", k=1)[0].title == "Unia lubelska"
    assert r.search("Kto zwyciężył Krzyżaków w 1410?", k=1)[0].title == "Bitwa pod Grunwaldem"
    assert r.search("zupełnie nieznane słowa xyz", k=2) == []
    assert "[Unia lubelska]" in format_knowledge(r.search("unia lubelska", k=1))
    assert len(format_knowledge(PASSAGES, max_chars=100)) < 260
    # Short inflected words match too ("unii" / "Unia"), not only 6-letter prefixes.
    assert r.search("unii", k=1)[0].title == "Unia lubelska"


def test_router_adds_knowledge_only_in_rag_modes(tmp_path):
    kb = tmp_path / "kb.jsonl"
    kb.write_text("".join(json.dumps({"id": p.id, "title": p.title, "text": p.text}, ensure_ascii=False) + "\n"
                          for p in PASSAGES))
    cfg = tmp_path / "configs" / "routes.yaml"
    cfg.parent.mkdir()
    cfg.write_text((ROOT / "configs/routes.yaml").read_text().replace("data/kb/passages.jsonl", str(kb)))
    backend = EchoBackend()
    router = Router.from_config(cfg, backend=backend)
    q = "Wyjaśnij, jakie były skutki unii lubelskiej."
    for mode, has in [("raw", False), ("routed", False), ("rag", True), ("adapters", True)]:
        res = router.answer(q, category=Category.SHORT_OPEN, mode=mode)
        user = backend.calls[-1][1][-1]["content"]
        assert ("Unia lubelska zawarta" in user) is has, mode
        assert bool(res.retrieved) is has
    assert user.rstrip().endswith(q)  # the question stays last


def test_router_without_kb_file_runs_without_rag(tmp_path):
    cfg = tmp_path / "configs" / "routes.yaml"
    cfg.parent.mkdir()
    cfg.write_text((ROOT / "configs/routes.yaml").read_text().replace("data/kb/passages.jsonl", "nope.jsonl"))
    router = Router.from_config(cfg, backend=EchoBackend())
    assert router.retriever is None
    assert router.answer("Podaj rok unii lubelskiej.", mode="rag").retrieved == ()


def test_kb_chunking_drops_references():
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_kb import chunk
    text = ("Wstęp\n" + "Zdanie o historii Polski i jej królach. " * 30 + "\nPrzypisy\n" + "ref " * 50)
    parts = chunk(text, size=300)
    assert parts and all(len(p) <= 600 for p in parts)
    assert not any("ref ref" in p for p in parts)


def test_sqlite_fts_retriever_matches_interface(tmp_path):
    import sqlite3
    from matura_router.rag import load_retriever
    db = tmp_path / "kb.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE VIRTUAL TABLE passages USING fts5(title, text)")
    con.executemany("INSERT INTO passages VALUES (?, ?)", [(p.title, p.text) for p in PASSAGES])
    con.commit()
    con.close()
    r = load_retriever(db)
    hits = r.search("Co postanowiono na mocy unii lubelskiej?", k=1)
    assert hits[0].title == "Unia lubelska" and hits[0].score > 0
    assert len(r.passages) == 3
