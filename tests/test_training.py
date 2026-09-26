import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gen_synthetic  # noqa: E402


def test_parse_items_handles_think_and_prose():
    text = '<think>hmm</think>Oto zadania:\n[{"question": "Q1", "context": "", "answer": "B"}, {"x": 1}]'
    assert gen_synthetic.parse_items(text) == [{"question": "Q1", "context": "", "answer": "B"}]
    assert gen_synthetic.parse_items("nie ma tu JSON-a") == []


class Teacher(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = body["messages"][-1]["content"]
        topic = prompt.split("Temat: ")[1].split(".\n")[0]
        items = [{"question": f"Pytanie o {topic} nr {i}", "context": "", "answer": "B"} for i in range(2)]
        # One item copies an eval question verbatim and must be dropped.
        items.append({"question": EVAL_Q, "context": "", "answer": "A"})
        data = json.dumps({"choices": [{"message": {"content": json.dumps(items, ensure_ascii=False)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


EVAL_Q = "Zaznacz poprawne dokończenie zdania. Unia w Krewie została zawarta w roku A. 1385 B. 1410"


def test_gen_synthetic_end_to_end(tmp_path):
    ev = tmp_path / "eval.jsonl"
    ev.write_text(json.dumps({"question": EVAL_Q}) + "\n")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Teacher)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    out = tmp_path / "syn.jsonl"
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts/gen_synthetic.py"),
                        "--base-url", f"http://127.0.0.1:{httpd.server_port}/v1",
                        "--categories", "closed_choice,true_false", "--per-category", "6",
                        "--batch", "3", "--eval", str(ev), "-o", str(out)], check=True)
    finally:
        httpd.shutdown()
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert rows and all(r["question"] != EVAL_Q for r in rows)
    assert {r["category"] for r in rows} == {"closed_choice", "true_false"}
    # The split script turns them into per-adapter chat datasets.
    subprocess.run([sys.executable, str(ROOT / "scripts/split_by_category.py"), str(out),
                    "-o", str(tmp_path / "split")], check=True)
    msgs = json.loads((tmp_path / "split/closed_choice.jsonl").read_text().splitlines()[0])["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant"]


def test_train_lora_skips_small_categories(tmp_path):
    (tmp_path / "essay.jsonl").write_text('{"messages": []}\n')
    out = subprocess.run([sys.executable, str(ROOT / "scripts/train_lora.py"), "--model", "bielik-11b",
                          "--category", "essay", "--data-dir", str(tmp_path)],
                         check=True, capture_output=True, text=True).stdout
    assert "skip bielik-11b/essay: 1 examples" in out


def test_ship_size_check_and_served_checkpoint(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("qc", ROOT / "scripts/quantize_checkpoint.py")
    qc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qc)
    (tmp_path / "model.safetensors").write_bytes(b"\0" * 2_000_000)
    (tmp_path / "config.json").write_text("{}")
    assert abs(qc.weights_gb(tmp_path) - 0.002) < 1e-9
    assert qc.load_config()["ship_limit_gb"] == 8.0
    assert qc.load_config()["finetuned_limit_gb"] == 8.8

    spec = importlib.util.spec_from_file_location("rb", ROOT / "scripts/run_baselines.py")
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    assert rb.served_weights("x", {"hf_id": "org/x", "checkpoint": str(tmp_path)}) == str(tmp_path)
    assert rb.served_weights("x", {"hf_id": "org/x", "checkpoint": str(tmp_path / "none")}) == "org/x"

