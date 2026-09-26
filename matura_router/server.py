"""OpenAI-compatible front door for the router.

We don't know yet how the organisers' exam script talks to the model. Most such
scripts speak the OpenAI chat API, so this exposes /v1/chat/completions: the script
sends a question, the router classifies it and answers with the right adapter.
Use model name "router" for automatic routing, or a category name (e.g. "essay")
to force one.
"""

from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .categories import Category
from .router import Router


def _split_messages(messages: list[dict]) -> tuple[str, str]:
    """Last user message is the question; any other user/system text is context."""
    users = [m.get("content", "") for m in messages if m.get("role") == "user"]
    question = users[-1] if users else ""
    context = "\n\n".join(users[:-1])
    return question, context


def make_handler(router: Router):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict):
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.rstrip("/") in ("/v1/models", "/models"):
                ids = ["router"] + [c.value for c in Category]
                return self._send(200, {"object": "list",
                                        "data": [{"id": i, "object": "model"} for i in ids]})
            if self.path.rstrip("/") == "/health":
                return self._send(200, {"ok": True})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path.rstrip("/") not in ("/v1/chat/completions", "/chat/completions"):
                return self._send(404, {"error": "not found"})
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                question, context = _split_messages(req.get("messages", []))
                model = req.get("model", "router")
                forced = Category(model) if model in {c.value for c in Category} else None
                res = router.answer(question, context, category=forced)
            except Exception as e:  # noqa: BLE001
                return self._send(500, {"error": str(e)})
            self._send(200, {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": res.adapter or "base",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": res.answer}}],
                "routing": res.to_dict(),
            })

    return Handler


def serve(router: Router, host: str = "127.0.0.1", port: int = 8080):
    httpd = ThreadingHTTPServer((host, port), make_handler(router))
    print(f"router listening on http://{host}:{port}/v1")
    httpd.serve_forever()
