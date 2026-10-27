"""A recorded stand-in for Gemini's REST API, for tests only (D-056: never Gemini evidence).

It answers each `models/{model}:generateContent` request with the next scripted reply, in the
shape Google documents for function calling, and records every request it receives (path,
headers and JSON body), so a test can inspect exactly what left the app (Phase 9 gate 4).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SIGNATURE = "c2lnbmF0dXJlLWZyb20tdGhlLWZha2U="  # stands for an opaque thought signature


def call(name: str, args: dict, *, call_id: str | None = None) -> tuple[int, dict]:
    """A model turn that asks for one tool."""
    return calls((name, args, call_id))


def calls(*wanted: tuple[str, dict, str | None]) -> tuple[int, dict]:
    """A model turn that asks for several tools at once (parallel calls)."""
    parts = []
    for name, args, call_id in wanted:
        function = {"name": name, "args": args}
        if call_id:
            function["id"] = call_id
        parts.append({"functionCall": function, "thoughtSignature": SIGNATURE})
    return 200, {"candidates": [{"content": {"role": "model", "parts": parts},
                                 "finishReason": "STOP"}]}


def text(answer: str) -> tuple[int, dict]:
    """A model turn with the final answer (and a thought summary the app must not show)."""
    return 200, {"candidates": [{"content": {"role": "model", "parts": [
        {"text": "Thinking about the rows.", "thought": True}, {"text": answer}]},
        "finishReason": "STOP"}]}


def refused(status: int, message: str) -> tuple[int, dict]:
    return status, {"error": {"code": status, "message": message, "status": "REFUSED"}}


class FakeGemini:
    def __init__(self, *replies: tuple[int, dict]) -> None:
        self.replies = list(replies)
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                fake.requests.append({"path": self.path, "headers": dict(self.headers),
                                      "raw": raw.decode(), "body": json.loads(raw)})
                status, body = (fake.replies.pop(0) if fake.replies
                                else refused(500, "The fake's script has ended."))
                encoded = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1beta"

    def __enter__(self) -> "FakeGemini":
        self.thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.server.shutdown()
        self.server.server_close()
