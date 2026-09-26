import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("small_infer", ROOT / "scripts/small_track/infer.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("key", sorted(module.FORBIDDEN))
def test_grading_fields_cannot_enter_candidate_prompt(key):
    with pytest.raises(ValueError, match="grading fields"):
        module.messages({"question": "Pytanie", key: "secret key"})


def test_candidate_sources_preserved_without_metadata_or_keys():
    row = {"id": "x", "context": "Źródło", "question": "Pytanie", "points": 2}
    prompt = module.messages(row)
    assert prompt[1]["content"] == "Źródło\n\nPytanie"
    assert "350" not in prompt[0]["content"]


def test_empty_question_rejected():
    with pytest.raises(ValueError, match="Empty"):
        module.messages({"question": " "})


def test_route_prompt_changes_only_system_message():
    row = {"question": "Pytanie", "context": "Źródło"}
    base = module.messages(row)
    routed = module.messages(row, system_prompt="Podaj jedną odpowiedź.")
    assert base[1] == routed[1]
    assert routed[0]['content'] == "Podaj jedną odpowiedź."

def test_offline_disables_proxy_and_redirect(monkeypatch):
    from types import SimpleNamespace
    import urllib.request
    captured=[]
    class FakeOpener:
        def open(self,*args,**kwargs):raise OSError('test')
    def build(*handlers):captured.extend(handlers);return FakeOpener()
    monkeypatch.setattr(urllib.request,'build_opener',build)
    args=SimpleNamespace(model='owned',mode='bare',images=False,image_root='.',offline=True,base_url='http://127.0.0.1:8080/v1',essay_tokens=10,max_tokens=10,timeout=1)
    module.answer({'id':'x','question':'Q','points':1},args,'hash')
    assert captured[0].proxies=={}
    with pytest.raises(ValueError):captured[1].redirect_request(None,None,302,'redirect',{},'https://external.invalid')
