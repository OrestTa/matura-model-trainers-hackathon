"""Bind externally authored Astra/human grades to immutable answers and aggregate.

This utility never generates marks. See docs/SMALL_TRACK_GRADING.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "small-track-grading-v1"


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    result = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected an object")
        result.append(row)
    return result


def indexed(values: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in values:
        key = row.get("id")
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label}: each row needs a nonempty string id")
        if key in result:
            raise ValueError(f"{label}: duplicate id {key}")
        result[key] = row
    return result


def integer(value, label: str, minimum: int = 0) -> int:
    # bool, numeric strings and fractional JSON values are not valid marks.
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label}: expected integer >= {minimum}")
    return value


def load_inputs(items_path: Path, answers_path: Path, official_max: int):
    items = indexed(rows(items_path), "items")
    answers = indexed(rows(answers_path), "answers")
    if not items:
        raise ValueError("empty rubric item set")
    papers = {r.get("paper_id", r.get("paper")) for r in items.values()}
    formulas = {r.get("formula") for r in items.values()}
    years = {r.get("year") for r in items.values()}
    if len(papers) != 1 or None in papers or len(formulas) != 1 or None in formulas or len(years) != 1 or None in years:
        raise ValueError("grade one fully identified paper/year/formula at a time")
    for key, row in items.items():
        maximum = integer(row.get("max_points", row.get("points")), key, 1)
        if row.get("points", maximum) != maximum:
            raise ValueError(f"{key}: conflicting point values")
        row["max_points"] = maximum
        if not (row.get("rubric") or row.get("official_solution")):
            raise ValueError(f"{key}: missing official rubric/solution")
    extracted = sum(r["max_points"] for r in items.values())
    if extracted != official_max:
        raise ValueError(f"incomplete or overlapping extraction: {extracted} task points != {official_max} official points")
    unknown = set(answers) - set(items)
    if unknown:
        raise ValueError(f"unknown answer IDs: {sorted(unknown)}")
    for key, row in answers.items():
        if not isinstance(row.get("answer"), str):
            raise ValueError(f"{key}: answer must be a string; use empty string for failure")
    return items, answers, next(iter(papers)), next(iter(formulas)), next(iter(years))


def grade_template(items, answers, run_id: str, items_hash: str) -> list[dict]:
    return [{
        "schema_version": SCHEMA, "run_id": run_id, "id": key,
        "items_sha256": items_hash,
        "answer_sha256": sha256(answers[key]["answer"]) if key in answers else None,
        "answer_present": key in answers, "max_points": item["max_points"],
        "earned_points": None, "status": "pending", "uncertain": False,
        "rationale": "", "rubric_reference": "", "evaluator": None,
    } for key, item in items.items()]


def aggregate(items, answers, grades, run_id: str, items_hash: str, official_max: int) -> dict:
    grade_map = indexed(grades, "grades")
    if set(grade_map) - set(items):
        raise ValueError("grades contain unknown task IDs")
    settled_points = settled_max = provisional_points = graded_max = 0
    pending_ids, uncertain_ids, missing_answers = [], [], []
    evaluators = set()
    for key, item in items.items():
        maximum = item["max_points"]
        if key not in answers:
            missing_answers.append(key)
        grade = grade_map.get(key)
        if grade is None:
            pending_ids.append(key)
            continue
        expected_hash = sha256(answers[key]["answer"]) if key in answers else None
        for field, expected in (("schema_version", SCHEMA), ("run_id", run_id),
                                ("items_sha256", items_hash), ("answer_sha256", expected_hash),
                                ("answer_present", key in answers), ("max_points", maximum)):
            if grade.get(field) != expected or (field == "answer_present" and type(grade.get(field)) is not bool):
                raise ValueError(f"{key}: stale/mismatched {field}")
        integer(grade["max_points"], f"{key} max_points", 1)
        if type(grade.get("uncertain")) is not bool:
            raise ValueError(f"{key}: uncertain must be boolean")
        if grade.get("status") == "pending":
            if grade.get("earned_points") is not None:
                raise ValueError(f"{key}: pending grade must have null earned_points")
            pending_ids.append(key)
            continue
        if grade.get("status") != "graded":
            raise ValueError(f"{key}: status must be pending or graded")
        earned = integer(grade.get("earned_points"), f"{key} earned_points")
        if earned > maximum:
            raise ValueError(f"{key}: earned points exceed maximum")
        if key not in answers and earned != 0:
            raise ValueError(f"{key}: missing answer cannot earn points")
        for field in ("rationale", "rubric_reference"):
            if not isinstance(grade.get(field), str) or not grade[field].strip():
                raise ValueError(f"{key}: graded row requires {field}")
        evaluator = grade.get("evaluator")
        if not isinstance(evaluator, dict) or evaluator.get("kind") not in ("astra", "human"):
            raise ValueError(f"{key}: external Astra or human evaluator required")
        if not isinstance(evaluator.get("identity"), str) or not evaluator["identity"].strip():
            raise ValueError(f"{key}: evaluator identity is required")
        if evaluator["kind"] == "astra" and evaluator["identity"] != "gpt-6-astra":
            raise ValueError(f"{key}: Astra identity must be gpt-6-astra")
        evaluators.add((evaluator["kind"], evaluator["identity"]))
        provisional_points += earned
        graded_max += maximum
        if grade["uncertain"]:
            uncertain_ids.append(key)
        else:
            settled_points += earned
            settled_max += maximum
    complete = not pending_ids and not uncertain_ids
    return {
        "schema_version": SCHEMA, "run_id": run_id,
        "official_max_points": official_max, "task_count": len(items),
        "graded_max_points": graded_max, "settled_max_points": settled_max,
        "grading_coverage": graded_max / official_max,
        "earned_points": settled_points if complete else None,
        "score_percent": 100 * settled_points / official_max if complete else None,
        "provisional_earned_points": provisional_points,
        "confirmed_lower_bound_points": settled_points,
        "possible_upper_bound_points": settled_points + official_max - settled_max,
        "complete": complete,
        "target_35_percent_met": settled_points * 100 >= official_max * 35 if complete else None,
        "pending_ids": pending_ids, "uncertain_ids": uncertain_ids,
        "missing_answer_ids": missing_answers,
        "evaluators": [{"kind": kind, "identity": identity} for kind, identity in sorted(evaluators)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("template", "summarize"))
    parser.add_argument("--items", required=True, type=Path, help="evaluator-only judge.jsonl")
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--grades", type=Path)
    parser.add_argument("--official-max-points", type=int, default=60)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        integer(args.official_max_points, "official maximum", 1)
        items, answers, paper_id, formula, year = load_inputs(args.items, args.answers, args.official_max_points)
        rubric_hash = file_hash(args.items)
        if args.command == "template":
            result = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in grade_template(items, answers, args.run_id, rubric_hash))
        else:
            if args.grades is None:
                parser.error("summarize requires --grades")
            summary = aggregate(items, answers, rows(args.grades), args.run_id, rubric_hash, args.official_max_points)
            summary.update(paper_id=paper_id, formula=formula, year=year,
                           items_sha256=rubric_hash, answers_sha256=file_hash(args.answers),
                           grades_sha256=file_hash(args.grades))
            result = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"grading validation failed: {exc}\n")


if __name__ == "__main__":
    main()
