"""Phase 7: the camera coach's server tier through the API (API 2.15, spec Build 2, D-121).

Frames are drawn in memory (`imagekit.coach_frame`) and read by the real OCR engine: regression
tools only. Gate 1 needs the owner's real captures and gate 4 the real webcam (D-056)."""

import os

import pytest

from app.services import coach
from tests import imagekit
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

LABEL = ["OAT MILK BARISTA", "MODEL AB-1234X", "EXP 14/03/2027"]


@pytest.fixture(autouse=True)
def _no_gap(monkeypatch):
    # The half-second gap is per process; every test starts as if no frame came before.
    monkeypatch.setattr(coach, "_last_accepted", float("-inf"))


def send(stack: Stack, data: bytes, content_type: str = "image/jpeg"):
    files = {"image": ("frame.jpg", data, content_type)}
    return stack.client.post("/api/v1/capture/frame", files=files, headers=HEADERS)


def files_under(folder) -> list[str]:
    return sorted(os.path.relpath(os.path.join(root, name), folder)
                  for root, _, names in os.walk(folder) for name in names)


def test_a_label_frame_is_read_with_its_model_and_date(stack: Stack):
    response = send(stack, imagekit.coach_frame(LABEL))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text_found"] is True
    assert body["fields"] == {"model": "AB-1234X", "date": "2027-03-14"}
    kinds = [box["kind"] for box in body["boxes"]]
    assert kinds.count("model") == 1 and kinds.count("date") >= 1
    for box in body["boxes"]:
        assert 0 <= box["x"] < 1 and 0 <= box["y"] < 1
        assert 0 < box["w"] <= 1 and 0 < box["h"] <= 1
        assert 0 <= box["conf"] <= 1


def test_an_empty_desk_has_no_text_and_no_fields_key_values(stack: Stack):
    response = send(stack, imagekit.coach_frame([], background="#6b5b4f"))
    assert response.status_code == 200, response.text
    assert response.json() == {"text_found": False, "confidence": 0.0, "boxes": [],
                               "fields": {}}


def test_plain_text_without_fields_is_text_found_and_quiet(stack: Stack):
    body = send(stack, imagekit.coach_frame(["FRESH OAT DRINK", "SHAKE WELL", "KEEP COOL"]))
    assert body.status_code == 200, body.text
    assert body.json()["text_found"] is True
    assert body.json()["fields"] == {}


def test_refused_frames_use_the_one_error_shape(stack: Stack):
    png = send(stack, imagekit.png_with_alpha(), "image/png")
    assert png.status_code == 415 and png.json()["error"]["code"] == "unsupported_media"
    big = send(stack, b"\xff\xd8\xff" + bytes(coach.FRAME_MAX_BYTES))
    assert big.status_code == 413 and big.json()["error"]["code"] == "payload_too_large"
    missing = stack.client.post("/api/v1/capture/frame", files={"other": ("a", b"x")},
                                headers=HEADERS)
    assert missing.status_code == 422
    assert "Traceback" not in png.text + big.text + missing.text


def test_a_frame_without_the_safety_header_is_refused(stack: Stack):
    files = {"image": ("frame.jpg", imagekit.coach_frame(LABEL), "image/jpeg")}
    response = stack.client.post("/api/v1/capture/frame", files=files)
    assert response.status_code == 403


def test_a_frame_is_never_stored(stack: Stack):
    data_dir = stack.settings.data_dir
    before = files_under(data_dir)
    conn = stack.manager.open_connection()
    events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert send(stack, imagekit.coach_frame(LABEL)).status_code == 200
    assert send(stack, imagekit.png_with_alpha(), "image/png").status_code == 415
    added = set(files_under(data_dir)) - set(before)
    assert {name for name in added if not name.endswith(("-wal", "-shm"))} == set()
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == events
    conn.close()


def test_a_frame_during_a_draft_reading_is_busy_at_once(stack: Stack):
    made = stack.client.post("/api/v1/drafts", headers=HEADERS, files=[
        ("images[]", ("label.jpg", imagekit.label_jpeg(LABEL), "image/jpeg"))])
    assert made.status_code == 201, made.text
    response = send(stack, imagekit.coach_frame(LABEL))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "busy"


def test_a_second_frame_within_half_a_second_is_rate_limited(stack: Stack):
    assert send(stack, imagekit.coach_frame([])).status_code == 200
    second = send(stack, imagekit.coach_frame([]))
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
