"""Phase 6: "Do I own this?" and savings (API 2.14, spec gates 2 to 4, D-114 to D-119).

Images are drawn in memory (`imagekit`): regression tools only, never the gate-1 measurement,
which needs the owner's 20 photos (D-056)."""

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from app import clock
from tests import imagekit
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

ZONE = "Asia/Kolkata"
FORBIDDEN = ("certain", "you own this", "100%")


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def make(stack: Stack, name: str, **body) -> dict:
    response = stack.post("/api/v1/items", {"name": name, **body})
    assert response.status_code == 201, response.text
    return response.json()


def check(stack: Stack, text: str | None = None, image: bytes | None = None):
    # Always multipart, as the page sends FormData; a text-only part has no file name.
    files: dict = {"image": ("query.jpg", image, "image/jpeg")} if image else {}
    if text is not None:
        files["text"] = (None, text)
    return stack.client.post("/api/v1/ownership/check", files=files, headers=HEADERS)


def candidates(stack: Stack, text: str | None = None, image: bytes | None = None) -> list[dict]:
    response = check(stack, text, image)
    assert response.status_code == 200, response.text
    assert not any(word in response.text.lower() for word in FORBIDDEN)
    return response.json()["candidates"]


def changes(stack: Stack) -> int:
    conn = sqlite3.connect(stack.settings.db_path)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return sum(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables)
    finally:
        conn.close()


def test_text_only_ranks_the_right_size_and_hides_the_wrong_one(stack: Stack):
    right = make(stack, "13 mm spanner", attributes={"size": "13 mm"})
    make(stack, "14 mm spanner", attributes={"size": "14 mm"})
    make(stack, "Oat milk", attributes={"size": "1 L"})
    found = candidates(stack, "13 mm spanner")
    assert [c["public_id"] for c in found] == [right["public_id"]]
    assert found[0]["level"] == "medium" and "Same size" in found[0]["reasons"]


def test_an_equal_model_number_is_high(stack: Stack):
    item = make(stack, "Sony WH-1000XM4 headphones", attributes={"model": "WH-1000XM4"})
    found = candidates(stack, "sony wh1000xm4")
    assert found[0]["public_id"] == item["public_id"] and found[0]["level"] == "high"
    assert "Same model number" in found[0]["reasons"]


def test_only_active_items_outside_trash_qualify(stack: Stack):
    used = make(stack, "Blue mug")
    trashed = make(stack, "Blue mug large")
    assert stack.post(f"/api/v1/items/{used['public_id']}/use", {"amount": 1}).status_code == 200
    assert stack.client.delete(f"/api/v1/items/{trashed['public_id']}",
                               headers=HEADERS).status_code == 200
    assert candidates(stack, "blue mug") == []


def test_the_check_writes_nothing_and_keeps_no_photo(stack: Stack):
    make(stack, "Tea strainer")
    before = changes(stack)
    candidates(stack, "tea strainer")
    candidates(stack, image=imagekit.label_jpeg(["TEA STRAINER", "Model TS-200"]))
    assert changes(stack) == before
    assert list(stack.settings.upload_tmp_dir.glob("*")) == []
    assert list(stack.settings.photos_dir.glob("*")) == []


def test_a_photo_check_reads_the_label_and_finds_the_look_alike(stack: Stack):
    label = imagekit.label_jpeg(["BUCK CONVERTER", "MODEL LM2596S"])
    item = make(stack, "Buck converter", attributes={"model": "LM2596S"})
    upload = stack.client.post(f"/api/v1/items/{item['public_id']}/photos", headers=HEADERS,
                               files={"image": ("a.jpg", label, "image/jpeg")})
    assert upload.status_code == 201
    assert stack.app.state.embedder.tick() == 1  # the background job embeds the new photo
    response = check(stack, image=label)
    body = response.json()
    assert body["engine"]["gemini_used"] is False and body["engine"]["ocr"]
    top = body["candidates"][0]
    assert top["public_id"] == item["public_id"] and top["level"] == "high"
    assert {"Same model number", "Looks similar"} <= set(top["reasons"])


def test_a_look_alike_alone_is_at_most_possible(stack: Stack):
    photo = imagekit.jpeg(colour=(30, 90, 160))
    item = make(stack, "Something blue")
    stack.client.post(f"/api/v1/items/{item['public_id']}/photos", headers=HEADERS,
                      files={"image": ("a.jpg", photo, "image/jpeg")})
    stack.app.state.embedder.tick()
    found = candidates(stack, image=photo)
    assert [(c["public_id"], c["level"]) for c in found] == [(item["public_id"], "low")]


def test_the_backfill_embeds_old_photos_and_skips_hidden_ones(stack: Stack):
    item = make(stack, "Lamp")
    ids = [stack.client.post(f"/api/v1/items/{item['public_id']}/photos", headers=HEADERS,
                             files={"image": ("a.jpg", imagekit.jpeg(), "image/jpeg")}).json()["id"]
           for _ in range(2)]
    stack.client.delete(f"/api/v1/photos/{ids[1]}", headers=HEADERS)
    assert stack.app.state.embedder.tick() == 1
    assert stack.app.state.embedder.tick() == 0  # nothing left: an idle tick writes nothing


def test_the_check_works_with_the_network_off(stack: Stack, monkeypatch: pytest.MonkeyPatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("the ownership check must not use the network")

    # The real network transport, not the test client's in-process one.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
    make(stack, "Glue gun", attributes={"model": "GG-60"})
    assert candidates(stack, "glue gun GG-60")[0]["level"] == "high"


def test_the_check_needs_a_photo_or_words(stack: Stack):
    assert check(stack, "  ").status_code == 422
    assert check(stack, "x" * 201).status_code == 422
    bad = stack.client.post("/api/v1/ownership/check", headers=HEADERS,
                            files={"image": ("a.heic", imagekit.heic_header(), "image/heic")})
    assert bad.status_code == 415


def test_savings_need_a_confirmed_price_and_add_up(stack: Stack):
    item = make(stack, "Spanner set", price_paise=125000)
    assert stack.post("/api/v1/savings", {"item_public_id": item["public_id"]}).status_code == 422
    assert stack.post("/api/v1/savings", {"item_public_id": item["public_id"],
                                          "price_paise": 0}).status_code == 422
    assert stack.post("/api/v1/savings", {"price_paise": 100}).status_code == 422
    assert stack.client.get("/api/v1/dashboard").json()["savings"] is None
    first = stack.post("/api/v1/savings", {"item_public_id": item["public_id"],
                                           "price_paise": 124000})
    assert first.status_code == 201
    stack.post("/api/v1/savings", {"item_name": "Phone case", "price_paise": 49900,
                                   "note": "kept the old one"})
    page = stack.client.get("/api/v1/savings").json()
    assert page["total_paise"] == page["month_paise"] == 173900
    assert sum(entry["price_paise"] for entry in page["items"]) == page["total_paise"]
    assert page["items"][1]["item_public_id"] == item["public_id"]
    assert page["items"][1]["item_name"] == "Spanner set"
    savings = stack.client.get("/api/v1/dashboard").json()["savings"]
    assert savings == {"month_paise": 173900, "pill_date": page["items"][0]["local_date"]}


def test_remove_and_undo_a_saving(stack: Stack):
    added = stack.post("/api/v1/savings", {"item_name": "Torch", "price_paise": 30000}).json()
    undo_add = stack.post(f"/api/v1/events/{added['event_id']}/undo")
    assert undo_add.status_code in (200, 204)
    assert stack.client.get("/api/v1/savings").json()["total_paise"] == 0
    again = stack.post("/api/v1/savings", {"item_name": "Torch", "price_paise": 30000}).json()
    removed = stack.client.delete(f"/api/v1/savings/{again['id']}", headers=HEADERS)
    assert removed.status_code == 200
    assert stack.client.delete(f"/api/v1/savings/{again['id']}", headers=HEADERS).status_code == 404
    stack.post(f"/api/v1/events/{removed.json()['event_id']}/undo")
    assert stack.client.get("/api/v1/savings").json()["total_paise"] == 30000


def test_this_month_follows_the_profile_time_zone(stack: Stack):
    stack.client.put("/api/v1/profile", json={"name": "Mohammed", "timezone": ZONE},
                     headers=HEADERS)
    # 31 October 23:00 in Kolkata is still October there, though UTC says 17:30 the same day;
    # 1 November 00:30 in Kolkata is 31 October 19:00 UTC: November there.
    clock.set_now(datetime(2026, 10, 31, 23, 0, tzinfo=ZoneInfo(ZONE)))
    stack.post("/api/v1/savings", {"item_name": "Charger", "price_paise": 50000})
    clock.set_now(datetime(2026, 11, 1, 0, 30, tzinfo=ZoneInfo(ZONE)))
    stack.post("/api/v1/savings", {"item_name": "Cable", "price_paise": 20000})
    month = stack.client.get("/api/v1/savings?period=month").json()
    assert (month["month_paise"], month["total_paise"]) == (20000, 70000)
    assert [entry["local_date"] for entry in month["items"]] == ["2026-11-01"]
    every = stack.client.get("/api/v1/savings?period=all").json()["items"]
    assert [entry["local_date"] for entry in every] == ["2026-11-01", "2026-10-31"]
