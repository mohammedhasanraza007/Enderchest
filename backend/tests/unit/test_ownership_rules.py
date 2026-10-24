"""Phase 6: the ownership check's scoring (spec Build 3, D-114). Pure functions only."""

from app.services import ownership_rules as rules
from app.services.ownership_rules import Query


def item(item_id=1, name="13 mm spanner", **attributes):
    return {"id": item_id, "name": name, "attributes": attributes}


def test_sizes_normalise_across_units():
    assert rules.sizes_in("1 L") == rules.sizes_in("1000 ml") == (("volume", 1000.0),)
    assert rules.sizes_in("1.5kg") == (("mass", 1500.0),)
    assert rules.sizes_in('13mm and 0.5"') == (("length", 13.0), ("length", 12.7))
    assert rules.sizes_in("no size here") == ()


def test_model_numbers_compare_without_punctuation():
    assert rules.normalise_model("wh-1000 xm4") == rules.normalise_model("WH1000XM4")


def test_equal_model_with_a_name_is_high():
    found = rules.score(Query(name="Sony headphones", model="WH-1000XM4"),
                        item(name="Sony WH-1000XM4 headphones", model="WH1000XM4"), None)
    assert found.level == "high" and "Same model number" in found.reasons
    assert found.score >= rules.HIGH


def test_a_near_model_number_earns_the_fuzzy_points_only():
    found = rules.score(Query(model="LM2596S-ADJX"), item(name="Buck module", model="LM2596S-ADJ"),
                        None)
    assert found.reasons == ["Similar model number"] and found.score == rules.MODEL_FUZZY


def test_a_different_size_sinks_a_same_named_tool():
    query = Query(name="13 mm spanner", sizes=rules.sizes_in("13 mm"))
    same = rules.score(query, item(1, "13 mm spanner", size="13 mm"), None)
    other = rules.score(query, item(2, "14 mm spanner", size="14 mm"), None)
    assert "Same size" in same.reasons and same.level == "medium"
    assert "Different size" in other.reasons and other.level is None  # below 25: hidden
    assert [c.item_id for c in rules.rank([other, same])] == [1]


def test_sizes_of_different_kinds_say_nothing():
    found = rules.score(Query(name="oat milk", sizes=rules.sizes_in("1 L")),
                        item(name="Oat milk", size="13 mm"), None)
    assert "Different size" not in found.reasons


def test_image_alone_is_at_most_possible():
    found = rules.score(Query(vector_score={1: 0.99}), item(name="Red mug"), None)
    assert found.level == "low" and found.reasons == ["Looks similar"]
    weak = rules.score(Query(vector_score={1: 0.75}), item(name="Red mug"), None)
    assert weak.level is None  # 8 points: hidden


def test_size_and_name_reach_high_only_with_enough_points():
    # Name 30 + size 20 + category 5 + image 15 = 70: still Medium, never High without 75.
    query = Query(name="tools spanner 13 mm", sizes=rules.sizes_in("13 mm"), vector_score={1: 0.9})
    found = rules.score(query, item(name="13 mm spanner", size="13 mm"), "Tools")
    assert found.level == "medium" and found.score < rules.HIGH


def test_high_needs_the_points_and_a_strong_signal():
    assert rules.level(80, False, False, 100, True) == "medium"
    assert rules.level(80, False, True, 85, True) == "high"
    assert rules.level(80, True, False, 0, True) == "high"
    assert rules.level(30, False, False, 0, False) == "low"
    assert rules.level(24, True, True, 100, True) is None


def test_at_most_five_best_first():
    found = [rules.Candidate(i, 30 + i, "low", []) for i in range(8)]
    assert [c.item_id for c in rules.rank(found)] == [7, 6, 5, 4, 3]


def test_attribute_lists_count():
    found = rules.score(Query(model="AB12"), item(name="x", part_no=["ZZ9", "AB-12"]), None)
    assert found.reasons == ["Same model number"]
