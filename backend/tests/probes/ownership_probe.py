"""Phase 6 probes, run INSIDE an app container with `docker exec` (standard library and Pillow,
which the image has). Prints one JSON line; exit code 0 means the probe passed.

  ownership_probe.py private   probe 24: the container has no network (`--network none`) and
                               Gemini's address points at a recorder in this script. With a key
                               set, Gemini on `auto` and photo sharing on, text and photo checks
                               reach the recorder zero times; Test connection reaches it (so the
                               recorder would have seen a leak); no request it receives carries an
                               item name. The check still answers offline.
  ownership_probe.py honest    probe 25: answers and the page never say "certain", "you own
                               this" or "100%"; a check saves nothing (items, drafts, savings
                               unchanged); a saving is refused without a positive typed price,
                               and the totals equal the confirmed entries.

Labels are drawn here with Pillow: test data only, never accuracy evidence (D-056).
"""

import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageDraw, ImageFont

BASE = "http://127.0.0.1:8470"
HOST = f"127.0.0.1:{os.environ.get('ENDERCHEST_PORT', '8470')}"
RECORDER_PORT = 9911  # probe 24 runs the container with ENDERCHEST_GEMINI_URL pointing here
KEY = "AIzaTestKeyThatIsNotReal_0123456789"
SECRET_NAMES = ["Zebra probe spanner", "Quokka probe buck module"]
FORBIDDEN = ("certain", "you own this", "100%")
received: list[bytes] = []


class Recorder(BaseHTTPRequestHandler):
    def _record(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        received.append(self.path.encode() + b"\n" + self.rfile.read(length))
        self.send_response(500)
        self.end_headers()

    do_GET = do_POST = _record

    def log_message(self, *_args) -> None:
        pass


def call(method: str, path: str, body: bytes | None = None,
         content_type: str = "application/json") -> tuple[int, dict, str]:
    headers = {"Host": HOST}
    if method != "GET":
        headers["X-Enderchest"] = "1"
    if body is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode()
            return response.status, _json(raw), raw
    except urllib.error.HTTPError as refused:
        raw = refused.read().decode()
        return refused.code, _json(raw), raw


def _json(raw: str) -> dict:
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}  # the page shell is HTML


def send(method: str, path: str, data: dict) -> tuple[int, dict, str]:
    return call(method, path, json.dumps(data).encode())


def multipart(parts: list[tuple[str, str | None, bytes]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = b""
    for name, filename, content in parts:
        disposition = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "")
        kind = "Content-Type: image/jpeg\r\n" if filename else ""
        body += (f"--{boundary}\r\nContent-Disposition: {disposition}\r\n{kind}\r\n".encode()
                 + content + b"\r\n")
    return body + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def label(lines: list[str]) -> bytes:
    image = Image.new("RGB", (1200, 120 + len(lines) * 110), "white")
    draw = ImageDraw.Draw(image)
    for index, text in enumerate(lines):
        draw.text((50, 50 + index * 110), text, fill="black",
                  font=ImageFont.load_default(size=80 if index == 0 else 40))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=92)
    return out.getvalue()


PHOTO = label(["BUCK MODULE", "MODEL LM2596S"])


def check(text: str | None = None, image: bytes | None = None) -> tuple[int, dict, str]:
    parts = ([("image", "q.jpg", image)] if image else []) + (
        [("text", None, text.encode())] if text else [])
    body, kind = multipart(parts)
    return call("POST", "/api/v1/ownership/check", body, kind)


def ready() -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if call("GET", "/health")[1].get("status") == "ok":
                break
        except OSError:
            pass
        time.sleep(0.5)
    send("PUT", "/api/v1/profile", {"name": "Probe", "timezone": "Asia/Kolkata"})
    send("PATCH", "/api/v1/settings", {"first_run_step": "done"})


def seed() -> str:
    send("POST", "/api/v1/items", {"name": SECRET_NAMES[0], "attributes": {"size": "13 mm"}})
    _, module, _ = send("POST", "/api/v1/items", {"name": SECRET_NAMES[1],
                                                  "attributes": {"model": "LM2596S"}})
    body, kind = multipart([("image", "a.jpg", PHOTO)])
    call("POST", f"/api/v1/items/{module['public_id']}/photos", body, kind)
    return module["public_id"]


def embedded(timeout: float = 90.0) -> None:
    """The background job embeds the new photo within seconds (it ticks every 10 s when idle)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _, answer, _ = check(image=PHOTO)
        if any("Looks similar" in c["reasons"] for c in answer.get("candidates", [])):
            return
        time.sleep(2)
    raise AssertionError("the new photo was never embedded")


def private() -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", RECORDER_PORT), Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    ready()
    module = seed()
    send("PUT", "/api/v1/gemini/key", {"key": KEY})
    send("PATCH", "/api/v1/settings", {"gemini_mode": "auto", "share_images_with_gemini": True})
    embedded()
    statuses, used, top = [], [], None
    for text, image in (("zebra spanner 13 mm", None), (None, PHOTO), ("buck module", PHOTO)):
        status, answer, _ = check(text, image)
        statuses.append(status)
        used.append(answer.get("engine", {}).get("gemini_used"))
        if image and text:
            first = answer["candidates"][0]
            top = [first["public_id"] == module, first["level"]]
    during_checks = len(received)
    call("POST", "/api/v1/gemini/test")  # the recorder must see this one
    leaked = [r for r in received if any(n.lower().encode() in r.lower() for n in SECRET_NAMES)]
    result = {"statuses": statuses, "gemini_used": used, "recorded_during_checks": during_checks,
              "recorded_after_test_connection": len(received), "item_names_sent": len(leaked),
              "photo_and_words_top": top}
    result["passed"] = (statuses == [200, 200, 200] and used == [False] * 3
                        and during_checks == 0 and len(received) >= 1 and not leaked
                        and top == [True, "high"])
    return result


def counts() -> list:
    items = call("GET", "/api/v1/items?limit=1")[1]["total"]
    drafts = len(call("GET", "/api/v1/drafts")[1]["items"])
    savings = call("GET", "/api/v1/savings?period=all")[1]
    return [items, drafts, savings["total_paise"], len(savings["items"])]


def honest() -> dict:
    ready()
    module = seed()
    before = counts()
    answers = [check("zebra spanner 13 mm"), check(None, PHOTO), check("buck module", PHOTO),
               check("something I do not own")]
    words = sorted({w for _, _, raw in answers for w in FORBIDDEN if w in raw.lower()})
    page_status, _, html = call("GET", "/camera?mode=own")
    after = counts()
    refused = [send("POST", "/api/v1/savings", body)[0] for body in (
        {"item_public_id": module}, {"item_public_id": module, "price_paise": 0},
        {"item_public_id": module, "price_paise": -5}, {"price_paise": 100},
        {"item_public_id": module, "price_paise": "100"})]
    unchanged = counts()
    send("POST", "/api/v1/savings", {"item_public_id": module, "price_paise": 124000})
    send("POST", "/api/v1/savings", {"item_name": "Probe case", "price_paise": 49950})
    listing = call("GET", "/api/v1/savings?period=all")[1]
    listed = sum(entry["price_paise"] for entry in listing["items"])
    result = {"forbidden_words": words, "page_status": page_status, "before": before,
              "after_checks": after, "refused": refused, "after_refusals": unchanged,
              "total": listing["total_paise"], "listed": listed, "month": listing["month_paise"]}
    result["passed"] = (not words and before == after == unchanged and page_status == 200
                        and all(status == 422 for status in refused)
                        and listing["total_paise"] == listed == listing["month_paise"] == 173950
                        and not any(w in html.lower() for w in FORBIDDEN))
    return result


if __name__ == "__main__":
    found = {"private": private, "honest": honest}[sys.argv[1]]()
    print(json.dumps(found))
    sys.exit(0 if found["passed"] else 1)
