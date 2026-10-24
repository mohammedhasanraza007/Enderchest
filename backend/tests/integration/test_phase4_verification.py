"""Phase 4 verification probes (fresh reviewer, docs/reviews/phase-4-verification.md): reconcile
edge cases the build's tests do not cover one by one (F-019, D-104, D-105, DATA_MODEL 2.9)."""

from datetime import timedelta

import pytest

from app import clock
from tests.conftest import HEADERS, Stack
from tests.integration.test_lifecycle import DAY0, centre, day, expiring, item, post, rows, task

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def test_a_snoozed_expiry_reminder_never_hides_the_expiry(stack: Stack):
    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=2))
    [row] = centre(stack)
    assert post(stack, f"/notifications/{row['id']}/snooze", {"option": "week"}).status_code == 200
    day(stack, DAY0 + timedelta(days=3))
    assert [n["kind"] for n in centre(stack)] == ["expired"]
    assert [(r["kind"], r["status"], r["resolution"]) for r in rows(stack)] == [
        ("expiry_soon", "resolved", "superseded"), ("expired", "open", None)]


def test_a_dismissed_finding_stays_closed_through_delete_restore_discard_reactivate(
        stack: Stack):
    day(stack, DAY0)
    public_id = item(stack, "Ladder")
    post(stack, f"/items/{public_id}/inspections", {"result": "worn"})
    [row] = centre(stack)
    post(stack, f"/notifications/{row['id']}/dismiss")
    stack.client.delete(f"/api/v1/items/{public_id}", headers=HEADERS)
    post(stack, f"/items/{public_id}/restore")
    post(stack, f"/items/{public_id}/discard")
    post(stack, f"/items/{public_id}/reactivate")
    day(stack, DAY0 + timedelta(days=1))
    assert centre(stack) == []
    assert [(r["status"], r["resolution"]) for r in rows(stack)] == [("resolved", "dismissed")]


def test_a_date_edit_and_back_reopens_the_same_row(stack: Stack):
    day(stack, DAY0)
    public_id = expiring(stack, DAY0 + timedelta(days=2))
    for value in ("2026-12-01", (DAY0 + timedelta(days=2)).isoformat()):
        stack.client.patch(f"/api/v1/items/{public_id}", json={"expiry_date": value},
                           headers=HEADERS)
    assert len(centre(stack)) == 1 and len(rows(stack)) == 1


def test_a_clock_moved_forward_and_back_makes_no_duplicate(stack: Stack):
    day(stack, DAY0)
    expiring(stack, DAY0 + timedelta(days=10))
    for offset in (0, 8, 0, 8, 12, 8, 12):
        day(stack, DAY0 + timedelta(days=offset))
        centre(stack)
    keys = [r["dedupe_key"] for r in rows(stack)]
    assert len(keys) == len(set(keys)) == 2  # one expiry_soon, one expired
    assert [n["kind"] for n in centre(stack)] == ["expired"]


@pytest.mark.parametrize("mode,next_due", [("fixed", 28), ("from_completion", 24)])
def test_a_task_done_early_moves_per_its_mode(stack: Stack, mode, next_due):
    day(stack, DAY0)
    made = task(stack, interval_days=14, schedule_mode=mode,
                first_due=(DAY0 + timedelta(days=14)).isoformat())
    day(stack, DAY0 + timedelta(days=10))
    done = post(stack, f"/tasks/{made['id']}/done").json()
    assert done["task"]["next_due"] == (DAY0 + timedelta(days=next_due)).isoformat()


def test_undo_of_task_done_is_refused_after_a_later_change(stack: Stack):
    day(stack, DAY0)
    made = task(stack, interval_days=7, first_due=DAY0.isoformat())
    done = post(stack, f"/tasks/{made['id']}/done").json()
    stack.client.patch(f"/api/v1/tasks/{made['id']}", json={"title": "Clean desk"},
                       headers=HEADERS)
    late = post(stack, f"/events/{done['event_id']}/undo")
    assert late.status_code == 409 and late.json()["error"]["details"]["reason"] == "changed"
