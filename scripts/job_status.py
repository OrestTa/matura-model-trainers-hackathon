"""Keeps docs/STATUS.md, the shared table of running and finished jobs, up to date.

Every bot and person starting, finishing or failing a job updates its row, so the
others (including the Grok bot) can see what is running without asking.

    python scripts/job_status.py set baselines-0926 running --where "Modal A100x4" \
        --owner "router thread" --note "6 models, raw+routed" --push
    python scripts/job_status.py set baselines-0926 done --note "report: results/..." --push
    python scripts/job_status.py show

States: queued, running, done, failed, cancelled. --push pulls main, commits only
docs/STATUS.md and pushes, retrying if someone else pushed first. Job scripts can
call it at each state change (it never fails the job: errors are printed only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "docs/STATUS.md"
COLUMNS = ["Job", "State", "Where", "Owner", "Updated (UTC)", "Notes"]
STATES = {"queued", "running", "done", "failed", "cancelled"}
HEADER = """# Job status

One row per job, updated on every state change with `scripts/job_status.py`.
Newest update first. Pull before reading; results and learnings go in
[FINDINGS.md](FINDINGS.md).

"""


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == len(COLUMNS) and cells[0] not in ("Job", "---"):
            rows.append(dict(zip(COLUMNS, cells)))
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: r["Updated (UTC)"], reverse=True)
    esc = lambda s: str(s).replace("|", "/").replace("\n", " ")  # noqa: E731
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(esc(r.get(c, "")) for c in COLUMNS) + " |" for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")


def upsert(path: Path, job: str, state: str, where: str | None, owner: str | None,
           note: str | None) -> dict:
    rows = read_rows(path)
    row = next((r for r in rows if r["Job"] == job), None)
    if row is None:
        row = {c: "" for c in COLUMNS}
        row["Job"] = job
        rows.append(row)
    row["State"] = state
    row["Updated (UTC)"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    for col, val in (("Where", where), ("Owner", owner), ("Notes", note)):
        if val is not None:
            row[col] = val
    write_rows(path, rows)
    return row


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def push(job: str, state: str, apply) -> None:
    """Pull, re-apply the change on top of main, commit STATUS.md alone, push. Retries races."""
    rel = str(STATUS.relative_to(ROOT))
    for _ in range(4):
        # Drop our local copy, take main's, and re-apply the one-row change on top.
        if git("ls-files", "--error-unmatch", rel).returncode == 0:
            git("checkout", "--", rel)
        else:
            STATUS.unlink(missing_ok=True)
        git("pull", "--quiet", "--rebase", "--autostash", "origin", "main")
        apply()
        git("add", rel)
        if git("diff", "--cached", "--quiet").returncode == 0:
            return
        git("commit", "--quiet", "-m", f"Status: {job} {state}", "--", rel)
        if git("push", "--quiet", "origin", "HEAD:main").returncode == 0:
            print(f"pushed status: {job} {state}")
            return
        git("reset", "--quiet", "--hard", "HEAD~1")
    print("could not push docs/STATUS.md; commit it by hand", file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("job")
    s.add_argument("state", choices=sorted(STATES))
    s.add_argument("--where")
    s.add_argument("--owner")
    s.add_argument("--note")
    s.add_argument("--push", action="store_true")
    s.add_argument("--file", default=str(STATUS))
    sh = sub.add_parser("show")
    sh.add_argument("--file", default=str(STATUS))
    args = p.parse_args()

    path = Path(args.file)
    if args.cmd == "show":
        for r in read_rows(path):
            print(f"{r['Updated (UTC)']}  {r['State']:<9} {r['Job']}  ({r['Where']}) {r['Notes']}")
        return
    apply = lambda: upsert(path, args.job, args.state, args.where, args.owner, args.note)  # noqa: E731
    try:
        if args.push:
            push(args.job, args.state, apply)
        else:
            apply()
    except Exception as e:  # noqa: BLE001 - status reporting must never break a job
        print(f"job_status: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
