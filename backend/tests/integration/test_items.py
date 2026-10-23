"""Items: create, edit, search, delete, undo, Trash, permanent delete, history, labels, lookup
(API 2.5, 2.7; DATA_MODEL 2.6, 2.11, 3.2; D-092). Gates 2, 3 and 4 (the API half)."""

import re
import time
from datetime import UTC, datetime, timedelta

import pytest

from app import clock
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def post(stack: Stack, path: str, body: dict | None = None, **headers):
    return stack.client.post(f"/api/v1{path}", json=body, headers={**HEADERS, **headers})


def create(stack: Stack, **fields) -> dict:
    response = post(stack, "/items", {"name": "Thing", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def get(stack: Stack, public_id: str) -> dict:
    return stack.client.get(f"/api/v1/items/{public_id}").json()


def listing(stack: Stack, query: str = "") -> dict:
    response = stack.client.get(f"/api/v1/items{query}")
    assert response.status_code == 200, response.text
    return response.json()


def problem_fields(response) -> list[str]:
    return [p["field"] for p in response.json()["error"]["details"]["problems"]]


def name_owner(stack: Stack, tz: str = "Asia/Kolkata") -> None:
    stack.client.put("/api/v1/profile", json={"name": "Mo", "timezone": tz}, headers=HEADERS)


# ---- create and read --------------------------------------------------------------------------

def test_a_new_item_gets_a_public_id_and_the_full_detail_shape(stack: Stack):
    body = create(stack, name="  Torque wrench ", quantity=2, price_paise=125000,
                  attributes={"sizes": [8, 10, 12], "brand": " Bosch "}, notes="line 1\nline 2")
    assert re.fullmatch(r"ENDR-[0-9A-HJKMNP-TV-Z]{8}", body["public_id"])
    assert body["name"] == "Torque wrench"
    assert body["attributes"] == {"sizes": [8, 10, 12], "brand": "Bosch"}
    assert body["expiry"] == {"mode": "unknown", "date": None, "status": "unknown",
                              "days_left": None, "word": "date not set"}
    assert body["label"] == {"printed_at": None, "no_label_needed": False}
    assert (body["state"], body["photos"], body["maintenance"]) == ("active", [], None)
    assert get(stack, body["public_id"]) == body


def test_expiry_status_uses_the_owners_local_date(stack: Stack):
    name_owner(stack, "Asia/Kolkata")
    # 20:00 UTC on 22 Oct is already 23 Oct in Kolkata.
    clock.set_now(datetime(2026, 10, 22, 20, 0, tzinfo=UTC))
    today = create(stack, expiry_date="2026-10-23")
    assert today["expiry"]["status"] == "today"
    assert create(stack, expiry_date="2026-10-25")["expiry"]["word"] == "2 days left"
    assert create(stack, expiry_mode="none")["expiry"]["word"] == "no expiry"


@pytest.mark.parametrize("body, field", [
    ({}, "name"),
    ({"name": ""}, "name"),
    ({"name": "x" * 121}, "name"),
    ({"name": "bad\x07"}, "name"),
    ({"name": "A", "quantity": -1}, "quantity"),
    ({"name": "A", "quantity": "2"}, "quantity"),
    ({"name": "A", "price_paise": -5}, "price_paise"),
    ({"name": "A", "expiry_date": "23/10/2026"}, "expiry_date"),
    ({"name": "A", "expiry_date": "2026-02-30"}, "expiry_date"),
    ({"name": "A", "expiry_mode": "date"}, "expiry_date"),
    ({"name": "A", "expiry_mode": "none", "expiry_date": "2026-10-23"}, "expiry_date"),
    ({"name": "A", "notes": "n" * 2001}, "notes"),
    ({"name": "A", "attributes": {"Part No": "x"}}, "attributes"),
    ({"name": "A", "attributes": {"size": ""}}, "attributes"),
    ({"name": "A", "category_id": 999}, "category_id"),
    ({"name": "A", "location_id": 999}, "location_id"),
    ({"name": "A", "state": "used"}, "state"),
])
def test_invalid_items_are_refused_with_the_field_named(stack: Stack, body, field):
    response = post(stack, "/items", body)
    assert response.status_code == 422, response.text
    assert field in problem_fields(response)[0]
    assert listing(stack)["total"] == 0


def test_an_idempotency_key_returns_the_first_item_for_a_repeat(stack: Stack):
    first = post(stack, "/items", {"name": "Once"}, **{"Idempotency-Key": "k-1"})
    again = post(stack, "/items", {"name": "Once"}, **{"Idempotency-Key": "k-1"})
    assert first.status_code == again.status_code == 201
    assert first.json()["public_id"] == again.json()["public_id"]
    assert listing(stack)["total"] == 1


def test_concurrent_creates_with_one_key_make_one_item(stack: Stack):
    from concurrent.futures import ThreadPoolExecutor

    def send(_):
        return post(stack, "/items", {"name": "Double"}, **{"Idempotency-Key": "same"}).json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(send, range(4)))
    assert len({r["public_id"] for r in results}) == 1
    assert listing(stack)["total"] == 1


# ---- edit -------------------------------------------------------------------------------------

def test_an_edit_changes_only_what_was_sent_and_records_the_old_values(stack: Stack):
    made = create(stack, name="Tape", quantity=3, price_paise=5000, expiry_date="2027-01-01")
    response = stack.client.patch(f"/api/v1/items/{made['public_id']}",
                                  json={"name": "Duct tape", "price_paise": None},
                                  headers=HEADERS)
    body = response.json()
    assert (body["name"], body["price_paise"], body["quantity"]) == ("Duct tape", None, 3)
    assert body["expiry"]["date"] == "2027-01-01"
    assert body["public_id"] == made["public_id"]  # the id survives every edit
    events = stack.client.get(f"/api/v1/items/{made['public_id']}/events").json()["items"]
    assert [e["kind"] for e in events] == ["item_updated", "item_created"]
    assert events[0]["payload"] == {"before": {"name": "Tape", "price_paise": 5000}}


def test_switching_expiry_mode_clears_or_requires_the_date(stack: Stack):
    made = create(stack, expiry_date="2027-01-01")
    path = f"/api/v1/items/{made['public_id']}"
    cleared = stack.client.patch(path, json={"expiry_mode": "none"}, headers=HEADERS).json()
    assert cleared["expiry"]["date"] is None
    refused = stack.client.patch(path, json={"expiry_mode": "date"}, headers=HEADERS)
    assert problem_fields(refused) == ["expiry_date"]
    dated = stack.client.patch(path, json={"expiry_date": "2027-02-02"}, headers=HEADERS).json()
    assert dated["expiry"]["mode"] == "date"


def test_state_and_unknown_fields_cannot_be_patched(stack: Stack):
    made = create(stack)
    for body in ({"state": "used"}, {"public_id": "ENDR-00000000"}, {"name": None}):
        response = stack.client.patch(f"/api/v1/items/{made['public_id']}", json=body,
                                      headers=HEADERS)
        assert response.status_code == 422


# ---- delete, undo, Trash, permanent delete ----------------------------------------------------

def test_delete_moves_to_trash_and_undo_brings_it_back(stack: Stack):
    made = create(stack, name="Glue")
    deleted = stack.client.delete(f"/api/v1/items/{made['public_id']}", headers=HEADERS)
    event_id = deleted.json()["event_id"]
    assert listing(stack)["total"] == 0
    assert listing(stack, "?deleted=only&state=all")["items"][0]["public_id"] == made["public_id"]
    assert post(stack, f"/events/{event_id}/undo").json() == {"ok": True}
    assert listing(stack)["total"] == 1
    assert post(stack, f"/events/{event_id}/undo").status_code == 200  # a second click: no change
    kinds = [e["kind"] for e in stack.client.get(
        f"/api/v1/items/{made['public_id']}/events").json()["items"]]
    assert kinds == ["item_restored", "item_deleted", "item_created"]


def test_undo_expires_after_60_seconds(stack: Stack):
    made = create(stack)
    event_id = stack.client.delete(f"/api/v1/items/{made['public_id']}",
                                   headers=HEADERS).json()["event_id"]
    clock.advance(61)
    response = post(stack, f"/events/{event_id}/undo")
    assert (response.status_code, response.json()["error"]["code"]) == (409, "undo_expired")
    assert post(stack, "/events/999999/undo").status_code == 404


def test_restore_from_trash(stack: Stack):
    made = create(stack)
    stack.client.delete(f"/api/v1/items/{made['public_id']}", headers=HEADERS)
    assert get(stack, made["public_id"])["deleted_at"] is not None
    restored = post(stack, f"/items/{made['public_id']}/restore")
    assert restored.status_code == 200 and restored.json()["deleted_at"] is None


def purge(stack: Stack, public_id: str, confirm: str = "DELETE"):
    return stack.client.request("DELETE", f"/api/v1/items/{public_id}/permanent",
                                json={"confirm": confirm}, headers=HEADERS)


def test_permanent_delete_rules(stack: Stack):
    made = create(stack, name="Old battery")
    assert purge(stack, made["public_id"]).json()["error"]["code"] == "not_deleted"
    stack.client.delete(f"/api/v1/items/{made['public_id']}", headers=HEADERS)
    assert purge(stack, made["public_id"], "delete").status_code == 422
    assert purge(stack, made["public_id"]).json()["error"]["code"] == "backup_required"

    assert post(stack, "/backups").status_code == 201
    assert purge(stack, made["public_id"]).status_code == 204
    assert stack.client.get(f"/api/v1/items/{made['public_id']}").status_code == 404
    conn = stack.manager.db()
    events = conn.execute("SELECT kind, payload FROM events").fetchall()
    assert [e["kind"] for e in events] == ["item_purged"]
    assert made["public_id"] in events[0]["payload"] and "Old battery" in events[0]["payload"]


def test_a_backup_older_than_24_hours_is_not_enough(stack: Stack):
    made = create(stack)
    stack.client.delete(f"/api/v1/items/{made['public_id']}", headers=HEADERS)
    post(stack, "/backups")
    clock.set_now(datetime.now(UTC) + timedelta(hours=25))
    assert purge(stack, made["public_id"]).json()["error"]["code"] == "backup_required"


def test_a_purged_public_id_is_never_generated_again(stack: Stack, monkeypatch):
    from app import ids

    made = create(stack)
    stack.client.delete(f"/api/v1/items/{made['public_id']}", headers=HEADERS)
    post(stack, "/backups")
    purge(stack, made["public_id"])
    candidates = iter([made["public_id"], "ENDR-22222222"])
    monkeypatch.setattr(ids, "new_public_id", lambda: next(candidates))
    assert create(stack)["public_id"] == "ENDR-22222222"


# ---- search and filters on items-1000 ---------------------------------------------------------

def load_1000(stack: Stack) -> None:
    name_owner(stack)
    response = post(stack, "/test/fixtures/items-1000")
    assert response.status_code == 200, response.text


def sql_count(stack: Stack, where: str, params: tuple = ()) -> int:
    return stack.manager.db().execute(f"SELECT COUNT(*) FROM items WHERE {where}",
                                      params).fetchone()[0]


def matches(word: str) -> str:
    return f"(name LIKE '%{word}%' OR attributes LIKE '%{word}%' OR public_id LIKE '%{word}%')"


def test_every_filter_matches_a_direct_count_on_items_1000(stack: Stack):
    load_1000(stack)
    today = stack.client.get("/api/v1/test/clock").json()["local_date"]
    soon = (datetime.fromisoformat(today) + timedelta(days=3)).date().isoformat()
    live = "deleted_at IS NULL AND state = 'active'"
    garage = stack.manager.db().execute("SELECT id FROM locations WHERE name = 'Garage'"
                                        ).fetchone()[0]
    tools = stack.manager.db().execute("SELECT id FROM categories WHERE name = 'Tools'"
                                       ).fetchone()[0]
    cases = [
        ("", live, ()),
        ("?state=all", "deleted_at IS NULL", ()),
        ("?state=used", "deleted_at IS NULL AND state = 'used'", ()),
        ("?deleted=only&state=all", "deleted_at IS NOT NULL", ()),
        (f"?category_id={tools}", f"{live} AND category_id = ?", (tools,)),
        (f"?location_id={garage}",
         f"{live} AND location_id IN (SELECT id FROM locations WHERE name IN "
         "('Garage', 'Shelf 1', 'Shelf 2', 'Blue box'))", ()),
        ("?expiry=past", f"{live} AND expiry_date < ?", (today,)),
        ("?expiry=today", f"{live} AND expiry_date = ?", (today,)),
        ("?expiry=soon", f"{live} AND expiry_date > ? AND expiry_date <= ?", (today, soon)),
        ("?expiry=none", f"{live} AND expiry_mode = 'none'", ()),
        ("?expiry=unknown", f"{live} AND expiry_mode = 'unknown'", ()),
        ("?has_photo=false", f"{live} AND primary_photo_id IS NULL", ()),
        ("?has_photo=true", f"{live} AND primary_photo_id IS NOT NULL", ()),
        ("?q=spare%20battery", f"{live} AND {matches('spare')} AND {matches('battery')}", ()),
        ("?q=12", f"{live} AND {matches('12')}", ()),
    ]
    for query, where, params in cases:
        assert listing(stack, query)["total"] == sql_count(stack, where, params), query


def test_paging_walks_every_item_once_in_order(stack: Stack):
    load_1000(stack)
    seen, cursor, pages = [], "", 0
    while True:
        page = listing(stack, f"?sort=name_asc&limit=200{cursor}")
        seen += [entry["name"] for entry in page["items"]]
        pages += 1
        if page["next_cursor"] is None:
            break
        cursor = f"&cursor={page['next_cursor']}"
    assert len(seen) == len(set(seen)) == page["total"]
    assert seen == sorted(seen, key=str.lower) and pages == 5
    assert stack.client.get("/api/v1/items?cursor=garbage").status_code == 422


def test_expiry_sort_puts_dated_items_first(stack: Stack):
    load_1000(stack)
    dates = [e["expiry"]["date"] for e in listing(stack, "?sort=expiry_asc&limit=200")["items"]]
    dated = [d for d in dates if d is not None]
    assert dated == sorted(dated) and dates[: len(dated)] == dated


def test_the_first_page_is_within_the_150_ms_budget(stack: Stack):
    load_1000(stack)
    listing(stack)  # warm up
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        listing(stack)
        timings.append((time.perf_counter() - start) * 1000)
    assert sorted(timings)[2] < 150, timings


# ---- labels and lookup ------------------------------------------------------------------------

def test_the_qr_is_an_svg_of_the_public_id_only(stack: Stack):
    made = create(stack)
    response = stack.client.get(f"/api/v1/items/{made['public_id']}/qr.svg")
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "immutable" in response.headers["cache-control"]
    svg = response.text
    assert svg.startswith("<svg") and "viewBox" in svg and "http" not in svg.split(">", 1)[1]
    assert stack.client.get("/api/v1/items/ENDR-ZZZZZZZZ/qr.svg").status_code == 404


def test_marking_labels_printed_sets_the_date_only_for_live_items(stack: Stack):
    first, second, gone = create(stack), create(stack), create(stack)
    stack.client.delete(f"/api/v1/items/{gone['public_id']}", headers=HEADERS)
    response = post(stack, "/items/label-printed",
                    {"public_ids": [first["public_id"], second["public_id"], gone["public_id"],
                                    "ENDR-ZZZZZZZZ", first["public_id"]]})
    assert response.json() == {"updated": 2}
    assert get(stack, first["public_id"])["label"]["printed_at"] is not None
    assert get(stack, gone["public_id"])["label"]["printed_at"] is None
    assert post(stack, "/items/label-printed", {"public_ids": []}).status_code == 422


def test_lookup_accepts_typed_forms_and_says_when_nothing_matches(stack: Stack):
    made = create(stack, name="Drill")
    body = made["public_id"][5:]
    typed = body.lower().replace("1", "l").replace("0", "o")
    for code in (made["public_id"], f"endr-{body.lower()}", f"ENDR{body}", typed):
        response = stack.client.get(f"/api/v1/lookup/{code}")
        assert response.status_code == 200, code
        assert response.json()["public_id"] == made["public_id"]
    unknown = stack.client.get("/api/v1/lookup/ENDR-ZZZZZZZZ")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["message"] == "No item with that ID."
    assert stack.client.get("/api/v1/lookup/hello").status_code == 404


def test_a_draft_or_a_deleted_item_never_counts(stack: Stack):
    create(stack)
    trashed = create(stack)
    stack.client.delete(f"/api/v1/items/{trashed['public_id']}", headers=HEADERS)
    conn = stack.manager.db()
    conn.execute("INSERT INTO drafts (id, user_id, created_at, updated_at) "
                 "VALUES ('d1', 1, 'x', 'x')")
    assert listing(stack)["total"] == 1
