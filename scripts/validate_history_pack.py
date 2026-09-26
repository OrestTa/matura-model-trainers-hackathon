#!/usr/bin/env python3
"""Validate a Tarasiuk Lab history mock-format pack (separate-text-and-images-v1)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(pack: Path) -> list[str]:
    errs: list[str] = []
    exam_p = pack / "exam.json"
    tmpl_p = pack / "answers-template.json"
    if not exam_p.exists():
        return ["missing exam.json"]
    if not tmpl_p.exists():
        return ["missing answers-template.json"]
    exam = json.loads(exam_p.read_text(encoding="utf-8"))
    tmpl = json.loads(tmpl_p.read_text(encoding="utf-8"))
    required = {
        "exam_id", "title", "source_exam_id", "source_url", "input_format",
        "language", "max_points", "instructions", "items",
    }
    if missing := required - set(exam):
        errs.append(f"exam missing keys: {sorted(missing)}")
    if exam.get("input_format") != "separate-text-and-images-v1":
        errs.append(f"input_format={exam.get('input_format')!r}")
    if exam.get("language") != "pl":
        errs.append(f"language={exam.get('language')!r}")
    ids = [it["id"] for it in exam.get("items", [])]
    if len(ids) != len(set(ids)):
        errs.append("duplicate item ids")
    tmpl_ids = [a["id"] for a in tmpl.get("answers", [])]
    if set(tmpl_ids) != set(ids) or len(tmpl_ids) != len(ids):
        errs.append("answers-template ids do not cover exam item ids exactly once")
    if tmpl.get("exam_id") != exam.get("exam_id"):
        errs.append("exam_id mismatch exam vs answers-template")
    pts = sum(int(it["max_points"]) for it in exam.get("items", []))
    if pts != exam.get("max_points"):
        errs.append(f"max_points field {exam.get('max_points')} != sum {pts}")
    for it in exam.get("items", []):
        for k in ("id", "group", "max_points", "question", "source_text", "images", "answer_format"):
            if k not in it:
                errs.append(f"item {it.get('id')} missing {k}")
        for im in it.get("images", []):
            p = pack / im["path"]
            if not p.exists():
                errs.append(f"missing image {im['path']}")
            elif sha256_file(p) != im.get("sha256"):
                errs.append(f"sha256 mismatch {im['path']}")
    return errs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pack_dir", type=Path)
    args = ap.parse_args()
    errs = validate(args.pack_dir)
    if errs:
        print("FAIL")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    exam = json.loads((args.pack_dir / "exam.json").read_text(encoding="utf-8"))
    n_img_files = len(list((args.pack_dir / "images").glob("*.png"))) if (args.pack_dir / "images").exists() else 0
    n_with = sum(1 for it in exam["items"] if it["images"])
    print("OK")
    print(f"exam_id={exam['exam_id']} items={len(exam['items'])} max_points={exam['max_points']} "
          f"png_files={n_img_files} items_with_images={n_with}")


if __name__ == "__main__":
    main()
