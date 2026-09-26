import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import job_status  # noqa: E402


def test_upsert_keeps_one_row_per_job(tmp_path):
    f = tmp_path / "STATUS.md"
    job_status.upsert(f, "baselines-1", "running", "Modal", "router", "6 models")
    job_status.upsert(f, "train-1", "queued", None, None, None)
    job_status.upsert(f, "baselines-1", "done", None, None, "report in results/ | ok")
    rows = {r["Job"]: r for r in job_status.read_rows(f)}
    assert set(rows) == {"baselines-1", "train-1"}
    assert rows["baselines-1"]["State"] == "done"
    assert rows["baselines-1"]["Where"] == "Modal"  # kept from the first update
    assert rows["baselines-1"]["Notes"] == "report in results/ / ok"  # pipes escaped


def test_cli_show(tmp_path):
    f = tmp_path / "STATUS.md"
    run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts/job_status.py"), *a,  # noqa: E731
                                     "--file", str(f)], check=True, capture_output=True, text=True)
    run("set", "gen-data", "failed", "--note", "teacher OOM")
    assert "failed    gen-data" in run("show").stdout
