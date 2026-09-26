"""Answers an official exam package and writes the answers.json the organisers grade.

Format (organisers' guide, matura-json-guide, 2026-09-26): the package has exam.json,
images/*.png and answers-template.json. exam.json holds `exam_id`, `instructions` and
`items`, each with `id` (string, e.g. "2.1"), `max_points`, `question`, `source_text`,
`images` ([{"path": "images/Z01.png", "source_page", "sha256"}], relative to exam.json)
and `answer_format`. The output is

    {"exam_id": "<copied>", "answers": [{"id": "1", "answer": "..."}, ...]}

with every item id exactly once, every answer a string ("" if unanswerable), Polish,
UTF-8, at most 1 MiB. Grading is done later by the organisers with LLMs against the
CKE key.

    bash scripts/serve_exam.sh bielik-11b &          # model + adapters + RAG, offline
    python scripts/run_exam.py path/to/package -o answers.json
    python scripts/run_exam.py path/to/package --mode raw -o answers-base.json   # bare model

The router is used in-process (no need for the :8080 server). Images go to the model
only when configs/routes.yaml has `backend.vision: true`; a text model gets the same
placeholder our eval set uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.router import DEFAULT_CONFIG, Router  # noqa: E402

MAX_BYTES = 1 << 20
MAX_ANSWER_CHARS = 100_000


def item_question(item: dict) -> str:
    """The task text plus the answer-sheet lines, unless the question already has them."""
    q = (item.get("question") or "").strip()
    fmt = (item.get("answer_format") or "").strip()
    if fmt and fmt not in q:
        q = f"{q}\n{fmt}"
    return q


def item_images(item: dict, base: Path) -> tuple[Path, ...]:
    out = []
    for im in item.get("images") or []:
        p = base / im["path"]
        if not p.exists():
            print(f"[{item['id']}] missing image {p}", file=sys.stderr)
            continue
        if im.get("sha256") and hashlib.sha256(p.read_bytes()).hexdigest() != im["sha256"]:
            print(f"[{item['id']}] sha256 mismatch for {p}", file=sys.stderr)
        out.append(p)
    return tuple(out)


def build_answers(exam: dict, answers: dict[str, str], template: dict | None = None) -> dict:
    """answers.json in the template's order, every id once, every answer a string."""
    ids = [str(a["id"]) for a in template["answers"]] if template else [str(i["id"]) for i in exam["items"]]
    return {"exam_id": exam["exam_id"],
            "answers": [{"id": i, "answer": str(answers.get(i) or "")[:MAX_ANSWER_CHARS]} for i in ids]}


def validate(out: dict, exam: dict) -> list[str]:
    problems = []
    ids = [a["id"] for a in out["answers"]]
    want = [str(i["id"]) for i in exam["items"]]
    if sorted(ids) != sorted(want) or len(set(ids)) != len(ids):
        problems.append("item ids differ from exam.json")
    if any(not isinstance(a["answer"], str) for a in out["answers"]):
        problems.append("non-string answer")
    size = len(json.dumps(out, ensure_ascii=False).encode())
    if size > MAX_BYTES:
        problems.append(f"file is {size} bytes, over 1 MiB")
    return problems


def bare_model_ok(router) -> bool:
    """--mode raw is the untouched-base submission: refuse a served model that is our own merge."""
    url = getattr(router.backend, "base_url", None)
    if not url:
        return True
    try:
        import urllib.request
        with urllib.request.urlopen(url + "/models", timeout=10) as r:
            roots = [str(m.get("root") or m.get("id") or "") for m in json.load(r).get("data", [])]
    except Exception as e:  # noqa: BLE001 - can't check; say so and go on
        print(f"WARNING: could not check which model is served ({e})", file=sys.stderr)
        return True
    ours = [x for x in roots if any(t in x.lower() for t in ("dapt", "merged"))]
    if ours:
        print(f"--mode raw must run on the untouched base model, but the server has {ours}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package", help="dir with exam.json (or the exam.json itself)")
    ap.add_argument("-o", "--out", default="answers.json")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--mode", default="adapters", choices=["raw", "routed", "rag", "adapters"])
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", help="key in configs/models.yaml: its `vision` flag overrides routes.yaml "
                                    "(the model serve_exam.sh started)")
    ap.add_argument("--log", help="per-item log (jsonl); default <out>.log.jsonl")
    args = ap.parse_args()

    exam_path = Path(args.package)
    exam_path = exam_path / "exam.json" if exam_path.is_dir() else exam_path
    base = exam_path.parent
    exam = json.loads(exam_path.read_text(encoding="utf-8"))
    tpl_path = base / "answers-template.json"
    template = json.loads(tpl_path.read_text(encoding="utf-8")) if tpl_path.exists() else None
    router = Router.from_config(args.config)
    if args.mode == "raw" and not bare_model_ok(router):
        return 1
    if args.model:
        import yaml
        spec = yaml.safe_load((Path(__file__).resolve().parent.parent / "configs/models.yaml")
                              .read_text())["models"][args.model]
        router.apply_model(spec)
    print(f"vision: {router.vision}", file=sys.stderr)

    def one(item):
        t0 = time.perf_counter()
        try:
            res = router.answer(item_question(item), item.get("source_text") or "",
                                mode=args.mode, images=item_images(item, base))
            return str(item["id"]), res.answer, {**res.to_dict(), "id": str(item["id"])}
        except Exception as e:  # noqa: BLE001 - a blank answer beats a missing file
            return str(item["id"]), "", {"id": str(item["id"]), "error": str(e),
                                         "latency_s": round(time.perf_counter() - t0, 3)}

    with ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(one, exam["items"]))

    out = build_answers(exam, {i: a for i, a, _ in results}, template)
    problems = validate(out, exam)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log = Path(args.log or f"{args.out}.log.jsonl")
    log.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for _, _, r in results), encoding="utf-8")
    blank = sum(1 for a in out["answers"] if not a["answer"])
    print(f"{len(out['answers'])} answers ({blank} blank) -> {args.out}; log {log}")
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
