import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)

sys.path.insert(0, str(HARNESS))
import history_pack  # noqa: E402


def make_pack(tmp: Path, exam_id: str = "history-2024-05") -> Path:
    (tmp / "images").mkdir(parents=True)
    (tmp / "images" / "Z01.png").write_bytes(PNG)
    exam = {
        "exam_id": exam_id,
        "title": "Historia",
        "source_exam_id": "MHIP-R0-100-A-2405",
        "source_url": "https://cke.gov.pl/example.pdf",
        "input_format": "separate-text-and-images-v1",
        "language": "pl",
        "max_points": 16,
        "instructions": "",
        "items": [
            {
                "id": "1",
                "group": 1,
                "max_points": 1,
                "question": "Zaznacz właściwą odpowiedź.",
                "source_text": "Krótki tekst źródłowy.",
                "images": [
                    {
                        "path": "images/Z01.png",
                        "source_page": 1,
                        "sha256": hashlib.sha256(PNG).hexdigest(),
                    }
                ],
                "answer_format": "A",
            },
            {
                "id": "25",
                "group": 25,
                "max_points": 15,
                "question": "Wybierz jeden z trzech tematów i napisz wypracowanie. Minimum 300 wyrazów.",
                "source_text": "",
                "images": [],
                "answer_format": "1 + wypracowanie",
            },
        ],
    }
    (tmp / "exam.json").write_text(json.dumps(exam, ensure_ascii=False), encoding="utf-8")
    (tmp / "answers-template.json").write_text(
        json.dumps(
            {"exam_id": exam_id, "answers": [{"id": "1", "answer": ""}, {"id": "25", "answer": ""}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp


def test_history_pack_helpers_accept_pack_dir_and_alias(tmp_path):
    pack = make_pack(tmp_path / "pack")
    assert history_pack.resolve_pack_dir(pack, None) == pack.resolve()
    assert history_pack.resolve_pack_dir(None, pack) == pack.resolve()

    with pytest.raises(SystemExit, match="pass only one of --pack-dir / --exam-dir"):
        history_pack.resolve_pack_dir(pack, pack)
    with pytest.raises(SystemExit, match="does not match pack exam_id"):
        history_pack.load_pack(pack, "history-2025-05")

    exam, template = history_pack.load_pack(pack, "history-2024-05")
    assert exam["exam_id"] == "history-2024-05"
    assert template["answers"][0]["id"] == "1"
    assert history_pack.categorize(exam["items"][0]) == "image_closed"
    assert history_pack.categorize(exam["items"][1]) == "essay"


@pytest.mark.parametrize(
    "script_name",
    ["run_official_mock.py", "run_official_mock_vllm.py"],
)
def test_pack_runners_support_pack_dir_dry_run(tmp_path, script_name):
    pack = make_pack(tmp_path / "pack")
    out = tmp_path / f"{script_name}.answers.json"
    cmd = [
        sys.executable,
        str(ROOT / "harness" / script_name),
        "--pack-dir",
        str(pack),
        "--exam-id",
        "history-2024-05",
        "--dry-run",
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    answers = json.loads(out.read_text(encoding="utf-8"))
    summary = json.loads(out.with_suffix(".summary.json").read_text(encoding="utf-8"))
    assert answers["exam_id"] == "history-2024-05"
    assert [a["id"] for a in answers["answers"]] == ["1", "25"]
    assert summary["dry_run"] is True
    assert summary["pack_dir"] == str(pack.resolve())
    assert summary["gauge_note"] == "Only history-2023-mock-v1 submissions count as the official gauge."
    assert summary["images"]["images_present"] == 1
