"""Command line entry point: `python -m matura_router <command>`.

  classify  FILE.jsonl            show the category for each question (no model needed)
  run       FILE.jsonl -o OUT     answer every question, write JSONL with routing info
  ask       "question text"       answer one question
  serve                           OpenAI-compatible endpoint in front of the router

Input JSONL rows: {"id": ..., "question": ..., "context": optional source text,
"category": optional gold label used by `classify` to print accuracy}.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from .classifier import Classifier
from .router import DEFAULT_CONFIG, Router


def _rows(path: str):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                row = json.loads(line)
                row.setdefault("id", i)
                yield row


def cmd_classify(args):
    clf = Classifier()
    counts, hits, labelled = collections.Counter(), 0, 0
    for row in _rows(args.file):
        c = clf.classify(row["question"], row.get("context", ""))
        counts[c.category.value] += 1
        gold = row.get("category")
        mark = ""
        if gold:
            labelled += 1
            hits += gold == c.category.value
            mark = " ok" if gold == c.category.value else f" MISS (gold {gold})"
        print(f"{row['id']}\t{c.category.value}\t{c.confidence:.2f}{mark}")
    print("\n" + json.dumps(dict(counts), ensure_ascii=False), file=sys.stderr)
    if labelled:
        print(f"accuracy {hits}/{labelled} = {hits / labelled:.1%}", file=sys.stderr)


def cmd_run(args):
    router = Router.from_config(args.config)
    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    for row in _rows(args.file):
        res = router.answer(row["question"], row.get("context", ""))
        out.write(json.dumps({"id": row["id"], **res.to_dict()}, ensure_ascii=False) + "\n")
        out.flush()
        print(f"{row['id']}: {res.category} via {res.adapter or 'base'} "
              f"({res.latency_s}s)", file=sys.stderr)


def cmd_ask(args):
    res = Router.from_config(args.config).answer(args.question, args.context or "")
    print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))


def cmd_serve(args):
    from .server import serve
    serve(Router.from_config(args.config), args.host, args.port)


def main(argv=None):
    p = argparse.ArgumentParser(prog="matura_router")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("classify"); s.add_argument("file"); s.set_defaults(fn=cmd_classify)
    s = sub.add_parser("run"); s.add_argument("file"); s.add_argument("-o", "--output")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("ask"); s.add_argument("question"); s.add_argument("--context")
    s.set_defaults(fn=cmd_ask)
    s = sub.add_parser("serve"); s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080); s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    if not Path(args.config).exists():
        p.error(f"config not found: {args.config}")
    args.fn(args)


if __name__ == "__main__":
    main()
