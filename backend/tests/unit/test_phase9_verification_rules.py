"""Phase 9 verification probes on the pure post-check (docs/reviews/phase-9-verification.md,
probe 3): odd ids, names that are regular-expression text, short owned names inside words, and
an answer from a turn that never looked (D-137)."""

from app.services import assistant_check as check
from app.services.assistant import _calling

OAT = {"public_id": "ENDR-7K2M9QXA", "name": "Oat Milk", "category": "Food",
       "location": "Kitchen › Fridge", "quantity": 1, "expiry": "expires today"}
ROWS = {OAT["public_id"]: OAT}


def test_an_unknown_id_is_caught_in_lower_case_and_without_the_dash():
    for written in ("It is endr-zzzz9999.", "It is ENDRZZZZ9999.", "It is Endr-zzzz9999."):
        assert check.check(written, ROWS, True, [], "?").replaced == "unknown_id", written
    assert check.check("It is endr7k2m9qxa.", ROWS, True, [], "?").replaced is None


def test_names_that_are_regular_expression_text_are_matched_literally():
    rows = {f"ENDR-0000000{n}": {**OAT, "public_id": f"ENDR-0000000{n}", "name": name}
            for n, name in enumerate(["C++ Primer", "Box (large)", "[Spare] fuse", "a.b"])}
    reply = "C++ Primer, Box (large) and [Spare] fuse; not axb."
    result = check.check(reply, rows, True, [row["name"] for row in rows.values()], "?")
    assert result.replaced is None
    assert [s["text"] for s in result.segments if s["public_id"]] == [
        "C++ Primer", "Box (large)", "[Spare] fuse"]
    assert "".join(s["text"] for s in result.segments) == reply


def test_a_short_owned_name_inside_another_word_is_not_a_name():
    result = check.check("Oat Milk is open.", ROWS, True, ["Pen", "Oat Milk"], "?")
    assert result.replaced is None


def test_an_answer_from_a_turn_that_never_looked_is_the_honest_miss():
    for answer in ("Yes, you have a 13 mm spanner.", "Your Bread is in the kitchen."):
        result = check.check(answer, {}, False, ["Bread"], "Is my Bread here?", looked=False)
        assert (result.reply, result.replaced) == (check.MISS, "no_tool")


def test_the_first_round_must_look_and_the_last_must_answer():
    assert [_calling(n) for n in range(1, 6)] == ["ANY", "AUTO", "AUTO", "AUTO", "NONE"]
