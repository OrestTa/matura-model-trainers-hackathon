import hashlib
import json
import subprocess
import sys
from pathlib import Path

from matura_router.backends import EchoBackend
from matura_router.categories import Category
from matura_router.router import Router

ROOT = Path(__file__).resolve().parent.parent
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def make_package(tmp: Path) -> Path:
    (tmp / "images").mkdir(parents=True)
    (tmp / "images/Z01.png").write_bytes(PNG)
    exam = {"exam_id": "history-2023-mock-v1", "title": "Historia", "language": "pl",
            "input_format": "separate-text-and-images-v1", "max_points": 3, "instructions": "",
            "items": [
                {"id": "1", "group": 1, "max_points": 1,
                 "question": "Rozstrzygnij, czy rekonstrukcja dotyczy paleolitu czy neolitu. Odpowiedź uzasadnij.",
                 "source_text": "Rekonstrukcja osady.", "answer_format": "Rozstrzygnięcie: …\nUzasadnienie: …",
                 "images": [{"path": "images/Z01.png", "source_page": 4,
                             "sha256": hashlib.sha256(PNG).hexdigest()}]},
                {"id": "2.1", "group": 2, "max_points": 1, "question": "Podaj rok unii lubelskiej.",
                 "source_text": "", "images": [], "answer_format": ""},
            ]}
    (tmp / "exam.json").write_text(json.dumps(exam, ensure_ascii=False))
    (tmp / "answers-template.json").write_text(json.dumps(
        {"exam_id": exam["exam_id"], "answers": [{"id": "1", "answer": ""}, {"id": "2.1", "answer": ""}]}))
    return tmp


def test_run_exam_writes_valid_answers(tmp_path):
    pkg = make_package(tmp_path / "pkg")
    cfg = tmp_path / "configs" / "routes.yaml"
    cfg.parent.mkdir()
    cfg.write_text((ROOT / "configs/routes.yaml").read_text().replace("kind: openai", "kind: echo"))
    out = tmp_path / "answers.json"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/run_exam.py"), str(pkg), "-o", str(out),
                        "--config", str(cfg)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    ans = json.loads(out.read_text())
    assert ans["exam_id"] == "history-2023-mock-v1"
    assert [a["id"] for a in ans["answers"]] == ["1", "2.1"]
    assert all(isinstance(a["answer"], str) and a["answer"] for a in ans["answers"])


def test_images_go_to_vision_models_only(tmp_path):
    pkg = make_package(tmp_path)
    backend = EchoBackend()
    router = Router.from_config(backend=backend)
    router.answer("Opisz ilustrację.", category=Category.SHORT_OPEN, mode="routed", images=(pkg / "images/Z01.png",))
    user = backend.calls[-1][1][-1]["content"]
    assert isinstance(user, str) and "[ilustracja – niedostępna w wersji tekstowej]" in user
    router.vision = True
    router.answer("Opisz ilustrację.", category=Category.SHORT_OPEN, mode="routed", images=(pkg / "images/Z01.png",))
    parts = backend.calls[-1][1][-1]["content"]
    assert parts[0]["type"] == "text" and parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
