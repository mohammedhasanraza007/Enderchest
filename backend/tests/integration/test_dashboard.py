"""Phase 5: the dashboard (API 2.13, DATA_MODEL 3.3 to 3.6, D-109 to D-113). Gate 2: every
number equals its breakdown list (F-020) on the three storyboard fixtures and on a tiny database
built by hand; gate 3: the storyboard frames reached by the owner's actions; gate 4: under 200 ms
with 1,000 items."""

import statistics
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app import clock
from app.derived import RING_WEIGHTS, RINGS
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

TODAY = date(2026, 10, 16)
ZONE = "Asia/Kolkata"


@pytest.fixture(autouse=True)
def _real_clock():
    yield
    clock.reset()


def post(stack: Stack, path: str, body: dict | None = None) -> dict:
    response = stack.client.post(f"/api/v1{path}", json=body, headers=HEADERS)
    assert response.status_code in (200, 201), response.text
    return response.json()


def get(stack: Stack, path: str) -> dict:
    response = stack.client.get(f"/api/v1{path}")
    assert response.status_code == 200, response.text
    return response.json()


def owner(stack: Stack, evening: bool = True) -> None:
    """The owner's profile, and the clock at 19:30 on the storyboard's day in their zone."""
    response = stack.client.put("/api/v1/profile", json={"name": "Mohammed", "timezone": ZONE},
                                headers=HEADERS)
    assert response.status_code == 200, response.text
    moment = datetime(2026, 10, 16, 19 if evening else 9, 30, tzinfo=ZoneInfo(ZONE))
    post(stack, "/test/clock", {"now": moment.isoformat()})


def story(stack: Stack, stage: int) -> dict:
    owner(stack)
    return post(stack, f"/test/fixtures/storyboard-{stage}")


def frame(board: dict) -> tuple:
    """What a storyboard frame shows: score, item count, card rows, the truck's day."""
    names = [f"{(row['item'] or row['task'])['name' if row['item'] else 'title']} ({row['word']})"
             for row in board["attention"]["rows"]]
    return board["score"], board["item_count"], names, board["road"]["truck_date"]


def assert_numbers_equal_their_breakdowns(stack: Stack) -> dict:
    """F-020: ring value, counts, score, item count and attention total each equal the list
    they summarise."""
    board = get(stack, "/dashboard")
    for ring in RINGS:
        sheet = get(stack, f"/dashboard/rings/{ring}")
        shown = board["rings"][ring]
        assert (sheet["value"], sheet["num"], sheet["den"]) == (
            shown["value"], shown["num"], shown["den"]), ring
        assert len(sheet["qualifying"]) == shown["num"], ring
        assert len(sheet["qualifying"]) + len(sheet["failing"]) == shown["den"], ring
        if shown["den"]:
            assert shown["value"] == int(100 * shown["num"] / shown["den"] + 0.5), ring
    applicable = [r for r in RINGS if board["rings"][r]["value"] is not None]
    if board["item_count"] and applicable:
        weighted = sum(RING_WEIGHTS[r] * board["rings"][r]["value"] for r in applicable)
        assert board["score"] == int(weighted / sum(RING_WEIGHTS[r] for r in applicable) + 0.5)
    active = get(stack, "/items?state=active&limit=200")
    assert board["item_count"] == active["total"]
    assert board["rings"]["documented"]["den"] == board["item_count"]
    open_rows = get(stack, "/notifications?status=open&limit=200")["items"]
    assert board["attention"]["total"] == len(open_rows)
    assert [r["id"] for r in board["attention"]["rows"]] == [r["id"] for r in open_rows[:3]]
    assert get(stack, "/notifications/count")["open"] == board["attention"]["total"]
    return board


# ---- the storyboard (DESIGN 20, D-109, D-111) -------------------------------------------------

FRAME_1 = (82, 142, ["Oat Milk (expires today)", "Baby Spinach (inspect)",
                     "Greek Yogurt (2 days left)"], "2026-10-18")
FRAME_2 = (86, 142, FRAME_1[2], "2026-10-21")
FRAME_3 = (91, 141, ["Baby Spinach (inspect)"], "2026-10-26")


@pytest.mark.parametrize("stage, expected", [(1, FRAME_1), (2, FRAME_2), (3, FRAME_3)])
def test_each_storyboard_fixture_computes_its_frame_and_its_breakdowns_add_up(
        stack: Stack, stage: int, expected: tuple):
    story(stack, stage)
    board = assert_numbers_equal_their_breakdowns(stack)
    assert frame(board) == expected
    assert board["greeting"] == {"part": "evening", "name": "Mohammed"}
    assert board["today"] == board["road"]["start"] == "2026-10-16"
    assert board["savings"] is None and board["streak"] is None
    truck = next(e for e in board["road"]["events"] if e["date"] == board["road"]["truck_date"])
    assert truck["label"] == {1: "Pantry Refill", 2: "Clean PC", 3: "Blade check"}[stage]


def test_frame_1_rings_are_the_planned_values(stack: Stack):
    story(stack, 1)
    rings = get(stack, "/dashboard")["rings"]
    assert {r: (rings[r]["num"], rings[r]["den"], rings[r]["value"]) for r in RINGS} == {
        "documented": (112, 142, 79), "located": (124, 142, 87), "fresh": (136, 142, 96),
        "on_time": (5, 9, 56)}
    sheet = get(stack, "/dashboard/rings/on_time")
    assert sorted(e["note"] for e in sheet["failing"]) == [
        "1 day overdue", "2 days overdue", "3 days overdue", "4 days overdue"]


def test_the_owners_actions_on_frame_1_reproduce_frames_2_and_3(stack: Stack):
    """Gate 3: the buttons' endpoints, not the fixture builder, move frame 1 to 2 to 3."""
    built = story(stack, 1)
    tasks, ids = built["task_ids"], built["public_ids"]
    for title in ("Pantry Refill", "Water the plants", "Change bedsheets"):
        post(stack, f"/tasks/{tasks[title]}/done")
    assert frame(assert_numbers_equal_their_breakdowns(stack)) == FRAME_2
    post(stack, f"/items/{ids['Oat Milk']}/use", {"amount": 1})
    yogurt = next(r for r in get(stack, "/dashboard")["attention"]["rows"]
                  if r["item"] and r["item"]["public_id"] == ids["Greek Yogurt"])
    post(stack, f"/notifications/{yogurt['id']}/snooze", {"option": "tomorrow"})
    for title in ("Clean PC", "Descale kettle", "Clean the fridge"):
        post(stack, f"/tasks/{tasks[title]}/done")
    assert frame(assert_numbers_equal_their_breakdowns(stack)) == FRAME_3


def test_the_storyboard_fixtures_have_real_photo_files(stack: Stack):
    story(stack, 1)
    photos = list(stack.settings.photos_dir.glob("*.jpg"))
    assert len(photos) == 112
    item = get(stack, "/items?state=active&limit=1&q=Oat")["items"][0]
    response = stack.client.get(f"/api/v1/photos/{item['primary_photo_id']}/thumb")
    assert response.status_code == 200


# ---- a tiny database built by hand: the edges -------------------------------------------------

def make_item(stack: Stack, name: str, **fields) -> str:
    return post(stack, "/items", {"name": name, **fields})["public_id"]


def test_an_empty_database_has_no_score_and_says_so(stack: Stack):
    owner(stack, evening=False)
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["score"] is None and board["item_count"] == 0
    assert board["subtitle"] == "Add items to see your overview"
    assert board["greeting"]["part"] == "morning"
    assert all(board["rings"][r] == {"value": None, "num": 0, "den": 0} for r in RINGS)
    assert board["road"] == {"start": "2026-10-16", "end": "2026-10-29", "events": [],
                             "truck_date": "2026-10-16"}
    assert board["attention"] == {"rows": [], "total": 0}


def test_fresh_and_on_time_edges_on_a_tiny_database(stack: Stack):
    owner(stack)
    make_item(stack, "Milk", expiry_mode="date", expiry_date="2026-10-16")  # today: fresh
    make_item(stack, "Curd", expiry_mode="date", expiry_date="2026-10-15")  # yesterday: not
    make_item(stack, "Rice", expiry_mode="unknown")  # unknown: not fresh
    make_item(stack, "Hammer", expiry_mode="none")  # no expiry: fresh
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["rings"]["fresh"] == {"value": 50, "num": 2, "den": 4}
    assert board["rings"]["on_time"] == {"value": None, "num": 0, "den": 0}  # no tasks yet
    # No tasks: On time is left out of the score, not counted as 100 (DATA_MODEL 3.4).
    assert board["score"] == int((25 * 0 + 20 * 0 + 35 * 50) / 80 + 0.5)
    notes = {e["name"]: e["note"] for e in get(stack, "/dashboard/rings/fresh")["failing"]}
    assert notes == {"Curd": "expired 15 Oct", "Rice": "date not set"}

    post(stack, "/tasks", {"title": "Due today", "first_due": "2026-10-16"})
    post(stack, "/tasks", {"title": "Late", "first_due": "2026-10-14"})
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["rings"]["on_time"] == {"value": 50, "num": 1, "den": 2}  # today is on time
    assert board["subtitle"] == "4 things need you today"  # expired, today, due, late


def test_items_out_of_active_and_in_trash_never_count(stack: Stack):
    owner(stack)
    kept = make_item(stack, "Kept", expiry_mode="none")
    used = make_item(stack, "Used", expiry_mode="none")
    binned = make_item(stack, "Binned", expiry_mode="none")
    post(stack, f"/items/{used}/use", {"amount": 1})
    assert stack.client.delete(f"/api/v1/items/{binned}", headers=HEADERS).status_code == 200
    board = assert_numbers_equal_their_breakdowns(stack)
    assert board["item_count"] == 1
    assert [e["public_id"] for e in get(stack, "/dashboard/rings/located")["failing"]] == [kept]


def test_a_disabled_task_and_a_task_on_a_used_item_leave_on_time(stack: Stack):
    owner(stack)
    drill = make_item(stack, "Drill", expiry_mode="none")
    response = stack.client.put(f"/api/v1/items/{drill}/maintenance", headers=HEADERS,
                                json={"enabled": True, "interval_days": 30,
                                      "first_due": "2026-10-10"})
    assert response.status_code == 200, response.text
    off = post(stack, "/tasks", {"title": "Off", "first_due": "2026-10-10"})
    stack.client.patch(f"/api/v1/tasks/{off['id']}", json={"enabled": False}, headers=HEADERS)
    assert get(stack, "/dashboard")["rings"]["on_time"]["den"] == 1
    post(stack, f"/items/{drill}/use", {"amount": 1})
    assert get(stack, "/dashboard")["rings"]["on_time"]["den"] == 0


def test_the_card_holds_three_rows_and_the_total_counts_them_all(stack: Stack):
    owner(stack)
    for offset in range(5):
        post(stack, "/tasks", {"title": f"Chore {offset}",
                               "first_due": (TODAY - timedelta(days=offset)).isoformat()})
    board = assert_numbers_equal_their_breakdowns(stack)
    assert (len(board["attention"]["rows"]), board["attention"]["total"]) == (3, 5)


def test_unknown_ring_and_road_window(stack: Stack):
    owner(stack)
    assert stack.client.get("/api/v1/dashboard/rings/shiny").json()["error"]["code"] == (
        "not_found")
    post(stack, "/tasks", {"title": "Far", "first_due": "2026-11-10"})
    assert get(stack, "/dashboard")["road"]["events"] == []
    road = get(stack, "/dashboard/road?days=30")
    assert (road["end"], road["truck_date"]) == ("2026-11-14", "2026-11-10")
    assert stack.client.get("/api/v1/dashboard/road?days=31").status_code == 422


# ---- gate 4: speed ----------------------------------------------------------------------------

def test_the_dashboard_answers_in_under_200_ms_with_1000_items(stack: Stack):
    owner(stack)
    post(stack, "/test/fixtures/items-1000")
    get(stack, "/dashboard")  # the first call reconciles
    times = []
    for _ in range(5):
        start = time.perf_counter()
        get(stack, "/dashboard")
        times.append((time.perf_counter() - start) * 1000)
    assert statistics.median(times) < 200, times
