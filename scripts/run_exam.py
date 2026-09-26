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
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.router import DEFAULT_CONFIG, Router  # noqa: E402

MAX_BYTES = 1 << 20
MAX_ANSWER_CHARS = 100_000


def answer_format_text(fmt: str) -> str:
    """The item's answer_format as the model sees it. The organisers' closed formats are syntax
    examples with values ("1: P\n2: F\n3: P", "A: 1\nB: 1", "A"): the values are blanked so the model
    can't copy them, and the "key: …" lines tell the router the keys (prompts.keyed_format)."""
    fmt = (fmt or "").strip()
    lines = fmt.splitlines()
    keyed = [re.match(r"^\s*(\S{1,2})\s*:\s*\S{1,3}\s*$", ln) for ln in lines]
    if len(lines) >= 2 and all(keyed):
        return "Format odpowiedzi (tylko składnia, nie rozwiązanie):\n" + "\n".join(f"{m.group(1)}: …" for m in keyed)
    if re.fullmatch(r"[A-H](, ?[A-H])*", fmt):
        return "Format odpowiedzi: tylko litera (litery) wybranej odpowiedzi."
    return fmt


def item_question(item: dict) -> str:
    """The task text plus the answer-sheet lines, unless the question already has them."""
    q = (item.get("question") or "").strip()
    fmt = answer_format_text(item.get("answer_format") or "")
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
    ap.add_argument("--mode", default="adapters", choices=["raw", "routed", "rag", "adapters", "subtype"],
                    help="subtype = the per-subtype setups of configs/subtypes.yaml (closed/open x text/image, essay)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", help="key in configs/models.yaml: its `vision` flag overrides routes.yaml "
                                    "(the model serve_exam.sh started)")
    ap.add_argument("--subtypes", help="per-subtype setups for --mode subtype (default configs/subtypes.yaml)")
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
    if args.subtypes:
        from matura_router.subtypes import load_profiles
        router.profiles = load_profiles(args.subtypes)
    if args.mode == "subtype":
        print("subtypes:", {k: v.name for k, v in router.profiles.items()}, file=sys.stderr)
        from matura_router import ocr
        if any(p.ocr for p in router.profiles.values()) and not ocr.available():
            print("WARNING: a subtype setup uses OCR notes but tesseract isn't installed "
                  "(apt-get install -y tesseract-ocr tesseract-ocr-pol before going offline); "
                  "those items run without them", file=sys.stderr)
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

    # Hard guarantee: a blank answer (thought that never closed, a timeout, a crash) is asked again with
    # thinking off, the whole exam at once after the first pass. Thinking-off scores ~52% vs 0 for "".
    blanks = [it for it, (_, a, _) in zip(exam["items"], results) if not (a or "").strip()]
    if blanks and hasattr(router.backend, "extra_body"):
        print(f"{len(blanks)} blank after pass 1; re-asking with thinking off", file=sys.stderr)
        kw = router.backend.extra_body.get("chat_template_kwargs") or {}
        router.backend.extra_body = {**router.backend.extra_body,
                                     "chat_template_kwargs": {**kw, "enable_thinking": False}}
        with ThreadPoolExecutor(args.concurrency) as pool:
            redo = {i: (a, r) for i, a, r in pool.map(one, blanks)}
        results = [(i, redo[i][0], {**redo[i][1], "retry": "thinking_off", "first": r})
                   if i in redo and (redo[i][0] or "").strip() else (i, a, r) for i, a, r in results]

    out = build_answers(exam, {i: a for i, a, _ in results}, template)
    problems = validate(out, exam)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log = Path(args.log or f"{args.out}.log.jsonl")
    log.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for _, _, r in results), encoding="utf-8")
    blank = sum(1 for a in out["answers"] if not a["answer"])
    print(f"{len(out['answers'])} answers ({blank} blank) -> {args.out}; log {log}")
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    # The file is still written (on stage a partial answer sheet beats none), but a run with more
    # than 10% blank after the re-ask means a dead or crashing server: fail loudly.
    if blank > 0.1 * len(out["answers"]):
        print(f"FAILED: {blank}/{len(out['answers'])} blank after the re-ask (server down?)", file=sys.stderr)
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
