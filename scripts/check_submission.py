"""Checks an answers.json the way the organisers' upload form does (submission-validation.mjs,
warsawmodeltrainers.dev, read 27.09.2026), offline, before uploading.

    python scripts/check_submission.py answers.json <exam package dir>

The expected ids come from the package's answers-template.json (else exam.json items).
Exit 0 = the form would accept the file; blanks are allowed and listed.
"""
import json
import sys
from pathlib import Path

MAX_BYTES = 1048576


def check(payload, exam_id: str, item_ids: list[str]) -> tuple[list[str], list[str]]:
    errors, blanks = [], []
    if not isinstance(payload, dict) or sorted(payload) != ["answers", "exam_id"]:
        return ["Use only exam_id and answers at the top level."], []
    if payload["exam_id"] != exam_id:
        errors.append(f"Wrong exam_id. Use {exam_id}.")
    if not isinstance(payload["answers"], list):
        return errors + ["answers must be an array."], []
    expected, seen = set(item_ids), set()
    for n, a in enumerate(payload["answers"], 1):
        if not (isinstance(a, dict) and sorted(a) == ["answer", "id"]
                and isinstance(a["id"], str) and isinstance(a["answer"], str)):
            errors.append(f"Entry {n}: use id and answer, both as text.")
            continue
        if a["id"] not in expected:
            errors.append(f"Unknown question ID: {a['id']}.")
        if a["id"] in seen:
            errors.append(f"Duplicate question ID: {a['id']}.")
        seen.add(a["id"])
        if len(a["answer"]) > 100000:
            errors.append(f"Answer {a['id']} exceeds 100,000 characters.")
        if not a["answer"].strip():
            blanks.append(a["id"])
    missing = [i for i in item_ids if i not in seen]
    if missing:
        errors.append(f"Missing question IDs: {', '.join(missing)}.")
    if len(payload["answers"]) != len(expected):
        errors.append(f"Expected {len(expected)} entries; found {len(payload['answers'])}.")
    # the site measures JSON.stringify(payload): compact, UTF-8
    if len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()) > MAX_BYTES:
        errors.append("JSON exceeds 1 MiB.")
    return errors, blanks


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    ans_path, pkg = Path(sys.argv[1]), Path(sys.argv[2])
    pkg = pkg.parent if pkg.is_file() else pkg
    exam = json.loads((pkg / "exam.json").read_text(encoding="utf-8"))
    tpl = pkg / "answers-template.json"
    ids = ([str(a["id"]) for a in json.loads(tpl.read_text(encoding="utf-8"))["answers"]] if tpl.exists()
           else [str(i["id"]) for i in exam["items"]])
    if ans_path.stat().st_size == 0 or ans_path.stat().st_size > MAX_BYTES:
        print("FAIL: file is empty or over 1 MiB")
        return 1
    errors, blanks = check(json.loads(ans_path.read_text(encoding="utf-8")), exam["exam_id"], ids)
    for e in errors:
        print("FAIL:", e)
    if errors:
        return 1
    n = len(ids)
    essay = [i for i in exam["items"] if i.get("max_points", 0) >= 10]
    words = {str(i["id"]): len(a["answer"].split()) for i in essay
             for a in json.load(open(ans_path, encoding="utf-8"))["answers"] if a["id"] == str(i["id"])}
    print(f"OK: {n} entries, {len(blanks)} blank {blanks}; essay words {words}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
