"""Phase 6 verification: the scoring table checked by hand against the spec (Build 3, D-119).

Written by the verifying session from the spec's table, not from the builder's tests."""

import pytest

from app.services import ownership_rules as rules
from app.services.ownership_rules import Query, level, rank, score, sizes_in


def item(name: str, **attributes) -> dict:
    return {"id": 1, "name": name, "attributes": attributes}


@pytest.mark.parametrize(("points", "model", "size", "overlap", "want"), [
    (24, True, True, 100, None),  # below 25 is hidden, whatever supports it
    (25, False, False, 60, "low"),
    (44, False, False, 60, "low"),
    (45, False, False, 60, "medium"),
    (74, True, False, 100, "medium"),
    (75, True, False, 0, "high"),  # a model match alone is enough at 75
    (75, False, True, 79, "medium"),  # a size match needs name overlap of at least 80
    (75, False, True, 80, "high"),
    (75, False, False, 100, "medium"),  # 75 without a model or size match is not High
    (90, False, False, 40, "low"),  # no text support: at most Possible
])
def test_level_boundaries(points, model, size, overlap, want):
    assert level(points, model, size, overlap, model or size or overlap >= 50) == want


def test_each_signal_earns_the_spec_points():
    base = item("Widget", model="AB-1234", size="13 mm")
    assert score(Query(model="ab 1234"), base, None).score == 60
    assert score(Query(model="AB-1243"), item("W", model="AB-1234"), None).score == 0  # 83.3
    assert score(Query(model="ABCDEFGH-12345"), item("W", model="ABCDEFGH-1234S"),
                 None).score == 35  # one character off in 13: ratio 92.3
    assert score(Query(sizes=sizes_in("13 mm")), base, None).score == 20
    assert score(Query(sizes=sizes_in("14 mm")), base, None).score == -30
    assert score(Query(name="widget"), base, None).score == 30
    assert score(Query(name="tools widget"), base, "Tools").score == 35  # 30 + category 5
    assert score(Query(vector_score={1: 0.80}), base, None).score == 15
    assert score(Query(vector_score={1: 0.70}), base, None).score == 8
    assert score(Query(vector_score={1: 0.69}), base, None).score == 0


@pytest.mark.parametrize(("query", "attribute"), [
    ("1 L", "1000 ml"), ("0.5 kg", "500 g"), ("13mm", "1.3 cm"), ("0.5 in", "12.7 mm"),
    ('1"', "25.4 mm"), ("1,5 l", "1500 ml"), ("10,000 mAh", "10000 mAh"),
    ("2,500 mAh", "2500mAh"),
])
def test_sizes_compare_after_unit_normalisation(query, attribute):
    assert score(Query(sizes=sizes_in(query)), item("X", size=attribute), None).score == 20


def test_sizes_of_other_kinds_say_nothing():
    found = score(Query(sizes=sizes_in("13 mm")), item("X", size="500 ml"), None)
    assert (found.score, found.reasons) == (0, [])


def test_a_sizes_list_matches_any_of_its_sizes():
    found = score(Query(sizes=sizes_in("14 mm")), item("Set", sizes=["13 mm", "14 mm"]), None)
    assert found.score == 20


def test_a_two_in_one_name_is_not_a_size_in_inches():
    # "2 in 1" and "3-in-1" are product names, not 2 inches: they must not cost the owner's own
    # cable its place when the words are typed exactly.
    cable = item("2 in 1 USB cable", size="1 m")
    found = score(Query(name="2 in 1 USB cable", sizes=sizes_in("2 in 1 USB cable")), cable, None)
    assert "Different size" not in found.reasons and found.level is not None


def test_model_numbers_ignore_case_spaces_dashes_and_dots():
    for typed in ("wh1000xm4", "WH 1000 XM4", "wh-1000-xm4", "WH.1000/XM4"):
        assert score(Query(model=typed), item("H", model="WH-1000XM4"), None).score == 60


def test_a_strong_look_alike_with_a_different_size_stays_hidden():
    # D-119 lifts a candidate whose ONLY signal is a strong look-alike; a different size is a
    # signal against it (-30), so a 14 mm spanner is not offered for a 13 mm one by looks.
    found = score(Query(sizes=sizes_in("13 mm"), vector_score={1: 0.9}),
                  item("Spanner", size="14 mm"), None)
    assert found.level is None


def test_a_strong_look_alike_alone_is_possible_and_a_weak_one_hidden():
    assert score(Query(vector_score={1: 0.85}), item("Mug"), None).level == "low"
    assert score(Query(vector_score={1: 0.75}), item("Mug"), None).level is None


def test_looks_and_words_without_a_model_or_size_cannot_reach_high():
    found = score(Query(name="blue mug", vector_score={1: 0.95}), item("Blue mug"), "Mug")
    assert found.score == 50 and found.level == "medium"


def test_at_most_five_best_first_ties_by_id():
    many = [rules.Candidate(i, 50, "medium", []) for i in range(10, 0, -1)]
    assert [c.item_id for c in rank(many)] == [1, 2, 3, 4, 5]


def test_no_reason_ever_says_certain():
    words = {"Same model number", "Similar model number", "Same size", "Different size",
             "Same name", "Similar name", "Same category", "Looks similar",
             "Looks a little similar"}
    found = score(Query(name="x", model="A1", sizes=sizes_in("1 mm"), vector_score={1: 0.9}),
                  item("x", model="A1", size="1 mm"), "x")
    assert set(found.reasons) <= words
    assert not any(w in " ".join(words).lower() for w in ("certain", "you own this", "100%"))
