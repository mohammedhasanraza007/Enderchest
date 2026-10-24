"""The expiry parser against the 35 supplied cases (tests/fixtures/expiry_cases.csv) and the
rules of the Phase 3 spec that the cases do not cover. The test clock date is 2026-10-17.
"""

import csv
import os
from datetime import date
from pathlib import Path

import pytest

from app.services.expiry_parser import parse_expiry

TODAY = date(2026, 10, 17)
# The tools image copies the fixture to /fixtures; from a checkout it sits at the repo root.
FIXTURES = Path(os.environ.get("ENDERCHEST_FIXTURES",
                               Path(__file__).resolve().parents[3] / "tests" / "fixtures"))


def _cases() -> list[dict]:
    with open(FIXTURES / "expiry_cases.csv", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


CASES = _cases()


def test_all_35_cases_are_present():
    assert len(CASES) == 35


@pytest.mark.parametrize("case", CASES, ids=[case["raw_text"] for case in CASES])
def test_supplied_case(case):
    reading = parse_expiry(case["raw_text"], TODAY)
    expected = date.fromisoformat(case["expected_date"]) if case["expected_date"] else None
    assert reading.date == expected
    assert set(reading.flags) == ({case["flags"]} if case["flags"] else set())


@pytest.mark.parametrize(("text", "chosen", "other"), [
    ("EXP 03/04/2027", date(2027, 4, 3), date(2027, 3, 4)),
    ("Expiry 5/6/2026", date(2026, 6, 5), date(2026, 5, 6)),
])
def test_an_ambiguous_date_offers_the_other_reading(text, chosen, other):
    reading = parse_expiry(text, TODAY)
    assert reading.date == chosen
    assert reading.alternatives == (other,)


def test_only_the_valid_reading_is_used_when_day_first_is_impossible():
    reading = parse_expiry("EXP 12/31/2027", TODAY)
    assert reading.date == date(2027, 12, 31)
    assert reading.flags == ()


def test_lowercase_l_and_capital_i_read_as_one_inside_a_date():
    reading = parse_expiry("exp l4/O3/2O27", TODAY)
    assert reading.date == date(2027, 3, 14)
    assert reading.flags == ("ocr_fix",)


def test_a_date_with_no_label_is_offered_but_flagged():
    reading = parse_expiry("Oat milk\n14/03/2027\n1 L", TODAY)
    assert reading.date == date(2027, 3, 14)
    assert reading.flags == ("unlabelled",)


def test_the_label_may_sit_on_the_line_above_the_date():
    assert parse_expiry("BEST BEFORE\n14 MAR 2027", TODAY).date == date(2027, 3, 14)


def test_a_shelf_life_in_years_counts_as_months():
    reading = parse_expiry("MFG 03/2025 BEST BEFORE 2 YEARS FROM MFG", TODAY)
    assert reading.date == date(2027, 3, 31)
    assert reading.flags == ("computed",)


def test_the_text_shows_where_the_date_came_from():
    reading = parse_expiry("Net 500 ml MFD 10/2025 EXP 10/2026 LOT 7", TODAY)
    assert reading.text == "EXP 10/2026"


def test_a_lot_number_or_a_size_is_not_a_date():
    assert parse_expiry("LOT 4471 500 ML 12 PCS", TODAY).flags == ("no_date",)
