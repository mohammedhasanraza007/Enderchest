"""The camera coach's server tier (Phase 7 spec, Build 2; API 2.15; D-121): the answer built
from read lines, refused frames, and frames that never queue."""

import io
import threading
from datetime import date

import pytest
from PIL import Image

from app import heavy
from app.errors import AppError
from app.integrations.ocr.pipeline import Line
from app.services import coach

TODAY = date(2026, 10, 25)
SIZE = (640, 360)


def line(text: str, confidence: float, top: int = 0, height: int = 20) -> Line:
    return Line(text, confidence, (64, top, 320, top + height), float(height), 0)


def frame_jpeg(width: int = 640, height: int = 360, quality: int = 80) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (90, 80, 70)).save(out, format="JPEG", quality=quality)
    return out.getvalue()


def test_text_is_found_with_three_confident_boxes():
    found = coach.describe([line("OAT MILK", 0.9), line("BARISTA", 0.6, 30),
                            line("1 L", 0.5, 60)], SIZE, TODAY)
    assert found["text_found"] is True


def test_two_confident_boxes_and_unsure_ones_are_not_text_found():
    found = coach.describe([line("OAT MILK", 0.9), line("BARISTA", 0.8, 30),
                            line("1L", 0.49, 60), line("xx", 0.2, 90)], SIZE, TODAY)
    assert found["text_found"] is False
    assert found["confidence"] == round((0.9 + 0.8 + 0.49 + 0.2) / 4, 3)


def test_nothing_read_is_an_empty_answer():
    assert coach.describe([], SIZE, TODAY) == {
        "text_found": False, "confidence": 0.0, "boxes": [], "fields": {}}


def test_boxes_are_fractions_of_the_frame():
    box = coach.describe([line("OAT MILK", 0.9, top=36, height=18)], SIZE, TODAY)["boxes"][0]
    assert box == {"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.05, "conf": 0.9, "kind": "text"}


def test_model_and_date_boxes_are_marked_and_named():
    found = coach.describe([line("OAT MILK BARISTA", 0.99), line("MODEL AB-1234X", 0.95, 30),
                            line("EXP 14/03/2027", 0.97, 60)], SIZE, TODAY)
    assert [box["kind"] for box in found["boxes"]] == ["text", "model", "date"]
    assert found["fields"] == {"model": "AB-1234X", "date": "2027-03-14"}


def test_a_date_over_two_lines_marks_both():
    found = coach.describe([line("BEST BEFORE", 0.95), line("14/03/2027", 0.95, 30)],
                           SIZE, TODAY)
    assert found["fields"]["date"] == "2027-03-14"
    assert [box["kind"] for box in found["boxes"]] == ["date", "date"]


def test_low_confidence_guesses_are_not_named():
    # An unlabelled date and a short unlabelled code are low-confidence proposals.
    found = coach.describe([line("TEA", 0.99), line("X12B", 0.95, 30),
                            line("14/03/2027", 0.6, 60)], SIZE, TODAY)
    assert found["fields"] == {}
    assert {box["kind"] for box in found["boxes"]} == {"text"}


def test_a_frame_must_be_a_jpeg_of_at_most_200_kb():
    with pytest.raises(AppError) as png:
        out = io.BytesIO()
        Image.new("RGB", (64, 64)).save(out, format="PNG")
        coach.decode(out.getvalue())
    assert (png.value.code, png.value.status) == ("unsupported_media", 415)
    with pytest.raises(AppError) as big:
        coach.decode(b"\xff\xd8\xff" + bytes(coach.FRAME_MAX_BYTES))
    assert (big.value.code, big.value.status) == ("payload_too_large", 413)
    with pytest.raises(AppError) as broken:
        coach.decode(b"\xff\xd8\xff\xe0" + b"not a picture" * 10)
    assert broken.value.code == "unsupported_media"
    with pytest.raises(AppError) as wide:
        coach.decode(frame_jpeg(1600, 900, quality=10))
    assert wide.value.code == "unsupported_media"
    assert coach.decode(frame_jpeg()).size == SIZE


@pytest.fixture
def no_gap(monkeypatch):
    monkeypatch.setattr(coach, "_last_accepted", float("-inf"))


def test_a_frame_never_waits_behind_other_heavy_work(no_gap):
    release = threading.Event()
    blocker = heavy.submit(release.wait)  # a draft reading holding the worker
    try:
        with pytest.raises(AppError) as busy:
            coach.frame(1, frame_jpeg(), TODAY)
        assert (busy.value.code, busy.value.status) == ("busy", 409)
    finally:
        release.set()
        blocker.result()


def test_a_second_frame_within_half_a_second_is_rate_limited(no_gap, monkeypatch):
    monkeypatch.setattr(coach, "read_image", lambda image, threads: [])
    assert coach.frame(1, frame_jpeg(), TODAY)["text_found"] is False
    with pytest.raises(AppError) as limited:
        coach.frame(1, frame_jpeg(), TODAY)
    assert (limited.value.code, limited.value.status) == ("rate_limited", 429)


def test_ten_frames_at_once_read_one(no_gap, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    reads = []

    def slow_read(image, threads):
        reads.append(1)
        started.set()
        release.wait(5)
        return []

    monkeypatch.setattr(coach, "read_image", slow_read)
    answers: list[str] = []

    def send():
        try:
            coach.frame(1, frame_jpeg(), TODAY)
            answers.append("ok")
        except AppError as error:
            answers.append(error.code)

    threads = [threading.Thread(target=send) for _ in range(10)]
    for thread in threads:
        thread.start()
    started.wait(5)
    release.set()
    for thread in threads:
        thread.join(10)
    assert len(reads) == 1
    assert answers.count("ok") == 1
    assert set(answers) - {"ok"} <= {"busy", "rate_limited"}


def test_heavy_try_submit_refuses_while_a_job_waits_and_runs_once_idle():
    release = threading.Event()
    first = heavy.submit(release.wait)
    with pytest.raises(heavy.Busy):
        heavy.try_submit(lambda: "frame")
    release.set()
    first.result()
    assert heavy.try_submit(lambda: "frame").result() == "frame"
