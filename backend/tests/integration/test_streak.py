"""Phase 8: the dashboard's streak through the API (DATA_MODEL 3.7, D-127): actions count, undone
ones do not, days with nothing due are skipped, a missed due day ends it."""

from datetime import date, timedelta

import pytest

from app import clock
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

DAY = date(2026, 10, 16)


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def post(stack: Stack, path: str, body: dict | None = None) -> dict:
    response = stack.client.post(f"/api/v1{path}", json=body, headers=HEADERS)
    assert response.status_code in (200, 201), response.text
    return response.json()


def on(stack: Stack, offset: int) -> None:
    post(stack, "/test/clock", {"local_date": (DAY + timedelta(days=offset)).isoformat()})


def streak(stack: Stack) -> int:
    response = stack.client.get("/api/v1/dashboard")
    assert response.status_code == 200, response.text
    return response.json()["streak"]["days"]


def expiring(stack: Stack, name: str, offset: int) -> str:
    """An item expiring `offset` days after DAY, so a reminder is due from today."""
    expiry = (DAY + timedelta(days=offset)).isoformat()
    return post(stack, "/items", {"name": name, "expiry_mode": "date",
                                  "expiry_date": expiry})["public_id"]


def setup(stack: Stack) -> None:
    response = stack.client.put("/api/v1/profile", json={"name": "Mohammed",
                                                         "timezone": "Asia/Kolkata"},
                                headers=HEADERS)
    assert response.status_code == 200, response.text
    on(stack, 0)


def test_a_new_owner_has_a_zero_streak(stack: Stack):
    setup(stack)
    assert streak(stack) == 0


def test_an_action_counts_and_quiet_days_neither_extend_nor_break_it(stack: Stack):
    setup(stack)
    milk = expiring(stack, "Oat milk", 1)
    assert streak(stack) == 0  # due today, nothing done yet: no streak, nothing broken
    post(stack, f"/items/{milk}/use")
    assert streak(stack) == 1
    on(stack, 1)
    assert streak(stack) == 1  # ends yesterday
    on(stack, 4)
    assert streak(stack) == 1  # days 1 to 3 had nothing due: skipped


def test_a_missed_due_day_ends_the_streak(stack: Stack):
    setup(stack)
    post(stack, f"/items/{expiring(stack, 'Oat milk', 1)}/use")
    on(stack, 1)
    expiring(stack, "Yogurt", 3)  # due from day 1, never handled
    assert streak(stack) == 1
    on(stack, 2)
    assert streak(stack) == 0


def test_an_undone_action_does_not_count(stack: Stack):
    setup(stack)
    used = post(stack, f"/items/{expiring(stack, 'Oat milk', 1)}/use")
    assert streak(stack) == 1
    post(stack, f"/events/{used['event_id']}/undo")
    assert streak(stack) == 0
