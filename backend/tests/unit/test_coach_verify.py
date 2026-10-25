"""Phase 7 verification probes (docs/reviews/phase-7-verification.md, V1 to V6): refused frames
the build's tests did not try, and the worker and the gap after a refusal or a failed reading."""

import io
from datetime import date

import pytest
from PIL import Image

from app import heavy
from app.errors import AppError
from app.services import coach

TODAY = date(2026, 10, 25)


def jpeg(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (90, 80, 70)).save(out, format="JPEG", quality=30)
    return out.getvalue()


@pytest.fixture
def no_gap(monkeypatch):
    monkeypatch.setattr(coach, "_last_accepted", float("-inf"))


@pytest.mark.parametrize("data", [
    b"",                                  # V1 an empty upload
    jpeg(640, 360)[:400],                 # V2 a truncated JPEG
    jpeg(1281, 200),                      # V3 one pixel over the long-side limit
    b"\x89PNG\r\n\x1a\n" + b"0" * 64,     # V4 a PNG
])
def test_odd_frames_are_refused_with_415_and_never_reach_the_worker(no_gap, monkeypatch, data):
    monkeypatch.setattr(coach, "read_image", lambda *_: pytest.fail("frame was read"))
    with pytest.raises(AppError) as refused:
        coach.frame(1, data, TODAY)
    assert refused.value.status == 415


def test_a_busy_frame_does_not_use_up_the_gap(no_gap, monkeypatch):
    # V5: a frame refused as busy was never read, so the next one after the job may be read.
    import threading
    release = threading.Event()
    blocker = heavy.submit(release.wait)
    with pytest.raises(AppError):
        coach.frame(1, jpeg(640, 360), TODAY)
    release.set()
    blocker.result()
    monkeypatch.setattr(coach, "read_image", lambda *_: [])
    assert coach.frame(1, jpeg(640, 360), TODAY)["text_found"] is False


def test_a_failed_reading_frees_the_worker(no_gap, monkeypatch):
    # V6: an OCR crash inside a frame must not leave the worker counted as busy forever.
    def crash(*_):
        raise RuntimeError("engine fell over")

    monkeypatch.setattr(coach, "read_image", crash)
    with pytest.raises(RuntimeError):
        coach.frame(1, jpeg(640, 360), TODAY)
    assert heavy.run(lambda: "idle") == "idle"
    heavy.try_submit(lambda: None).result()
