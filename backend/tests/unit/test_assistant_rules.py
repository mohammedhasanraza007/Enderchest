"""The assistant's pure rules (Phase 9): the post-check, the links, the row shape and the
function-calling client against a stand-in transport. Regression only: real answers are the
owner's gate (tests/live)."""

import json
from datetime import date

import httpx
import pytest

from app.integrations.gemini import client
from app.services import assistant_check as check
from app.services.assistant_tools import row_view

BASE = "https://gemini.test/v1beta"
KEY = "AIzaTestKeyThatIsNotReal_0123456789"
OAT = {"public_id": "ENDR-7K2M9QXA", "name": "Oat Milk", "category": "Food",
       "location": "Kitchen › Fridge", "quantity": 1, "expiry": "expires today"}
SPANNER = {"public_id": "ENDR-4H8P2RTW", "name": "Spanner 13 mm", "category": "Tools",
           "location": "Garage", "quantity": 1, "expiry": "no expiry"}
ROWS = {row["public_id"]: row for row in (OAT, SPANNER)}
NAMES = ["Oat Milk", "Spanner 13 mm", "Greek Yogurt", "TV"]


def test_an_answer_naming_only_this_turns_rows_is_kept_and_linked():
    result = check.check("Oat Milk is in Kitchen › Fridge; it expires today.", ROWS, True,
                         NAMES, "What expires today?")
    assert result.replaced is None
    assert result.segments[0] == {"text": "Oat Milk", "public_id": OAT["public_id"]}
    assert result.cited == [{"public_id": OAT["public_id"], "name": "Oat Milk"}]


def test_a_search_with_no_rows_is_always_the_honest_miss():
    result = check.check("Yes, you have a drill in the garage.", {}, True, NAMES,
                         "Do I have a drill?")
    assert (result.reply, result.replaced) == (check.MISS, "nothing_found")
    assert result.segments == [{"text": check.MISS, "public_id": None}]


def test_an_id_that_no_tool_returned_replaces_the_answer():
    result = check.check("It is ENDR-ZZZZ9999.", ROWS, True, NAMES, "Where is it?")
    assert result.replaced == "unknown_id"


def test_an_owned_name_outside_the_rows_replaces_the_answer():
    result = check.check("Oat Milk and Greek Yogurt expire soon.", {"x": OAT}, True, NAMES,
                         "What expires?")
    assert result.replaced == "name_outside_rows"


def test_the_question_and_row_text_exempt_a_name():
    asked = check.check("No Greek Yogurt here, only Oat Milk.", {"x": OAT}, True, NAMES,
                        "Do I have greek yogurt?")
    assert asked.replaced is None
    inside = check.check("Your Milk is fine.", {"x": OAT}, True, ["Milk", *NAMES], "Milk?")
    assert inside.replaced is None


def test_short_names_never_match_ordinary_words():
    result = check.check("Oat Milk is next to the TV stand.", {"x": OAT}, True, NAMES, "?")
    assert result.replaced is None


def test_a_count_with_no_search_may_answer_zero():
    result = check.check("You have 0 tools.", {}, False, NAMES, "How many tools?")
    assert result.replaced is None and result.segments == [{"text": "You have 0 tools.",
                                                            "public_id": None}]


def test_links_prefer_the_longest_name_and_cite_each_item_once():
    rows = {"a": {**OAT, "public_id": "ENDR-AAAAAAAA", "name": "Milk"}, "b": OAT}
    segments, cited = check.link("Oat Milk, then Milk, then oat milk.", rows)
    linked = [(s["text"], s["public_id"]) for s in segments if s["public_id"]]
    assert linked == [("Oat Milk", OAT["public_id"]), ("Milk", "ENDR-AAAAAAAA"),
                      ("oat milk", OAT["public_id"])]
    assert [c["public_id"] for c in cited] == [OAT["public_id"], "ENDR-AAAAAAAA"]
    assert "".join(s["text"] for s in segments) == "Oat Milk, then Milk, then oat milk."


def test_a_long_answer_is_cut():
    result = check.check("x" * 5000, {}, False, [], "?")
    assert len(result.reply) == check.REPLY_MAX and result.reply.endswith("…")


def test_row_view_carries_only_the_allowed_fields():
    row = {"public_id": "ENDR-7K2M9QXA", "name": "Oat Milk", "category_name": "Food",
           "location_id": 3, "quantity": 2, "expiry_mode": "date", "expiry_date": "2026-10-30",
           "notes": "secret", "price_paise": 9900}
    view = row_view(row, {3: ["Kitchen", "Fridge"]}, date(2026, 10, 28), 7)
    assert view == {"public_id": "ENDR-7K2M9QXA", "name": "Oat Milk", "category": "Food",
                    "location": "Kitchen › Fridge", "quantity": 2, "expiry": "2 days left"}
    assert row_view({**row, "location_id": None}, {}, date(2026, 10, 28), 7)["location"] is None


def replying(status: int, body: object, seen: list):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handle)


def test_converse_sends_tools_and_returns_the_content_verbatim():
    parts = [{"functionCall": {"name": "search_items", "args": {"q": "milk"}, "id": "c1"},
              "thoughtSignature": "sig"}]
    seen: list[httpx.Request] = []
    content = client.converse(BASE, "m", KEY, system="S", contents=[{"role": "user",
                              "parts": [{"text": "milk?"}]}], tools=[{"name": "search_items"}],
                              calling="NONE",
                              transport=replying(200, {"candidates": [{"content": {
                                  "parts": parts}}]}, seen))
    assert content == {"role": "model", "parts": parts}
    body = json.loads(seen[0].content)
    assert body["toolConfig"]["functionCallingConfig"]["mode"] == "NONE"
    assert body["systemInstruction"]["parts"][0]["text"] == "S"
    assert seen[0].headers["x-goog-api-key"] == KEY
    assert client.function_calls(content) == [{"name": "search_items", "args": {"q": "milk"},
                                               "id": "c1"}]


@pytest.mark.parametrize(("status", "body", "words"), [
    (401, {}, "did not accept the key"),
    (404, {}, "does not know the model"),
    (429, {}, "limit"),
    (200, {"promptFeedback": {"blockReason": "SAFETY"}}, "declined"),
    (200, {"candidates": []}, "empty answer"),
    (200, {"candidates": [{"content": {"parts": "x"}}]}, "unexpected shape"),
])
def test_converse_failures_keep_plain_words(status, body, words):
    with pytest.raises(client.GeminiError, match=words):
        client.converse(BASE, "m", KEY, system="S", contents=[], tools=[],
                        transport=replying(status, body, []))


def test_answer_text_drops_thoughts_and_calls_without_names():
    content = {"parts": [{"text": "hidden", "thought": True}, {"text": "Oat "},
                         {"functionCall": {"args": {}}}, {"text": "Milk"}]}
    assert client.answer_text(content) == "Oat Milk"
    assert client.function_calls(content) == []
