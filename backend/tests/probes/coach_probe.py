"""Phase 7 probes, run INSIDE the test app container with `docker exec` (standard library and
Pillow). Prints one JSON line; exit code 0 means the probe passed.

  coach_probe.py health   probe 26: coach frames are sent back to back for 20 s while /health is
                          timed every 50 ms: every answer under 200 ms, at least 10 frames read,
                          and no file appears under /data (a frame is never stored).
  coach_probe.py burst    probe 27: ten frames at once: exactly one is read, the rest answer
                          `busy` or `rate_limited` at once (never two OCR jobs, never a queue).

Frames are drawn here with Pillow: test data only, never gate evidence (D-056).
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

from PIL import Image, ImageDraw, ImageFont

BASE = "http://127.0.0.1:8470"
HOST = f"127.0.0.1:{os.environ.get('ENDERCHEST_PORT', '8470')}"
DATA = os.environ.get("ENDERCHEST_DATA_DIR", "/data")


def frame_jpeg() -> bytes:
    image = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26)
    for row, text in enumerate(["OAT MILK BARISTA", "MODEL AB-1234X", "EXP 14/03/2027"]):
        draw.text((40, 40 + row * 47), text, fill="black", font=font)
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=80)
    return out.getvalue()


def post_frame(data: bytes) -> int:
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
            f"filename=\"frame.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n").encode() + data + \
        f"\r\n--{boundary}--\r\n".encode()
    headers = {"Host": HOST, "X-Enderchest": "1",
               "Content-Type": f"multipart/form-data; boundary={boundary}"}
    request = urllib.request.Request(BASE + "/api/v1/capture/frame", data=body, method="POST",
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as refused:
        return refused.code


def health_ms() -> float:
    started = time.perf_counter()
    request = urllib.request.Request(BASE + "/health", headers={"Host": HOST})
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()
    return (time.perf_counter() - started) * 1000


def files() -> set[str]:
    found = set()
    for root, _, names in os.walk(DATA):
        found.update(os.path.join(root, name) for name in names
                     if not name.endswith(("-wal", "-shm")))
    return found


def health() -> dict:
    data = frame_jpeg()
    before = files()
    stop = threading.Event()
    read = []

    def sender():
        while not stop.is_set():
            status = post_frame(data)
            if status == 200:
                read.append(1)
            time.sleep(0.55)  # just over the half-second gap

    thread = threading.Thread(target=sender)
    thread.start()
    timings = []
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        timings.append(health_ms())
        time.sleep(0.05)
    stop.set()
    thread.join()
    added = sorted(files() - before)
    worst = max(timings)
    ok = worst < 200 and len(read) >= 10 and not added
    return {"ok": ok, "frames_read": len(read), "health_checks": len(timings),
            "health_max_ms": round(worst, 1), "files_added": added}


def burst() -> dict:
    data = frame_jpeg()
    time.sleep(0.6)
    statuses: list[int] = []
    gate = threading.Barrier(10)

    def one():
        gate.wait()
        statuses.append(post_frame(data))

    threads = [threading.Thread(target=one) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    ok = statuses.count(200) == 1 and all(code in (200, 409, 429) for code in statuses)
    return {"ok": ok, "statuses": sorted(statuses)}


if __name__ == "__main__":
    result = {"health": health, "burst": burst}[sys.argv[1]]()
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)
