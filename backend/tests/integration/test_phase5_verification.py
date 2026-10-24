"""Phase 5 verification probes (docs/reviews/phase-5-verification.md): the local-midnight roll in
Asia/Kolkata, the greeting's hour boundaries, the road window's edges and validation, and the
degenerate data sets the build tests did not cover."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app import clock
from app.derived import RINGS
from tests.conftest import HEADERS, Stack
from tests.integration.test_dashboard import (
    ZONE,
    assert_numbers_equal_their_breakdowns,
    get,
    make_item,
    post,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def at(stack: Stack, day: int, hour: int, minute: int = 0) -> None:
    """The owner in Asia/Kolkata, with the clock at a local moment in October 2026."""
    response = stack.client.put(
        "/api/v1/profile", json={"name": "Mohammed", "timezone": ZONE}, headers=HEADERS
    )
    assert response.status_code == 200, response.text
    moment = datetime(2026, 10, day, hour, minute, tzinfo=ZoneInfo(ZONE))
    post(stack, "/test/clock", {"now": moment.isoformat()})


def test_the_road_and_freshness_roll_at_local_midnight_not_utc_midnight(stack: Stack):
    at(stack, 16, 23, 59)
    make_item(stack, "Milk", expiry_mode="date", expiry_date="2026-10-16")
    board = get(stack, "/dashboard")
    assert (board["today"], board["road"]["start"]) == ("2026-10-16", "2026-10-16")
    assert board["rings"]["fresh"]["value"] == 100
    at(stack, 17, 0, 1)  # 18:31 UTC on the 16th: UTC has not rolled, Kolkata has
    board = assert_numbers_equal_their_breakdowns(stack)
    assert (board["today"], board["road"]["start"], board["road"]["end"]) == (
        "2026-10-17",
        "2026-10-17",
        "2026-10-30",
    )
    assert board["rings"]["fresh"]["value"] == 0
    assert board["road"]["events"] == []  # yesterday's expiry is off the road


@pytest.mark.parametrize(
    "hour, minute, part",
    [
        (4, 59, "night"),
        (5, 0, "morning"),
        (11, 59, "morning"),
        (12, 0, "afternoon"),
        (16, 59, "afternoon"),
        (17, 0, "evening"),
        (20, 59, "evening"),
        (21, 0, "night"),
        (0, 0, "night"),
    ],
)
def test_the_greeting_word_at_each_local_boundary(stack: Stack, hour: int, minute: int, part: str):
    at(stack, 16, hour, minute)
    assert get(stack, "/dashboard")["greeting"] == {"part": part, "name": "Mohammed"}


@pytest.mark.parametrize("days", ["0", "-1", "31", "x", "1.5"])
def test_a_bad_road_window_is_a_validation_error_in_the_one_shape(stack: Stack, days: str):
    at(stack, 16, 19)
    response = stack.client.get(f"/api/v1/dashboard/road?days={days}")
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"} and body["error"]["code"]
    assert "Traceback" not in response.text


def test_a_one_day_road_and_the_windows_last_day(stack: Stack):
    at(stack, 16, 19)
    make_item(stack, "Today", expiry_mode="date", expiry_date="2026-10-16")
    make_item(stack, "Last", expiry_mode="date", expiry_date="2026-10-29")
    make_item(stack, "After", expiry_mode="date", expiry_date="2026-10-30")
    one = get(stack, "/dashboard/road?days=1")
    assert (one["start"], one["end"], one["truck_date"]) == (
        "2026-10-16",
        "2026-10-16",
        "2026-10-16",
    )
    assert [e["date"] for e in one["events"]] == ["2026-10-16"]
    road = get(stack, "/dashboard")["road"]
    assert [e["date"] for e in road["events"]] == ["2026-10-16", "2026-10-29"]
    assert road["truck_date"] == "2026-10-29"  # expiries only: the next event after today


def test_only_events_today_park_the_truck_today_and_a_busy_day_counts_them(stack: Stack):
    at(stack, 16, 19)
    make_item(stack, "Milk", expiry_mode="date", expiry_date="2026-10-16")
    post(stack, "/tasks", {"title": "Sweep", "first_due": "2026-10-16"})
    post(stack, "/tasks", {"title": "Mop", "first_due": "2026-10-16"})
    road = get(stack, "/dashboard")["road"]
    assert road["truck_date"] == "2026-10-16"
    (event,) = road["events"]
    assert (event["kind"], event["count"]) == ("mixed", 3)
    assert event["entries"][0]["kind"] == "task"  # a mixed day is named after a task


def test_only_unknown_expiries_and_only_trashed_items(stack: Stack):
    at(stack, 16, 19)
    for name in ("Rice", "Dal"):
        make_item(stack, name, expiry_mode="unknown")
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["rings"]["fresh"] == {"value": 0, "num": 0, "den": 2}
    assert board["score"] == 0 and board["road"]["events"] == []
    for item in get(stack, "/items?state=active&limit=200")["items"]:
        assert (
            stack.client.delete(f"/api/v1/items/{item['public_id']}", headers=HEADERS).status_code
            == 200
        )
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["item_count"] == 0 and board["score"] is None
    assert all(board["rings"][r]["den"] == 0 for r in RINGS)


def test_tasks_with_no_items_keep_on_time_but_no_score(stack: Stack):
    at(stack, 16, 19)
    post(stack, "/tasks", {"title": "Sweep", "first_due": "2026-10-20"})
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["rings"]["on_time"] == {"value": 100, "num": 1, "den": 1}
    assert board["item_count"] == 0 and board["score"] is None
    assert board["road"]["truck_date"] == "2026-10-20"


def test_the_breakdown_caps_at_200_and_the_counts_stay_whole(stack: Stack):
    at(stack, 16, 19)
    post(stack, "/test/fixtures/items-1000")
    board = get(stack, "/dashboard")
    for ring in ("documented", "located", "fresh"):
        sheet = get(stack, f"/dashboard/rings/{ring}")
        assert (sheet["num"], sheet["den"]) == (
            board["rings"][ring]["num"],
            board["rings"][ring]["den"],
        )
        assert len(sheet["qualifying"]) == min(sheet["num"], 200)
        assert len(sheet["failing"]) == min(sheet["den"] - sheet["num"], 200)
    assert board["item_count"] == board["rings"]["documented"]["den"]
