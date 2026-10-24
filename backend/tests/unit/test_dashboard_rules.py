"""Phase 5 rules: rings, score, greeting, subtitle and the road (DATA_MODEL 3.3 to 3.6,
D-110, D-113), each formula and each exclusion on its own."""

from datetime import date

from app.derived import (
    dashboard_subtitle,
    greeting_part,
    health_score,
    is_documented,
    is_fresh,
    ring_value,
    road,
    round_half_up,
)

TODAY = date(2026, 10, 16)


def rings(documented=None, located=None, fresh=None, on_time=None) -> dict:
    return {name: {"value": value, "num": 0, "den": 0}
            for name, value in (("documented", documented), ("located", located),
                                ("fresh", fresh), ("on_time", on_time))}


# ---- rings and score --------------------------------------------------------------------------

def test_a_ring_is_the_rounded_share_and_rounds_half_up():
    assert ring_value(112, 142) == {"value": 79, "num": 112, "den": 142}
    assert ring_value(1, 8)["value"] == 13  # 12.5 rounds up, not to the even 12
    assert round_half_up(82.5) == 83


def test_a_ring_with_nothing_to_count_is_not_applicable():
    assert ring_value(0, 0) == {"value": None, "num": 0, "den": 0}


def test_the_score_is_the_weighted_average_of_the_applicable_rings():
    # 25 × 79 + 20 × 87 + 35 × 96 + 20 × 56 = 8,195 over 100 → 82 (the storyboard's frame 1)
    assert health_score(rings(79, 87, 96, 56)) == 82
    assert health_score(rings(79, 87, 96, 78)) == 86
    assert health_score(rings(79, 87, 96, 100)) == 91


def test_with_no_tasks_on_time_is_left_out_of_the_score_not_counted_as_full():
    # (25 × 80 + 20 × 50 + 35 × 60) / 80 = 63.75 → 64
    assert health_score(rings(80, 50, 60, None)) == 64
    assert health_score(rings(80, 50, 60, 100)) == 71


def test_with_no_ring_applicable_there_is_no_score():
    assert health_score(rings()) is None


def test_documented_needs_a_photo_and_a_printed_label_or_no_label_needed():
    assert is_documented(True, True, False)
    assert is_documented(True, False, True)
    assert not is_documented(True, False, False)
    assert not is_documented(False, True, True)


def test_fresh_counts_no_expiry_and_dates_not_yet_past_including_today():
    assert is_fresh("none", None, TODAY)
    assert is_fresh("date", "2026-10-16", TODAY)  # expires today: still fresh today
    assert is_fresh("date", "2026-11-01", TODAY)
    assert not is_fresh("date", "2026-10-15", TODAY)
    assert not is_fresh("unknown", None, TODAY)  # unknown is not fresh until the owner picks


# ---- greeting and subtitle --------------------------------------------------------------------

def test_the_greeting_follows_the_local_hour():
    assert [greeting_part(h) for h in (4, 5, 11, 12, 16, 17, 20, 21, 0)] == [
        "night", "morning", "morning", "afternoon", "afternoon", "evening", "evening", "night",
        "night"]


def test_the_subtitle_states_one_real_fact():
    assert dashboard_subtitle(142, 3) == "3 things need you today"
    assert dashboard_subtitle(142, 1) == "1 thing needs you today"
    assert dashboard_subtitle(142, 0) == "Everything is on track"
    assert dashboard_subtitle(0, 0) == "Add items to see your overview"


# ---- road -------------------------------------------------------------------------------------

def expiry(on: str, name: str) -> dict:
    return {"date": on, "label": name, "public_id": f"ENDR-{name[:8].upper():0<8}"}


def job(on: str, title: str, task_id: int) -> dict:
    return {"date": on, "label": title, "task_id": task_id, "public_id": None}


def test_the_window_starts_today_and_leaves_out_the_past_and_after_the_window():
    result = road(TODAY, 14, [expiry("2026-10-15", "Old"), expiry("2026-10-29", "Last"),
                              expiry("2026-10-30", "Out")], [job("2026-10-10", "Late", 1)])
    assert (result["start"], result["end"]) == ("2026-10-16", "2026-10-29")
    assert [event["date"] for event in result["events"]] == ["2026-10-29"]


def test_several_events_on_one_day_collapse_and_take_the_task_name():
    result = road(TODAY, 14, [expiry("2026-10-18", "Greek Yogurt")],
                  [job("2026-10-18", "Pantry Refill", 7)])
    (event,) = result["events"]
    assert (event["kind"], event["label"], event["count"]) == ("mixed", "Pantry Refill", 2)
    assert [entry["kind"] for entry in event["entries"]] == ["task", "expiry"]


def test_the_truck_parks_at_the_next_task_after_today_not_at_today():
    # The storyboard's frame 1: Oat Milk expires today, the inspection is due today, Greek
    # Yogurt on the 18th with Pantry Refill: the truck goes to the 18th (D-110).
    result = road(TODAY, 14,
                  [expiry("2026-10-16", "Oat Milk"), expiry("2026-10-18", "Greek Yogurt")],
                  [job("2026-10-16", "Inspect", 1), job("2026-10-18", "Pantry Refill", 2),
                   job("2026-10-21", "Clean PC", 3)])
    assert result["truck_date"] == "2026-10-18"


def test_with_no_task_ahead_the_truck_goes_to_the_next_event_else_today():
    assert road(TODAY, 14, [expiry("2026-10-20", "Milk")], [])["truck_date"] == "2026-10-20"
    assert road(TODAY, 14, [expiry("2026-10-16", "Milk")], [])["truck_date"] == "2026-10-16"
    empty = road(TODAY, 14, [], [])
    assert (empty["events"], empty["truck_date"]) == ([], "2026-10-16")


def test_the_tasks_page_road_is_the_same_road_over_30_days():
    result = road(TODAY, 30, [], [job("2026-11-14", "Service bicycle", 4)])
    assert result["end"] == "2026-11-14"
    assert result["truck_date"] == "2026-11-14"
