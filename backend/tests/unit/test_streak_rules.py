"""Phase 8: the streak (DATA_MODEL 3.7, D-127), each rule on its own."""

from datetime import date, timedelta

from app.derived import due_days, streak_days

TODAY = date(2026, 10, 27)


def ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def always_due(_day: date) -> bool:
    return True


def test_no_actions_is_zero():
    assert streak_days(TODAY, set(), always_due) == 0


def test_consecutive_days_ending_today_count():
    assert streak_days(TODAY, {ago(0), ago(1), ago(2)}, always_due) == 3


def test_today_not_counting_yet_does_not_break_a_streak_ending_yesterday():
    assert streak_days(TODAY, {ago(1), ago(2)}, always_due) == 2


def test_a_day_with_something_due_and_no_action_breaks_it():
    assert streak_days(TODAY, {ago(0), ago(2), ago(3)}, always_due) == 1


def test_a_streak_ending_before_yesterday_is_over():
    assert streak_days(TODAY, {ago(2), ago(3)}, always_due) == 0


def test_days_with_nothing_due_are_skipped_not_counted():
    due = {ago(0), ago(2), ago(3)}
    assert streak_days(TODAY, {ago(0), ago(2), ago(3)}, lambda d: d in due) == 3


def test_skipped_yesterday_lets_a_streak_reach_today_from_further_back():
    assert streak_days(TODAY, {ago(2)}, lambda d: d != ago(1) and d != ago(0)) == 1


def test_the_walk_stops_at_the_first_action():
    nothing_due = lambda _d: False  # noqa: E731
    assert streak_days(TODAY, {ago(5)}, nothing_due) == 1


def test_due_days_cover_open_and_resolved_rows():
    rows = [(ago(5), ago(3)), (ago(1), None)]
    due = due_days(rows, TODAY)
    assert {ago(5), ago(4), ago(3), ago(1), ago(0)} == due
    assert ago(2) not in due and ago(6) not in due
