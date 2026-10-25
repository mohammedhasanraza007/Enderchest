"""The camera coach's server tier (Phase 7 spec, Build 2; API 2.15; D-121).

About once a second the camera page sends one small JPEG frame, only when its own cheap checks
(sharpness and light) pass. The frame is checked by its bytes, decoded in memory and read by the
Phase 3 OCR engine in the shared heavy worker; it is never written anywhere and never leaves the
machine. A frame never waits: a frame within `MIN_GAP_S` of the last accepted one is
`rate_limited`, and while the worker has any job (a draft reading, an upload, another frame) the
answer is `busy`. The page drops the frame either way.
"""

import io
import threading
import time
from datetime import date

from PIL import Image, UnidentifiedImageError

from .. import heavy
from ..errors import AppError
from ..images import sniff
from ..integrations.ocr.pipeline import Line, read_image
from . import extraction

FRAME_MAX_BYTES = 200 * 1024
FRAME_MAX_EDGE = 1280  # the page sends 640 px; anything far larger is not a coach frame
MIN_GAP_S = 0.5
# Spec Build 2: text is found when at least 3 boxes are read with confidence 0.5 or more.
TEXT_MIN_BOXES = 3
TEXT_MIN_CONFIDENCE = 0.5

_lock = threading.Lock()
_last_accepted = float("-inf")


def decode(data: bytes) -> Image.Image:
    """The frame as an RGB image, or the one error shape (413 or 415)."""
    if len(data) > FRAME_MAX_BYTES:
        raise AppError("payload_too_large", 413, "A coach frame is at most 200 KB.")
    if sniff(data) != "jpeg":
        raise AppError("unsupported_media", 415, "A coach frame must be a JPEG.")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            if max(opened.size) > FRAME_MAX_EDGE:
                raise AppError("unsupported_media", 415,
                               f"A coach frame is at most {FRAME_MAX_EDGE} px on its long side.")
            return opened.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise AppError("unsupported_media", 415,
                       "That frame could not be read as a JPEG.") from error


def _accept(image: Image.Image, threads: int):
    """Start the reading now or refuse; the gap and the start are decided under one lock."""
    global _last_accepted
    with _lock:
        now = time.monotonic()
        if now - _last_accepted < MIN_GAP_S:
            raise AppError("rate_limited", 429, "Send at most two frames a second.")
        try:
            future = heavy.try_submit(read_image, image, threads)
        except heavy.Busy:
            raise AppError("busy", 409, "The last frame is still being read.") from None
        _last_accepted = now
    return future


def _sure(proposal: dict | None) -> str | None:
    """A field is named to the owner only when the reading is not a low-confidence guess."""
    if proposal is None or proposal["confidence"] == "low":
        return None
    return str(proposal["value"])


def describe(lines: list[Line], size: tuple[int, int], today: date) -> dict:
    """The API 2.15 answer for the lines read from one frame of `size` pixels."""
    width, height = size
    proposed = extraction.propose(lines, today)["proposed"] if lines else {}
    model = _sure(proposed.get("model"))
    expiry = _sure(proposed.get("expiry_date"))
    date_lines = set(extraction.covering(lines, proposed["expiry_date"]["text"])) if expiry \
        else set()
    model_marked = False
    boxes = []
    for index, line in enumerate(lines):
        kind = "text"
        if index in date_lines:
            kind = "date"
        elif model and not model_marked and model in line.text:
            kind, model_marked = "model", True
        left, top, right, bottom = line.box
        boxes.append({"x": round(left / width, 4), "y": round(top / height, 4),
                      "w": round((right - left) / width, 4), "h": round((bottom - top) / height, 4),
                      "conf": line.confidence, "kind": kind})
    confident = sum(line.confidence >= TEXT_MIN_CONFIDENCE for line in lines)
    mean = sum(line.confidence for line in lines) / len(lines) if lines else 0.0
    fields = {key: value for key, value in (("model", model), ("date", expiry)) if value}
    return {"text_found": confident >= TEXT_MIN_BOXES, "confidence": round(mean, 3),
            "boxes": boxes, "fields": fields}


def frame(threads: int, data: bytes, today: date) -> dict:
    """POST /capture/frame: read one frame now, or refuse at once."""
    image = decode(data)
    lines = _accept(image, threads).result()
    return describe(lines, image.size, today)
