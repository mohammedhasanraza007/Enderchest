"""Phase 6 verification: independent probes of the ownership check and savings (API 2.14, P-13,
P-14, D-116, D-119). Written by the verifying session; images are drawn in memory (`imagekit`),
regression tools only, never the gate-1 measurement (D-056)."""

import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app import clock
from app.integrations.embedding import model as embedding
from tests import imagekit
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

ZONE = "Asia/Kolkata"


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def make(stack: Stack, name: str, **body) -> dict:
    response = stack.post("/api/v1/items", {"name": name, **body})
    assert response.status_code == 201, response.text
    return response.json()


def check(stack: Stack, text: str | None = None, image=None, name="q.jpg", mime="image/jpeg"):
    files: dict = {"image": (name, image, mime)} if image is not None else {}
    if text is not None:
        files["text"] = (None, text)
    return stack.client.post("/api/v1/ownership/check", files=files, headers=HEADERS)


def save(stack: Stack, body: dict, key: str | None = None):
    headers = {**HEADERS, **({"Idempotency-Key": key} if key else {})}
    return stack.client.post("/api/v1/savings", json=body, headers=headers)


def snapshot(stack: Stack) -> tuple[dict, list]:
    conn = sqlite3.connect(stack.settings.db_path)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        conn.close()
    files = sorted(str(p) for d in (stack.settings.photos_dir, stack.settings.thumbs_dir,
                                    stack.settings.upload_tmp_dir) if d.exists()
                   for p in d.rglob("*"))
    return counts, files


def is_error_shape(response, code: str | None = None) -> bool:
    body = response.json()
    ok = set(body) == {"error"} and {"code", "message"} <= set(body["error"])
    ok = ok and "Traceback" not in response.text
    return ok and (code is None or body["error"]["code"] == code)


# ---- the check -------------------------------------------------------------------------------

def test_failing_and_passing_checks_write_nothing_and_keep_no_file(stack: Stack):
    make(stack, "Tea strainer", attributes={"model": "TS-200"})
    before = snapshot(stack)
    assert check(stack, "tea strainer TS-200").status_code == 200
    assert check(stack, image=imagekit.label_jpeg(["TEA STRAINER TS-200"])).status_code == 200
    assert check(stack, image=imagekit.png_with_alpha(), name="a.png",
                 mime="image/png").status_code == 200
    for bad in (check(stack, image=imagekit.heic_header(), name="a.heic", mime="image/heic"),
                check(stack, image=b"", name="empty.jpg"),
                check(stack, image=imagekit.truncated_jpeg()),
                check(stack, image=b"not an image at all", name="x.jpg"),
                check(stack, image=b"\xff\xd8" + b"0" * (12 * 1024 * 1024 + 10))):
        assert 400 <= bad.status_code < 500, bad.text
        assert is_error_shape(bad)
    assert snapshot(stack) == before


def test_a_json_body_or_no_input_is_a_validation_error(stack: Stack):
    as_json = stack.client.post("/api/v1/ownership/check", json={"text": "mug"}, headers=HEADERS)
    assert as_json.status_code == 422 and is_error_shape(as_json)
    empty = stack.client.post("/api/v1/ownership/check", headers=HEADERS)
    assert empty.status_code == 422 and is_error_shape(empty)
    assert check(stack, "x" * 200).status_code == 200
    assert is_error_shape(check(stack, "x" * 201), "validation_error")


def test_ten_equal_matches_give_five_best_first(stack: Stack):
    made = [make(stack, "Blue mug", attributes={"model": "BM-100"}) for _ in range(10)]
    found = check(stack, "blue mug BM-100").json()["candidates"]
    assert len(found) == 5
    assert [c["public_id"] for c in found] == [m["public_id"] for m in made[:5]]
    assert all(c["level"] == "high" for c in found)


def test_items_that_left_the_shelf_never_qualify(stack: Stack):
    for number, state in enumerate(("use", "mark-expired", "discard"), start=1):
        thing = make(stack, f"Glue {state}", attributes={"model": f"GL-{number}00"})
        words = f"glue {state} GL-{number}00"
        assert check(stack, words).json()["candidates"][0]["public_id"] == thing["public_id"]
        path = f"/api/v1/items/{thing['public_id']}/{state}"
        assert stack.post(path, {"amount": 1} if state == "use" else {}).status_code == 200
        assert check(stack, words).json()["candidates"] == []


def test_a_photo_of_a_hidden_picture_does_not_find_its_item(stack: Stack):
    photo = imagekit.jpeg(colour=(200, 40, 40))
    thing = make(stack, "Red box")
    added = stack.client.post(f"/api/v1/items/{thing['public_id']}/photos", headers=HEADERS,
                              files={"image": ("a.jpg", photo, "image/jpeg")}).json()
    stack.app.state.embedder.tick()
    assert check(stack, image=photo).json()["candidates"] != []
    stack.client.delete(f"/api/v1/photos/{added['id']}", headers=HEADERS)
    assert check(stack, image=photo).json()["candidates"] == []


def test_an_unreadable_photo_file_is_marked_once_and_never_retried(stack: Stack):
    thing = make(stack, "Lamp")
    added = stack.client.post(f"/api/v1/items/{thing['public_id']}/photos", headers=HEADERS,
                              files={"image": ("a.jpg", imagekit.jpeg(), "image/jpeg")}).json()
    conn = sqlite3.connect(stack.settings.db_path)
    path = conn.execute("SELECT path FROM photos WHERE id = ?", (added["id"],)).fetchone()[0]
    conn.close()
    (stack.settings.photos_dir / path).write_bytes(b"broken")
    assert stack.app.state.embedder.tick() == 1
    assert stack.app.state.embedder.tick() == 0
    conn = sqlite3.connect(stack.settings.db_path)
    row = conn.execute("SELECT length(embedding), embedding_model FROM photos").fetchone()
    conn.close()
    assert row == (0, embedding.MODEL_NAME)
    assert check(stack, image=imagekit.jpeg()).status_code == 200


def test_a_new_model_name_embeds_every_photo_again(stack: Stack, monkeypatch):
    thing = make(stack, "Lamp")
    for _ in range(2):
        stack.client.post(f"/api/v1/items/{thing['public_id']}/photos", headers=HEADERS,
                          files={"image": ("a.jpg", imagekit.jpeg(), "image/jpeg")})
    assert stack.app.state.embedder.tick() == 2
    monkeypatch.setattr(embedding, "MODEL_NAME", "another-model")
    assert stack.app.state.embedder.tick() == 2
    assert stack.app.state.embedder.tick() == 0


def test_a_draft_photo_is_embedded_but_never_a_candidate(stack: Stack):
    photo = imagekit.jpeg(colour=(20, 160, 60))
    drafts = stack.client.post("/api/v1/drafts", headers=HEADERS,
                               files=[("images[]", ("a.jpg", photo, "image/jpeg"))])
    assert drafts.status_code == 201, drafts.text
    assert stack.app.state.embedder.tick() == 1
    assert check(stack, image=photo).json()["candidates"] == []


# ---- savings ---------------------------------------------------------------------------------

@pytest.mark.parametrize("price", ["100", 10.5, 10.0, 0, -5, True, None, 10**12 + 1, 10**30])
def test_a_saving_needs_a_positive_whole_number_of_paise(stack: Stack, price):
    response = save(stack, {"item_name": "Torch", "price_paise": price})
    assert response.status_code == 422 and is_error_shape(response, "validation_error")
    assert stack.client.get("/api/v1/savings?period=all").json()["items"] == []


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_a_saving_needs_a_real_name(stack: Stack, name):
    response = save(stack, {"item_name": name, "price_paise": 100})
    assert response.status_code == 422 and is_error_shape(response)


def test_a_saving_on_an_item_takes_the_items_name_and_refuses_trash(stack: Stack):
    thing = make(stack, "Spanner set")
    first = save(stack, {"item_public_id": thing["public_id"], "item_name": "Something else",
                         "price_paise": 100})
    assert first.status_code == 201
    listed = stack.client.get("/api/v1/savings").json()["items"][0]
    assert (listed["item_name"], listed["item_public_id"]) == ("Spanner set", thing["public_id"])
    assert is_error_shape(save(stack, {"item_public_id": "ENDR-ZZZZZZZZ", "price_paise": 1}),
                          "not_found")
    stack.client.delete(f"/api/v1/items/{thing['public_id']}", headers=HEADERS)
    refused = save(stack, {"item_public_id": thing["public_id"], "price_paise": 100})
    assert refused.status_code == 404 and is_error_shape(refused, "not_found")
    # The earlier saving stays, by its snapshot name, with no link to an item in Trash.
    listed = stack.client.get("/api/v1/savings").json()["items"]
    assert [(s["item_name"], s["item_public_id"]) for s in listed] == [("Spanner set", None)]


def test_a_purged_item_keeps_its_savings_by_name(stack: Stack):
    thing = make(stack, "Old drill")
    assert save(stack, {"item_public_id": thing["public_id"], "price_paise": 5000}).status_code \
        == 201
    stack.client.delete(f"/api/v1/items/{thing['public_id']}", headers=HEADERS)
    assert stack.post("/api/v1/backups").status_code in (200, 201, 202)
    purged = stack.client.request("DELETE", f"/api/v1/items/{thing['public_id']}/permanent",
                                  json={"confirm": "DELETE"}, headers=HEADERS)
    assert purged.status_code == 204, purged.text
    page = stack.client.get("/api/v1/savings").json()
    assert page["total_paise"] == 5000
    assert [(s["item_name"], s["item_public_id"]) for s in page["items"]] == [("Old drill", None)]


def test_the_same_idempotency_key_records_one_saving(stack: Stack):
    body = {"item_name": "Cable", "price_paise": 20000}
    first, again = save(stack, body, "key-1"), save(stack, body, "key-1")
    assert first.json() == again.json()
    assert save(stack, body, "key-2").json()["id"] != first.json()["id"]
    assert stack.client.get("/api/v1/savings").json()["total_paise"] == 40000


def test_totals_equal_the_list_across_pages(stack: Stack):
    for price in (100, 250, 999, 12345, 7):
        save(stack, {"item_name": "Thing", "price_paise": price})
    removed = save(stack, {"item_name": "Gone", "price_paise": 5000}).json()
    stack.client.delete(f"/api/v1/savings/{removed['id']}", headers=HEADERS)
    seen, cursor = [], None
    while True:
        query = "/api/v1/savings?period=all&limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = stack.client.get(query).json()
        seen += page["items"]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == 5 and sum(s["price_paise"] for s in seen) == page["total_paise"] == 13701


@pytest.mark.parametrize("query", ["period=week", "limit=0", "limit=201", "cursor=%%%"])
def test_bad_listing_queries_are_refused_in_the_error_shape(stack: Stack, query):
    response = stack.client.get(f"/api/v1/savings?{query}")
    assert response.status_code == 422 and is_error_shape(response)


def test_removing_unknown_savings(stack: Stack):
    assert is_error_shape(stack.client.delete("/api/v1/savings/999", headers=HEADERS),
                          "not_found")
    assert stack.client.delete("/api/v1/savings/abc", headers=HEADERS).status_code == 422


def test_undo_works_once_within_a_minute_and_is_refused_after(stack: Stack):
    clock.set_now(datetime(2026, 10, 20, 12, 0, tzinfo=ZoneInfo("UTC")))
    added = save(stack, {"item_name": "Torch", "price_paise": 30000}).json()
    clock.advance(59)
    assert stack.post(f"/api/v1/events/{added['event_id']}/undo").status_code in (200, 204)
    assert stack.post(f"/api/v1/events/{added['event_id']}/undo").status_code in (200, 204)
    assert stack.client.get("/api/v1/savings").json()["total_paise"] == 0
    kept = save(stack, {"item_name": "Torch", "price_paise": 30000}).json()
    removed = stack.client.delete(f"/api/v1/savings/{kept['id']}", headers=HEADERS).json()
    clock.advance(61)
    late = stack.post(f"/api/v1/events/{removed['event_id']}/undo")
    assert late.status_code == 409 and is_error_shape(late, "undo_expired")
    assert stack.client.get("/api/v1/savings").json()["total_paise"] == 0
    conn = sqlite3.connect(stack.settings.db_path)
    kinds = [r[0] for r in conn.execute("SELECT kind FROM events ORDER BY id")]
    conn.close()
    assert kinds == ["saving_added", "saving_undone", "saving_added", "saving_removed"]


def test_the_pill_date_follows_the_latest_live_saving(stack: Stack):
    stack.client.put("/api/v1/profile", json={"name": "Mohammed", "timezone": ZONE},
                     headers=HEADERS)
    day = datetime(2026, 10, 20, 10, 0, tzinfo=ZoneInfo(ZONE))
    clock.set_now(day)
    save(stack, {"item_name": "Charger", "price_paise": 50000})
    clock.set_now(day + timedelta(days=2))
    later = save(stack, {"item_name": "Cable", "price_paise": 20000}).json()
    board = stack.client.get("/api/v1/dashboard").json()
    assert board["savings"] == {"month_paise": 70000, "pill_date": "2026-10-22"}
    assert board["road"]["start"] == "2026-10-22"
    stack.client.delete(f"/api/v1/savings/{later['id']}", headers=HEADERS)
    board = stack.client.get("/api/v1/dashboard").json()
    assert board["savings"] == {"month_paise": 50000, "pill_date": "2026-10-20"}
    # The clock put back before the latest saving: its date is in the future, never today.
    clock.set_now(day - timedelta(days=1))
    board = stack.client.get("/api/v1/dashboard").json()
    assert board["savings"]["pill_date"] != board["road"]["start"]
