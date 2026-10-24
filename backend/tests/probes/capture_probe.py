"""Phase 3 probes, run INSIDE an app container with `docker exec` (standard library and Pillow,
which the image has). Prints one JSON line; exit code 0 means the probe passed.

  capture_probe.py offline   probe 20: the container has no network at all (`--network none`).
                             A photo is still read; Gemini, at Google's real address, fails with a
                             clear message and leaves the local result alone (gate 3).
  capture_probe.py health    probe 21: three readings queued at once; /health is timed every
                             50 ms until all are done; every answer must be under 200 ms and no
                             reading may fail (gate 5).

The label is drawn here with Pillow: test data only, never accuracy evidence (D-056).
"""

import io
import json
import os
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFont

BASE = "http://127.0.0.1:8470"
HOST = f"127.0.0.1:{os.environ.get('ENDERCHEST_PORT', '8470')}"
KEY = "AIzaTestKeyThatIsNotReal_0123456789"
LABEL = ["OAT MILK BARISTA", "1 L  MODEL AB-1234X", "MFD 12/01/2026  EXP 14/03/2027",
         "BATCH L4471  Net Qty 500 ml"]


def call(method: str, path: str, body: bytes | None = None,
         content_type: str = "application/json") -> tuple[int, dict]:
    headers = {"Host": HOST}
    if method != "GET":
        headers["X-Enderchest"] = "1"
    if body is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as refused:
        return refused.code, json.loads(refused.read() or b"{}")


def send(method: str, path: str, data: dict) -> tuple[int, dict]:
    return call(method, path, json.dumps(data).encode())


def label_jpeg() -> bytes:
    image = Image.new("RGB", (1200, 120 + len(LABEL) * 90), "white")
    draw = ImageDraw.Draw(image)
    top = 50
    for index, text in enumerate(LABEL):
        size = 80 if index == 0 else 40
        draw.text((50, top), text, fill="black", font=ImageFont.load_default(size=size))
        top += size + 36
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=92)
    return out.getvalue()


def make_drafts(count: int) -> list[str]:
    boundary = uuid.uuid4().hex
    image = label_jpeg()
    parts = b"".join(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"images[]\"; "
        f"filename=\"l{n}.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + image + b"\r\n"
        for n in range(count))
    body = parts + f"--{boundary}--\r\n".encode()
    status, answer = call("POST", "/api/v1/drafts", body,
                          f"multipart/form-data; boundary={boundary}")
    assert status == 201, (status, answer)
    return [draft["id"] for draft in answer["drafts"]]


def settled(draft_id: str, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _, draft = call("GET", f"/api/v1/drafts/{draft_id}")
        if "pending" not in (draft["ocr_status"], draft["gemini_status"]):
            return draft
        time.sleep(0.25)
    raise AssertionError(f"reading of {draft_id} never finished")


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


def offline() -> dict:
    ready()
    try:
        urllib.request.urlopen("https://generativelanguage.googleapis.com", timeout=5)
        network = "reachable"
    except OSError:
        network = "unreachable"
    draft_id = make_drafts(1)[0]
    local = settled(draft_id)
    send("PUT", "/api/v1/gemini/key", {"key": KEY})
    send("PATCH", "/api/v1/settings", {"gemini_mode": "ask"})
    test_status, test = call("POST", "/api/v1/gemini/test")
    extract_status, _ = send("POST", f"/api/v1/drafts/{draft_id}/extract", {"engine": "gemini"})
    after = settled(draft_id)
    result = {
        "network": network,
        "ocr_status": local["ocr_status"],
        "read": {field: p["value"] for field, p in local["proposed"].items()},
        "test": [test_status, test.get("error", {}).get("message")],
        "extract": extract_status,
        "gemini": [after["gemini_status"], after["gemini_error"]],
        "local_kept": after["proposed"] == local["proposed"],
    }
    result["passed"] = (
        network == "unreachable" and local["ocr_status"] == "done"
        and result["read"].get("expiry_date") == "2027-03-14"
        and test_status == 502 and "could not be reached" in (result["test"][1] or "")
        and extract_status == 202 and after["gemini_status"] == "failed"
        and "could not be reached" in (after["gemini_error"] or "") and result["local_kept"])
    return result


def health() -> dict:
    ready()
    timings: list[float] = []
    made: list[str] = []
    threads = [threading.Thread(target=lambda: made.extend(make_drafts(1))) for _ in range(2)]
    for thread in threads:
        thread.start()
    made.extend(make_drafts(1))
    for thread in threads:
        thread.join()
    while True:
        started = time.perf_counter()
        status, answer = call("GET", "/health")
        timings.append((time.perf_counter() - started) * 1000)
        assert status == 200 and answer["status"] == "ok", answer
        states = [call("GET", f"/api/v1/drafts/{draft}")[1]["ocr_status"] for draft in made]
        if "pending" not in states:
            break
        time.sleep(0.05)
    readings = [settled(draft) for draft in made]
    result = {
        "readings": [[d["ocr_status"], d["ocr_info"]["ms"] if d["ocr_info"] else None]
                     for d in readings],
        "health_samples": len(timings),
        "health_ms": {"median": round(statistics.median(timings), 1),
                      "max": round(max(timings), 1)},
    }
    result["passed"] = (len(made) == 3 and all(d["ocr_status"] == "done" for d in readings)
                        and max(timings) < 200 and len(timings) >= 5)
    return result


if __name__ == "__main__":
    outcome = {"offline": offline, "health": health}[sys.argv[1]]()
    print(json.dumps(outcome))
    sys.exit(0 if outcome["passed"] else 1)
