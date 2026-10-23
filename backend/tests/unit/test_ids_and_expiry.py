from datetime import date

import pytest

from app import ids
from app.derived import expiry_view


def test_new_public_id_has_the_right_shape():
    for _ in range(200):
        value = ids.new_public_id()
        assert ids.is_public_id(value)
        assert not set(value[5:]) & set("ILOU")


@pytest.mark.parametrize("typed", [
    "ENDR-7K2M9QXA", "endr-7k2m9qxa", "ENDR7K2M9QXA", "7k2m9qxa", " endr - 7k2m 9qxa ",
])
def test_typed_forms_normalise(typed):
    assert ids.normalise(typed) == "ENDR-7K2M9QXA"


def test_look_alikes_become_digits():
    assert ids.normalise("endr-ilo00000") == "ENDR-11000000"


@pytest.mark.parametrize("bad", ["", "ENDR-", "ENDR-7K2M9QX", "ENDR-7K2M9QXAB", "ENDR-7K2M9QXU",
                                 "https://example.com/ENDR-7K2M9QXA"])
def test_bad_codes_are_refused(bad):
    assert ids.normalise(bad) is None


TODAY = date(2026, 10, 23)


@pytest.mark.parametrize(("expiry", "status", "word", "days"), [
    ("2026-10-22", "expired", "expired", -1),
    ("2026-10-23", "today", "expires today", 0),
    ("2026-10-24", "soon", "1 day left", 1),
    ("2026-10-26", "soon", "3 days left", 3),
    ("2026-10-27", "ok", "4 days left", 4),
])
def test_expiry_status_by_days_left(expiry, status, word, days):
    view = expiry_view("date", expiry, TODAY, lead_days=3)
    assert (view["status"], view["word"], view["days_left"]) == (status, word, days)


def test_no_expiry_and_unknown():
    assert expiry_view("none", None, TODAY, 3)["word"] == "no expiry"
    unknown = expiry_view("unknown", None, TODAY, 3)
    assert (unknown["status"], unknown["word"], unknown["days_left"]) == ("unknown",
                                                                         "date not set", None)
