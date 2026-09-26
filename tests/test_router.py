import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from matura_router.backends import EchoBackend, GenerationParams
from matura_router.backends.openai_compat import OpenAICompatBackend
from matura_router.categories import Category
from matura_router.classifier import Classifier, LLMClassifier
from matura_router.prompts import postprocess
from matura_router.router import Router
from matura_router.server import make_handler

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [json.loads(l) for l in (ROOT / "examples/sample_questions.jsonl").open()]


@pytest.mark.parametrize("row", SAMPLES, ids=[r["id"] for r in SAMPLES])
def test_rules_classify_samples(row):
    c = Classifier().classify(row["question"], row.get("context", ""))
    assert c.category.value == row["category"]


def test_unclear_question_falls_back_to_general():
    assert Classifier().classify("Kto?").category is Category.GENERAL


def test_llm_fallback_used_only_when_rules_unsure():
    calls = []
    llm = LLMClassifier(lambda p: calls.append(p) or "chronology")
    clf = Classifier(llm=llm)
    assert clf.classify("Kto?").category is Category.CHRONOLOGY
    assert clf.classify(SAMPLES[0]["question"]).category is Category.CLOSED_CHOICE
    assert len(calls) == 1


def test_router_uses_category_adapter():
    backend = EchoBackend()
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=backend)
    res = router.answer(SAMPLES[6]["question"])
    assert res.category == "essay" and res.adapter == "essay"
    assert backend.calls[-1][0] == "essay"


def test_missing_adapter_falls_back_to_base():
    class Partial(EchoBackend):
        def available_adapters(self):
            return {"essay"}
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=Partial())
    assert router.answer(SAMPLES[0]["question"]).adapter is None
    assert router.answer(SAMPLES[6]["question"]).adapter == "essay"


def test_failing_adapter_retries_on_base():
    class Flaky(EchoBackend):
        def chat(self, messages, adapter, params):
            if adapter:
                raise RuntimeError("adapter broke")
            return "B"
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=Flaky())
    res = router.answer(SAMPLES[0]["question"])
    assert res.adapter is None and res.answer == "B"


def test_postprocess_formats():
    assert postprocess(Category.CLOSED_CHOICE, "Poprawna odpowiedź to B.") == "B"
    assert postprocess(Category.TRUE_FALSE, "1. P 2. F") == "1. P\n2. F"
    assert postprocess(Category.CHRONOLOGY, "B, D, A, C") == "B, D, A, C"


def test_openai_request_bodies():
    p = GenerationParams(max_tokens=5)
    vllm = OpenAICompatBackend(base_model="bielik", adapter_mode="model_name")
    assert vllm.request_body([], "essay", p)["model"] == "essay"
    assert vllm.request_body([], None, p)["model"] == "bielik"
    lcpp = OpenAICompatBackend(adapter_mode="llamacpp",
                               llamacpp_lora_ids={"essay": 0, "true_false": 1})
    assert lcpp.request_body([], "true_false", p)["lora"] == [
        {"id": 0, "scale": 0.0}, {"id": 1, "scale": 1.0}]


def test_server_routes_chat_completion():
    router = Router.from_config(ROOT / "configs/routes.yaml", backend=EchoBackend())
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(router))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        body = json.dumps({"model": "router", "messages": [
            {"role": "user", "content": SAMPLES[2]["question"]}]}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_port}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req).read())
        assert out["routing"]["category"] == "chronology"
        assert out["choices"][0]["message"]["content"]
    finally:
        httpd.shutdown()


class _Scripted(EchoBackend):
    def __init__(self, outputs):
        super().__init__()
        self.outputs = list(outputs)

    def chat(self, messages, adapter, params):
        self.calls.append((adapter, params))
        return self.outputs.pop(0)


def test_closed_answers_are_majority_voted():
    backend = _Scripted(["A", "C", "C", "B", "C"])
    router = Router.from_config(backend=backend)
    res = router.answer("Wybierz poprawną odpowiedź. A. x B. y C. z", category=Category.CLOSED_CHOICE,
                        mode="routed")
    assert res.answer == "C" and len(backend.calls) == 5
    assert backend.calls[0][1].temperature == 0.0 and backend.calls[1][1].temperature == 0.7

    tie = _Scripted(["A", "B", "B", "A", "D"])
    assert Router.from_config(backend=tie).answer("x", category=Category.CLOSED_CHOICE,
                                                  mode="routed").answer == "A"
    raw = _Scripted(["A"])
    Router.from_config(backend=raw).answer("x", category=Category.CLOSED_CHOICE, mode="raw")
    assert len(raw.calls) == 1


def test_subtype_profiles_budget_and_thinking():
    from matura_router.backends import EchoBackend
    from matura_router.categories import Category
    from matura_router.router import Router
    from matura_router.subtypes import Profile, subtype_of

    assert subtype_of("closed_choice", False) == "closed_text"
    assert subtype_of("true_false", True) == "closed_image"
    assert subtype_of("source_analysis", True) == "open_image"
    assert subtype_of("short_open", False) == "open_text"
    assert subtype_of("essay", True) == "essay"
    r = Router.from_config(backend=EchoBackend())
    r.apply_model({"think_tokens": 8192, "think_tokens_by_type": {"essay": 16384}})
    essay = r.routes[Category.ESSAY]
    # the profile sets the reasoning budget itself: not added on top of the model entry's
    rt = r.profile_route(essay, Profile(think_tokens=16384), Category.ESSAY)
    assert rt.params.max_tokens == essay.params.max_tokens
    assert rt.params.extra["chat_template_kwargs"]["enable_thinking"] is True
    off = r.profile_route(essay, Profile(think=False), Category.ESSAY)
    assert off.params.max_tokens == essay.params.max_tokens - 16384
    assert off.params.extra["chat_template_kwargs"]["enable_thinking"] is False
    res = r.answer("Napisz wypracowanie na temat unii lubelskiej.", mode="subtype")
    assert res.subtype == "essay" and res.profile


def test_keyed_answer_format():
    """The organisers' closed answer_format ("1: P\\n2: F", "A: 1\\nB: 1", "1: A\\n2: A")."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from run_exam import answer_format_text
    from matura_router.prompts import conform_keyed, keyed_format

    q = "Oceń prawdziwość.\n" + answer_format_text("1: P\n2: F\n3: P")
    assert "1: …" in q and "1: P" not in q     # the syntax example's values are blanked
    keys = keyed_format(q)
    assert keys == ["1", "2", "3"]
    assert conform_keyed("1. Prawda\n2. fałsz\n3) P", keys) == "1: P\n2: F\n3: P"
    assert conform_keyed("P, F, F", keys) == "1: P\n2: F\n3: F"
    assert conform_keyed("1: A\n2: A", ["1", "2"]) == "1: A\n2: A"          # not collapsed to "A"
    assert conform_keyed("A – 1, B – 3", ["A", "B"]) == "A: 1\nB: 3"
    assert conform_keyed("nie wiem", keys) == "nie wiem"
    assert keyed_format("Podaj nazwę.\nTekst po polsku.") == []
    assert answer_format_text("A") == "Format odpowiedzi: tylko litera (litery) wybranej odpowiedzi."
