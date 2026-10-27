"""Phase 9 probe, run INSIDE an app container with `docker exec` (standard library only).
Prints one JSON line; exit code 0 means the probe passed.

  assistant_probe.py   probe 28: the container has no network (`--network none`) and Gemini's
                       address points at a recorder in this script that plays Gemini: it first
                       asks for `search_items`, then answers with the row's name. With a key set
                       and "Use the assistant" on, the answer comes back linked; the recorder
                       sees the question and only the tool's rows (the six allowed fields), never
                       an item's notes, price, attributes or another item's name; and nothing in
                       the database changes (items, events, savings, drafts, notifications).

The recorder is test code: a regression check of what leaves, never evidence of real answers.
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = "http://127.0.0.1:8470"
HOST = f"127.0.0.1:{os.environ.get('ENDERCHEST_PORT', '8470')}"
RECORDER_PORT = 9911  # probe 28 runs the container with ENDERCHEST_GEMINI_URL pointing here
KEY = "AIzaTestKeyThatIsNotReal_0123456789"
WANTED = "Zebra probe spanner"
OTHER = "Quokka probe kettle"  # an item the question does not match: it must never leave
NOTE = "probe-secret-note-71f3"
ROW_FIELDS = {"public_id", "name", "category", "location", "quantity", "expiry"}
received: list[dict] = []


def _reply(parts: list[dict]) -> bytes:
    return json.dumps({"candidates": [{"content": {"role": "model", "parts": parts}}]}).encode()


class Recorder(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        received.append(body)
        if len(received) == 1:
            out = _reply([{"functionCall": {"name": "search_items", "args": {"q": "zebra"}}}])
        else:
            out = _reply([{"text": f"{WANTED} is in Garage."}])
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *_args) -> None:
        pass


def call(method: str, path: str, data: dict | None = None) -> tuple[int, dict]:
    headers = {"Host": HOST}
    if method != "GET":
        headers["X-Enderchest"] = "1"
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    request = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as refused:
        raw = refused.read().decode()
        return refused.code, json.loads(raw) if raw.startswith("{") else {}


def ready() -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if call("GET", "/health")[1].get("status") == "ok":
                break
        except OSError:
            pass
        time.sleep(0.5)
    call("PUT", "/api/v1/profile", {"name": "Probe", "timezone": "Asia/Kolkata"})
    call("PATCH", "/api/v1/settings", {"first_run_step": "done"})


def snapshot(public_ids: list[str]) -> list:
    items = [call("GET", f"/api/v1/items/{pid}")[1] for pid in public_ids]
    events = [len(call("GET", f"/api/v1/items/{pid}/events")[1].get("items", []))
              for pid in public_ids]
    return [call("GET", "/api/v1/items?limit=1")[1]["total"],
            [item.get("updated_at") for item in items], events,
            call("GET", "/api/v1/savings?period=all")[1]["total_paise"],
            len(call("GET", "/api/v1/drafts")[1]["items"]),
            call("GET", "/api/v1/notifications/count")[1]]


def function_rows(body: dict) -> list[dict]:
    rows = []
    for content in body.get("contents", []):
        for part in content.get("parts", []):
            response = (part.get("functionResponse") or {}).get("response") or {}
            rows += response.get("rows", [])
            if "item" in response:
                rows.append(response["item"])
    return rows


def main() -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", RECORDER_PORT), Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    ready()
    _, wanted = call("POST", "/api/v1/items", {"name": WANTED, "notes": NOTE, "price_paise": 34900,
                                                "attributes": {"size": "13 mm"}})
    _, other = call("POST", "/api/v1/items", {"name": OTHER, "notes": NOTE})
    call("PUT", "/api/v1/gemini/key", {"key": KEY})
    off_status, off = call("POST", "/api/v1/assistant/chat",
                           {"messages": [{"role": "user", "content": "Do I have a zebra?"}]})
    call("PATCH", "/api/v1/settings", {"assistant_share_item_text": True})
    before = snapshot([wanted["public_id"], other["public_id"]])
    status, answer = call("POST", "/api/v1/assistant/chat",
                          {"messages": [{"role": "user", "content": "Where is my zebra spanner?"}]})
    after = snapshot([wanted["public_id"], other["public_id"]])
    sent = json.dumps(received)
    rows = [row for body in received for row in function_rows(body)]
    linked = [s["public_id"] for s in answer.get("segments", []) if s.get("public_id")]
    result = {
        "switched_off": [off_status, off.get("error", {}).get("details", {}).get("reason")],
        "status": status, "requests": len(received), "rows_sent": len(rows),
        "row_fields_ok": all(set(row) == ROW_FIELDS for row in rows),
        "note_sent": NOTE in sent, "price_sent": "34900" in sent,
        "attributes_sent": "13 mm" in sent, "other_item_sent": OTHER.lower() in sent.lower(),
        "linked": linked == [wanted["public_id"]], "rows_checked": answer.get("rows_checked"),
        "database_unchanged": before == after,
    }
    result["passed"] = (result["switched_off"] == [409, "assistant_off"] and status == 200
                        and len(received) == 2 and len(rows) == 1 and result["row_fields_ok"]
                        and not result["note_sent"] and not result["price_sent"]
                        and not result["attributes_sent"] and not result["other_item_sent"]
                        and result["linked"] and result["rows_checked"] == 1
                        and result["database_unchanged"])
    return result


if __name__ == "__main__":
    outcome = main()
    print(json.dumps(outcome))
    sys.exit(0 if outcome["passed"] else 1)
