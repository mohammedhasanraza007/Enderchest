"""Phase 4: lifecycle, tasks, maintenance, inspections and the reconciled notifications
(API 2.10 to 2.12; DATA_MODEL 2.9, 2.10, 2.12, 3.8; D-103 to D-107). Gates 1 to 7 on the test
clock; restarts are new app instances on the same folders."""

import json
from datetime import date, timedelta

import pytest

from app import clock
from app.config import Settings
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

DAY0 = date(2026, 10, 20)


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def day(stack: Stack, value: date) -> None:
    """Move the test clock to noon of `value` in the owner's zone (the /test/clock endpoint)."""
    response = stack.post("/api/v1/test/clock", {"local_date": value.isoformat()})
    assert response.status_code == 200, response.text


def post(stack: Stack, path: str, body: dict | None = None):
    return stack.client.post(f"/api/v1{path}", json=body, headers=HEADERS)


def item(stack: Stack, name: str = "Oat milk", **fields) -> str:
    response = post(stack, "/items", {"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()["public_id"]


def expiring(stack: Stack, on: date, name: str = "Oat milk", quantity: int = 1) -> str:
    return item(stack, name, expiry_mode="date", expiry_date=on.isoformat(), quantity=quantity)


def task(stack: Stack, **fields) -> dict:
    response = post(stack, "/tasks", {"title": "Clean PC", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def rows(stack: Stack) -> list[dict]:
    """Every notification row, straight from the table."""
    conn = stack.manager.db()
    return [dict(r) for r in conn.execute(
        "SELECT id, kind, item_id, task_id, due_date, dedupe_key, status, snoozed_until, "
        "resolution, os_notified_at FROM notifications ORDER BY id")]


def centre(stack: Stack, status: str = "open") -> list[dict]:
    response = stack.client.get(f"/api/v1/notifications?status={status}")
    assert response.status_code == 200, response.text
    return response.json()["items"]


def restart(settings: Settings) -> Stack:
    """A new app on the same folders; its reconciler's first tick is the start-up reconcile."""
    stack = Stack(settings).__enter__()
    assert stack.app.state.reconciler.tick() is True
    return stack


# ---- gate 1: one expiry_soon, through restarts and day by day ---------------------------------

def test_an_item_expiring_soon_has_exactly_one_reminder_through_restarts(settings: Settings):
    stack = restart(settings)
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=3))
    assert [n["word"] for n in centre(stack)] == ["3 days left"]
    stack.__exit__(None, None, None)
    for _ in range(3):  # restart three times on the same day
        stack = restart(settings)
        stack.__exit__(None, None, None)
    words = []
    for offset in range(1, 4):  # then a day at a time, restarting each day
        stack = restart(settings)
        day(stack, DAY0 + timedelta(days=offset))
        assert stack.app.state.reconciler.tick() is True  # the date moved: reconcile again
        words.append([n["word"] for n in centre(stack)])
        stack.__exit__(None, None, None)
    assert words == [["2 days left"], ["1 day left"], ["expires today"]]
    stack = restart(settings)
    day(stack, DAY0 + timedelta(days=3))
    soon = [r for r in rows(stack) if r["kind"] == "expiry_soon"]
    assert len(soon) == 1 and soon[0]["status"] == "open"
    assert stack.client.get(f"/api/v1/items/{public_id}").json()["expiry"]["word"] == (
        "expires today")
    stack.__exit__(None, None, None)


def test_running_the_reconcile_twice_changes_nothing(stack: Stack):
    from app.services.notifications import reconcile

    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=1))
    expiring(stack, DAY0 - timedelta(days=2), "Old yogurt")
    task(stack, first_due=DAY0.isoformat())
    before = rows(stack)
    assert reconcile(stack.manager.db(), 1) == {"inserted": 0, "reopened": 0, "woken": 0,
                                                "superseded": 0}
    assert rows(stack) == before and len(before) == 3


# ---- gate 2: expired while the app was off ----------------------------------------------------

def test_an_item_that_expired_while_the_app_was_off_is_expired_after_start(settings: Settings):
    stack = restart(settings)
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=2))
    assert [r["kind"] for r in rows(stack)] == ["expiry_soon"]
    stack.__exit__(None, None, None)
    clock.advance(5 * 86400)  # the laptop was off for five days
    stack = restart(settings)
    by_kind = {r["kind"]: r for r in rows(stack)}
    assert by_kind["expiry_soon"]["status"] == "resolved"
    assert by_kind["expiry_soon"]["resolution"] == "superseded"
    assert by_kind["expired"]["status"] == "open"
    assert stack.client.get(f"/api/v1/items/{public_id}").json()["expiry"]["status"] == "expired"
    [row] = centre(stack)
    assert (row["kind"], row["word"], row["urgency"]) == ("expired", "expired", "overdue")
    assert [a["key"] for a in row["actions"]] == ["mark_expired", "snooze", "use", "discard"]
    stack.__exit__(None, None, None)


# ---- gate 3: a 14-day task, both modes; 30 days late is one row -------------------------------

@pytest.mark.parametrize("mode, late_days, next_due", [
    ("from_completion", 0, DAY0 + timedelta(days=28)),
    ("from_completion", 3, DAY0 + timedelta(days=31)),
    ("fixed", 3, DAY0 + timedelta(days=28)),
])
def test_a_14_day_task_becomes_due_completes_and_reschedules(stack: Stack, mode, late_days,
                                                              next_due):
    day(stack, DAY0)
    made = task(stack, interval_days=14, schedule_mode=mode,
                first_due=(DAY0 + timedelta(days=14)).isoformat())
    day(stack, DAY0 + timedelta(days=13))
    assert centre(stack) == []
    day(stack, DAY0 + timedelta(days=14))
    [row] = centre(stack)
    assert (row["kind"], row["word"], row["task"]["title"]) == ("task_due", "due today", "Clean PC")
    day(stack, DAY0 + timedelta(days=14 + late_days))
    done = post(stack, f"/tasks/{made['id']}/done")
    assert done.status_code == 200, done.text
    assert done.json()["task"]["next_due"] == next_due.isoformat()
    assert done.json()["task"]["last_done"] == (DAY0 + timedelta(days=14 + late_days)).isoformat()
    assert centre(stack) == []
    assert [r["resolution"] for r in rows(stack)] == ["done"]


def test_a_task_30_days_late_makes_one_reminder_not_two(stack: Stack):
    day(stack, DAY0)
    task(stack, interval_days=14, first_due=DAY0.isoformat())
    for offset in range(0, 31, 5):
        day(stack, DAY0 + timedelta(days=offset))
        assert len(centre(stack)) == 1
    assert len(rows(stack)) == 1
    assert centre(stack)[0]["word"] == "30 days overdue"


def test_a_one_off_task_switches_off_when_done_and_skip_moves_without_last_done(stack: Stack):
    day(stack, DAY0)
    one_off = task(stack, first_due=DAY0.isoformat())
    finished = post(stack, f"/tasks/{one_off['id']}/done").json()["task"]
    assert (finished["enabled"], finished["word"]) == (False, "done 20 Oct")
    repeat = task(stack, title="Water plants", interval_days=7, first_due=DAY0.isoformat())
    skipped = post(stack, f"/tasks/{repeat['id']}/skip").json()["task"]
    assert (skipped["next_due"], skipped["last_done"]) == (
        (DAY0 + timedelta(days=7)).isoformat(), None)
    assert {r["resolution"] for r in rows(stack)} == {"done", "skipped"}
    refused = post(stack, f"/tasks/{one_off['id']}/done")
    assert refused.status_code == 409 and refused.json()["error"]["details"]["reason"] == (
        "disabled")


# ---- gate 4: use it, and undo -----------------------------------------------------------------

def test_use_on_three_leaves_two_and_on_one_resolves_and_undo_restores(stack: Stack):
    day(stack, DAY0)
    three = expiring(stack, DAY0 + timedelta(days=1), "Yogurt", quantity=3)
    used = post(stack, f"/items/{three}/use")
    assert used.status_code == 200, used.text
    assert (used.json()["item"]["quantity"], used.json()["item"]["state"]) == (2, "active")
    assert [n["item"]["public_id"] for n in centre(stack)] == [three]  # still needs the owner

    one = expiring(stack, DAY0 + timedelta(days=2), "Spinach")
    used = post(stack, f"/items/{one}/use")
    assert (used.json()["item"]["quantity"], used.json()["item"]["state"]) == (0, "used")
    spinach = [r for r in rows(stack) if r["due_date"] == (DAY0 + timedelta(days=2)).isoformat()]
    assert [(r["status"], r["resolution"]) for r in spinach] == [("resolved", "used")]

    undone = post(stack, f"/events/{used.json()['event_id']}/undo")
    assert undone.status_code == 200, undone.text
    back = stack.client.get(f"/api/v1/items/{one}").json()
    assert (back["quantity"], back["state"]) == (1, "active")
    spinach = [r for r in rows(stack) if r["due_date"] == (DAY0 + timedelta(days=2)).isoformat()]
    assert [(r["status"], r["resolution"]) for r in spinach] == [("open", None)]
    assert len(rows(stack)) == 2  # the same row came back, no new one
    assert post(stack, f"/events/{used.json()['event_id']}/undo").status_code == 200  # twice: no-op


def test_use_more_than_the_quantity_is_refused_and_inactive_items_cannot_be_used(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack, quantity=2)
    refused = post(stack, f"/items/{public_id}/use", {"amount": 3})
    assert refused.status_code == 422
    assert refused.json()["error"]["details"]["problems"][0]["field"] == "amount"
    assert post(stack, f"/items/{public_id}/discard").status_code == 200
    again = post(stack, f"/items/{public_id}/use")
    assert again.status_code == 409 and again.json()["error"]["details"]["reason"] == "not_active"


def test_mark_expired_discard_reactivate_and_their_undo(stack: Stack):
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 - timedelta(days=1), quantity=4)
    marked = post(stack, f"/items/{public_id}/mark-expired").json()
    assert (marked["item"]["state"], marked["item"]["quantity"]) == ("expired", 4)
    assert [r["resolution"] for r in rows(stack)] == ["expired_marked"]
    assert post(stack, f"/events/{marked['event_id']}/undo").status_code == 200
    assert [r["status"] for r in rows(stack)] == ["open"]
    discarded = post(stack, f"/items/{public_id}/discard").json()
    assert discarded["item"]["state"] == "discarded"
    assert [r["resolution"] for r in rows(stack)] == ["discarded"]
    back = post(stack, f"/items/{public_id}/reactivate")
    assert back.status_code == 200 and (back.json()["state"], back.json()["quantity"]) == (
        "active", 4)
    assert post(stack, f"/items/{public_id}/reactivate").status_code == 409
    # The discard's undo is refused now: the item changed after it.
    late = post(stack, f"/events/{discarded['event_id']}/undo")
    assert late.status_code == 409 and late.json()["error"]["details"]["reason"] == "changed"


def test_undo_after_60_seconds_is_refused(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack)
    event_id = post(stack, f"/items/{public_id}/use").json()["event_id"]
    clock.advance(61)
    refused = post(stack, f"/events/{event_id}/undo")
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "undo_expired"


# ---- gate 5: snooze ---------------------------------------------------------------------------

def test_snooze_cannot_push_an_expiry_reminder_past_its_date_and_returns_when_due(stack: Stack):
    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=2))
    [row] = centre(stack)
    snoozed = post(stack, f"/notifications/{row['id']}/snooze", {"option": "week"})
    assert snoozed.status_code == 200, snoozed.text
    assert snoozed.json()["snoozed_until"] == (DAY0 + timedelta(days=2)).isoformat()
    assert centre(stack) == [] and len(centre(stack, "snoozed")) == 1
    day(stack, DAY0 + timedelta(days=1))
    assert centre(stack) == []
    day(stack, DAY0 + timedelta(days=2))
    [back] = centre(stack)
    assert (back["word"], back["status"]) == ("expires today", "open")
    assert [a["key"] for a in back["actions"]] == ["use"]  # nothing left to snooze to
    refused = post(stack, f"/notifications/{back['id']}/snooze", {"option": "tomorrow"})
    assert refused.status_code == 409
    assert refused.json()["error"]["details"]["reason"] == "cannot_snooze"


def test_a_snoozed_task_returns_after_its_snooze(stack: Stack):
    day(stack, DAY0)
    task(stack, first_due=DAY0.isoformat())
    [row] = centre(stack)
    assert post(stack, f"/notifications/{row['id']}/snooze",
                {"option": "3days"}).json()["snoozed_until"] == "2026-10-23"
    day(stack, DAY0 + timedelta(days=2))
    assert centre(stack) == []
    day(stack, DAY0 + timedelta(days=3))
    assert [n["word"] for n in centre(stack)] == ["3 days overdue"]


# ---- gate 6: maintenance and inspections ------------------------------------------------------

def test_maintenance_toggle_and_an_ok_inspection_completes_the_task(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack, "Angle grinder")
    made = stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                            json={"enabled": True, "interval_days": 30,
                                  "first_due": DAY0.isoformat()}, headers=HEADERS)
    assert made.status_code == 200, made.text
    assert (made.json()["title"], made.json()["kind"]) == ("Inspect Angle grinder", "maintenance")
    detail = stack.client.get(f"/api/v1/items/{public_id}").json()
    assert detail["maintenance"] == {"task_id": made.json()["id"], "enabled": True,
                                     "interval_days": 30, "next_due": "2026-10-20",
                                     "last_done": None, "source": "user"}
    [row] = centre(stack)
    assert (row["kind"], row["word"]) == ("inspection_due", "inspect")
    assert [a["key"] for a in row["actions"]] == ["inspect", "snooze", "skip", "discard"]
    done = post(stack, f"/items/{public_id}/inspections", {"result": "ok", "note": "Fine"})
    assert done.status_code == 201, done.text
    assert done.json()["task"]["next_due"] == (DAY0 + timedelta(days=30)).isoformat()
    assert centre(stack) == [] and rows(stack)[0]["resolution"] == "inspected"
    off = stack.client.put(f"/api/v1/items/{public_id}/maintenance", json={"enabled": False},
                           headers=HEADERS)
    assert off.json()["enabled"] is False
    listed = stack.client.get(f"/api/v1/items/{public_id}/inspections").json()["items"]
    assert [(i["result"], i["note"]) for i in listed] == [("ok", "Fine")]


@pytest.mark.parametrize("result", ["worn", "defective"])
def test_worn_and_defective_raise_a_finding_that_offers_mark_discarded(stack: Stack, result):
    day(stack, DAY0)
    public_id = item(stack, "Blade")
    found = post(stack, f"/items/{public_id}/inspections", {"result": result})
    assert found.status_code == 201 and found.json()["task"] is None
    assert stack.client.get(f"/api/v1/items/{public_id}").json()["state"] == "active"
    [row] = centre(stack)
    assert row["kind"] == "inspection_finding"
    assert row["word"] == f"inspection suggested: {result}"
    assert "replace" not in row["word"]
    assert [(a["key"], a["label"]) for a in row["actions"]] == [
        ("discard", "Mark discarded"), ("keep", "Keep using")]
    assert post(stack, f"/items/{public_id}/discard").status_code == 200
    assert centre(stack) == [] and rows(stack)[0]["resolution"] == "discarded"


def test_keep_using_dismisses_a_finding_for_good_and_an_ok_inspection_supersedes_it(
        stack: Stack):
    from app.services.notifications import reconcile

    day(stack, DAY0)
    kept = item(stack, "Ladder")
    post(stack, f"/items/{kept}/inspections", {"result": "worn"})
    [row] = centre(stack)
    closed = post(stack, f"/notifications/{row['id']}/dismiss")
    assert closed.status_code == 200 and closed.json()["resolution"] == "dismissed"
    reconcile(stack.manager.db(), 1)
    assert centre(stack) == []  # still the latest inspection, but the owner closed it
    fixed = item(stack, "Kettle")
    post(stack, f"/items/{fixed}/inspections", {"result": "defective"})
    post(stack, f"/items/{fixed}/inspections", {"result": "ok"})
    assert centre(stack) == []
    assert rows(stack)[-1]["resolution"] == "superseded"
    refused = post(stack, f"/notifications/{rows(stack)[-1]['id']}/dismiss")
    assert refused.status_code == 200  # already resolved: nothing changes
    task(stack, first_due=DAY0.isoformat())
    task_row = centre(stack)[0]
    assert post(stack, f"/notifications/{task_row['id']}/dismiss").status_code == 409


def test_an_inspection_photo_must_be_the_items_own(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack)
    refused = post(stack, f"/items/{public_id}/inspections",
                   {"result": "ok", "photo_id": "00000000-0000-4000-8000-000000000000"})
    assert refused.status_code == 422
    assert refused.json()["error"]["details"]["problems"][0]["field"] == "photo_id"


def test_gemini_interval_is_offered_as_a_suggestion_until_confirmed(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack, "Drill")
    conn = stack.manager.db()
    item_id = conn.execute("SELECT id FROM items WHERE public_id = ?", (public_id,)).fetchone()[0]
    conn.execute(
        "INSERT INTO drafts (id, user_id, status, gemini_status, gemini_result, created_at, "
        "updated_at, committed_item_id) VALUES ('d1', 1, 'committed', 'done', ?, ?, ?, ?)",
        (json.dumps({"values": {"inspection_interval_days": 90}}), "2026-10-20T00:00:00Z",
         "2026-10-20T00:00:00Z", item_id))
    detail = stack.client.get(f"/api/v1/items/{public_id}").json()
    assert (detail["maintenance"], detail["maintenance_suggestion"]) == (None,
                                                                         {"interval_days": 90})
    made = stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                            json={"enabled": True, "interval_days": 90, "source": "gemini"},
                            headers=HEADERS).json()
    assert (made["source"], made["next_due"]) == ("gemini", "2027-01-18")
    confirmed = stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                                 json={"enabled": True, "source": "user"}, headers=HEADERS)
    assert confirmed.json()["source"] == "user"
    edited = stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                              json={"enabled": True, "source": "gemini"}, headers=HEADERS)
    changed = stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                               json={"enabled": True, "interval_days": 60}, headers=HEADERS)
    assert (edited.json()["source"], changed.json()["source"]) == ("gemini", "user")


# ---- gate 7: delete or discard resolves -------------------------------------------------------

def test_deleting_supersedes_and_restoring_brings_the_reminder_back(stack: Stack):
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=1))
    stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                     json={"enabled": True, "interval_days": 7, "first_due": DAY0.isoformat()},
                     headers=HEADERS)
    assert len(centre(stack)) == 2
    deleted = stack.client.delete(f"/api/v1/items/{public_id}", headers=HEADERS)
    assert deleted.status_code == 200
    assert centre(stack) == []
    assert {(r["status"], r["resolution"]) for r in rows(stack)} == {("resolved", "superseded")}
    assert post(stack, f"/items/{public_id}/restore").status_code == 200
    assert len(centre(stack)) == 2 and len(rows(stack)) == 2


def test_editing_the_expiry_date_supersedes_the_old_reminder(stack: Stack):
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=1))
    stack.client.patch(f"/api/v1/items/{public_id}", json={"expiry_date": "2026-12-01"},
                       headers=HEADERS)
    assert centre(stack) == [] and rows(stack)[0]["resolution"] == "superseded"


def test_permanent_delete_removes_the_items_tasks_inspections_and_reminders(stack: Stack):
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=1))
    stack.client.put(f"/api/v1/items/{public_id}/maintenance",
                     json={"enabled": True, "interval_days": 7}, headers=HEADERS)
    post(stack, f"/items/{public_id}/inspections", {"result": "worn"})
    chore = task(stack, item_public_id=public_id, first_due=DAY0.isoformat())
    stack.client.delete(f"/api/v1/items/{public_id}", headers=HEADERS)
    assert post(stack, "/backups").status_code in (200, 201)
    purged = stack.client.request("DELETE", f"/api/v1/items/{public_id}/permanent",
                                  json={"confirm": "DELETE"}, headers=HEADERS)
    assert purged.status_code == 204, purged.text
    conn = stack.manager.db()
    assert conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM notifications WHERE item_id IS NOT NULL"
                        ).fetchone()[0] == 0
    left = stack.client.get("/api/v1/tasks?scope=all").json()["items"]
    assert [(t["id"], t["item"]) for t in left] == [(chore["id"], None)]
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


# ---- tasks API --------------------------------------------------------------------------------

def test_task_scopes_edits_delete_and_undo(stack: Stack):
    day(stack, DAY0)
    soon = task(stack, title="Soon", first_due=(DAY0 + timedelta(days=7)).isoformat())
    later = task(stack, title="Later", interval_days=30,
                 first_due=(DAY0 + timedelta(days=8)).isoformat())
    off = task(stack, title="Off", first_due=DAY0.isoformat(), enabled=False)
    titles = {scope: [t["title"] for t in stack.client.get(
        f"/api/v1/tasks?scope={scope}").json()["items"]] for scope in ("open", "due", "all")}
    assert titles == {"open": ["Soon", "Later"], "due": ["Soon"], "all": ["Off", "Soon", "Later"]}
    assert centre(stack) == []  # a switched-off task never reminds
    edited = stack.client.patch(f"/api/v1/tasks/{later['id']}",
                                json={"next_due": DAY0.isoformat(), "interval_days": None},
                                headers=HEADERS).json()
    assert (edited["next_due"], edited["interval_days"], edited["word"]) == (
        DAY0.isoformat(), None, "due today")
    assert [n["task"]["title"] for n in centre(stack)] == ["Later"]
    removed = stack.client.delete(f"/api/v1/tasks/{later['id']}", headers=HEADERS)
    assert centre(stack) == []
    assert post(stack, f"/events/{removed.json()['event_id']}/undo").status_code == 200
    assert [n["task"]["title"] for n in centre(stack)] == ["Later"]
    done = post(stack, f"/tasks/{soon['id']}/done").json()
    assert [t["title"] for t in stack.client.get("/api/v1/tasks?scope=done").json()["items"]] == [
        "Soon"]
    assert post(stack, f"/events/{done['event_id']}/undo").status_code == 200
    back = stack.client.get("/api/v1/tasks?scope=all").json()["items"]
    assert [(t["title"], t["enabled"], t["last_done"]) for t in back if t["title"] == "Soon"] == [
        ("Soon", True, None)]
    assert off["word"] == "off"


@pytest.mark.parametrize("body, field", [
    ({"title": "", "first_due": "2026-10-20"}, "title"),
    ({"title": "A", "first_due": "20/10/2026"}, "first_due"),
    ({"title": "A"}, "first_due"),
    ({"title": "A", "first_due": "2026-10-20", "interval_days": 0}, "interval_days"),
    ({"title": "A", "first_due": "2026-10-20", "item_public_id": "ENDR-7K2M9QXA"},
     "item_public_id"),
    ({"title": "A", "first_due": "2026-10-20", "kind": "maintenance"}, "item_public_id"),
])
def test_task_create_refusals_name_the_field(stack: Stack, body, field):
    refused = post(stack, "/tasks", body)
    assert refused.status_code == 422, refused.text
    assert field in [p["field"] for p in refused.json()["error"]["details"]["problems"]]


def test_a_second_maintenance_task_for_an_item_is_refused(stack: Stack):
    day(stack, DAY0)
    public_id = item(stack)
    task(stack, kind="maintenance", item_public_id=public_id, first_due=DAY0.isoformat())
    refused = post(stack, "/tasks", {"title": "Again", "kind": "maintenance",
                                     "item_public_id": public_id, "first_due": "2026-10-21"})
    assert refused.status_code == 409
    assert refused.json()["error"]["details"]["reason"] == "has_maintenance"


def test_task_create_is_idempotent_with_a_key(stack: Stack):
    body = {"title": "Once", "first_due": "2026-10-20"}
    first = stack.client.post("/api/v1/tasks", json=body,
                              headers={**HEADERS, "Idempotency-Key": "k-1"})
    second = stack.client.post("/api/v1/tasks", json=body,
                               headers={**HEADERS, "Idempotency-Key": "k-1"})
    assert first.json() == second.json()
    assert len(stack.client.get("/api/v1/tasks").json()["items"]) == 1


# ---- the bell, read and the browser-alert claim -----------------------------------------------

def test_count_read_and_the_browser_alert_is_claimed_once(stack: Stack):
    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=1))
    task(stack, first_due=DAY0.isoformat())
    count = stack.client.get("/api/v1/notifications/count").json()
    assert (count["open"], count["unread"], len(count["unshown"])) == (2, 2, 2)
    first_id = count["unshown"][0]["id"]
    assert post(stack, f"/notifications/{first_id}/shown").json() == {"claimed": True}
    assert post(stack, f"/notifications/{first_id}/shown").json() == {"claimed": False}
    assert [n["id"] for n in stack.client.get(
        "/api/v1/notifications/count").json()["unshown"]] != [first_id]
    assert post(stack, f"/notifications/{first_id}/read").status_code == 204
    assert stack.client.get("/api/v1/notifications/count").json()["unread"] == 1
    assert post(stack, "/notifications/read-all").json() == {"updated": 1}
    assert stack.client.get("/api/v1/notifications/count").json()["unread"] == 0
    assert post(stack, "/notifications/999/shown").status_code == 404


def test_lead_days_change_reconciles_at_once(stack: Stack):
    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=6))
    assert centre(stack) == []
    stack.client.patch("/api/v1/settings", json={"lead_days": 7}, headers=HEADERS)
    assert [n["word"] for n in centre(stack)] == ["6 days left"]
