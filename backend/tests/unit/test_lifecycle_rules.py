"""Phase 4 rules: the completion rule (DATA_MODEL 2.9), words and urgency (D-106), the snooze
cap (3.8, D-047) and the reconcile's desired set (3.8, D-104)."""

from datetime import date

import pytest

from app.derived import (
    dedupe_key,
    next_due_after,
    notification_word,
    snooze_until,
    task_word,
    urgency,
)
from app.services.notifications import Desired, desired_rows

D = date.fromisoformat


# ---- completion rule ----------------------------------------------------------------------------

def test_from_completion_counts_from_the_day_it_was_done():
    assert next_due_after("from_completion", 14, D("2026-10-20"), D("2026-10-25")) == D(
        "2026-11-08")
    assert next_due_after("from_completion", 14, D("2026-10-20"), D("2026-10-15")) == D(
        "2026-10-29")


def test_fixed_keeps_the_original_series():
    # Done 5 days late: the next date of the series after the 25th is 3 Nov, not 8 Nov.
    assert next_due_after("fixed", 14, D("2026-10-20"), D("2026-10-25")) == D("2026-11-03")
    # Done on the day: the next one is a full interval later.
    assert next_due_after("fixed", 14, D("2026-10-20"), D("2026-10-20")) == D("2026-11-03")
    # Done early: that occurrence is satisfied, so the series moves one step.
    assert next_due_after("fixed", 14, D("2026-10-20"), D("2026-10-15")) == D("2026-11-03")


def test_fixed_thirty_days_late_lands_after_the_day_done():
    # Series 20 Oct, 3 Nov, 17 Nov, 1 Dec: done on 19 Nov, the next is 1 Dec.
    result = next_due_after("fixed", 14, D("2026-10-20"), D("2026-11-19"))
    assert result == D("2026-12-01") and result > D("2026-11-19")


def test_a_one_off_has_no_next_date():
    assert next_due_after("from_completion", None, D("2026-10-20"), D("2026-10-25")) is None
    assert next_due_after("fixed", None, D("2026-10-20"), D("2026-10-25")) is None


# ---- words and urgency --------------------------------------------------------------------------

TODAY = D("2026-10-24")


@pytest.mark.parametrize("kind, due, word", [
    ("expiry_soon", "2026-10-24", "expires today"),
    ("expiry_soon", "2026-10-25", "1 day left"),
    ("expiry_soon", "2026-10-27", "3 days left"),
    ("expired", "2026-10-20", "expired"),
    ("inspection_due", "2026-10-24", "inspect"),
    ("inspection_due", "2026-10-23", "inspect, 1 day overdue"),
    ("inspection_due", "2026-10-14", "inspect, 10 days overdue"),
    ("task_due", "2026-10-24", "due today"),
    ("task_due", "2026-10-23", "1 day overdue"),
    ("task_due", "2026-09-24", "30 days overdue"),
])
def test_notification_words(kind, due, word):
    assert notification_word(kind, D(due), TODAY) == word


def test_finding_words_never_say_replacement():
    assert notification_word("inspection_finding", TODAY, TODAY, "worn") == (
        "inspection suggested: worn")
    assert notification_word("inspection_finding", TODAY, TODAY, "defective") == (
        "inspection suggested: defective")


@pytest.mark.parametrize("kind, due, value", [
    ("expired", "2026-10-30", "overdue"),  # an expired row is always overdue
    ("task_due", "2026-10-23", "overdue"),
    ("task_due", "2026-10-24", "today"),
    ("expiry_soon", "2026-10-24", "today"),
    ("expiry_soon", "2026-10-26", "upcoming"),
    ("inspection_finding", "2026-10-24", "today"),
])
def test_urgency(kind, due, value):
    assert urgency(kind, D(due), TODAY) == value


@pytest.mark.parametrize("next_due, enabled, interval, last_done, word", [
    ("2026-10-24", True, 14, None, "due today"),
    ("2026-10-25", True, 14, None, "due tomorrow"),
    ("2026-10-30", True, 14, None, "due in 6 days"),
    ("2026-10-23", True, 14, None, "1 day overdue"),
    ("2026-10-10", True, 14, None, "14 days overdue"),
    ("2026-10-30", False, 14, None, "off"),
    ("2026-10-20", False, None, "2026-10-20", "done 20 Oct"),
])
def test_task_words(next_due, enabled, interval, last_done, word):
    assert task_word(D(next_due), TODAY, enabled, interval,
                     D(last_done) if last_done else None) == word


# ---- snooze --------------------------------------------------------------------------------------

def test_snooze_options():
    assert snooze_until("tomorrow", "task_due", D("2026-10-20"), TODAY) == D("2026-10-25")
    assert snooze_until("3days", "task_due", D("2026-10-20"), TODAY) == D("2026-10-27")
    assert snooze_until("week", "expired", D("2026-10-20"), TODAY) == D("2026-10-31")


def test_snooze_never_hides_an_expiry_past_its_date():
    assert snooze_until("week", "expiry_soon", D("2026-10-26"), TODAY) == D("2026-10-26")
    assert snooze_until("tomorrow", "expiry_soon", D("2026-10-26"), TODAY) == D("2026-10-25")


def test_snooze_that_cannot_move_the_row_is_refused():
    assert snooze_until("week", "expiry_soon", TODAY, TODAY) is None
    assert snooze_until("tomorrow", "inspection_finding", TODAY, TODAY) is None


# ---- desired set ---------------------------------------------------------------------------------

def test_dedupe_key_shape():
    assert dedupe_key("expiry_soon", 7, None, D("2026-10-26")) == "expiry_soon|7|-|2026-10-26"
    assert dedupe_key("task_due", None, 3, D("2026-10-20")) == "task_due|-|3|2026-10-20"


def test_desired_rows_follow_the_reconcile_rules():
    items = [(1, "2026-10-24"), (2, "2026-10-27"), (3, "2026-10-28"), (4, "2026-10-20")]
    tasks = [(10, "chore", None, "2026-10-24"), (11, "maintenance", 2, "2026-09-24")]
    findings = [(3, "2026-10-22")]
    rows = desired_rows(items, tasks, findings, TODAY, lead_days=3)
    assert rows == {
        "expiry_soon|1|-|2026-10-24": Desired("expiry_soon", 1, None, "2026-10-24"),
        "expiry_soon|2|-|2026-10-27": Desired("expiry_soon", 2, None, "2026-10-27"),
        "expired|4|-|2026-10-20": Desired("expired", 4, None, "2026-10-20"),
        "task_due|-|10|2026-10-24": Desired("task_due", None, 10, "2026-10-24"),
        "inspection_due|2|11|2026-09-24": Desired("inspection_due", 2, 11, "2026-09-24"),
        "inspection_finding|3|-|2026-10-22": Desired("inspection_finding", 3, None, "2026-10-22"),
    }  # item 3 is four days out with lead 3: no expiry row yet
