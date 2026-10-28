"""Final UX test (owner, 2026-10-28): "do I own a controller, what is its price" found nothing.
The owner's controller is called "Supernova" and only its note says "controller"; word search
matched names, ids and attribute values but never notes (D-140). And a price question got
"I couldn't find that": prices never leave the laptop (D-134), so the assistant must say so and
name the item instead. Gemini is the recorded stand-in, never evidence of real answers (D-056).
"""

import pytest

from tests import gemini_fake as fake
from tests.conftest import HEADERS, Stack
from tests.integration.test_assistant import ROW_KEYS, ask, gemini, household, item, tool_rows

pytestmark = pytest.mark.integration
__all__ = ["gemini"]  # the shared fixture, used through `indirect=True`

NOTE = "controller, a gift from Ayaan"
PRICE = 179900


def _controller(stack: Stack) -> str:
    return item(stack, "Supernova", notes=NOTE, price_paise=PRICE,
                attributes={"brand": "ANT ESPORTS"})


def test_inventory_search_finds_a_word_in_the_notes(stack: Stack):
    supernova = _controller(stack)
    item(stack, "Desk lamp", notes="for the study")
    found = stack.client.get("/api/v1/items", params={"q": "controller"}, headers=HEADERS)
    assert found.status_code == 200, found.text
    assert [row["public_id"] for row in found.json()["items"]] == [supernova]


@pytest.mark.parametrize("gemini", [(fake.call("search_items", {"q": "controller"}),
                                     fake.text("Yes: Supernova. Prices stay on this laptop, so "
                                               "open Supernova to see what you paid."))],
                         indirect=True)
def test_the_assistant_finds_the_controller_and_no_note_or_price_leaves(gemini):
    stack, stand_in = gemini
    household(stack)
    supernova = _controller(stack)
    answer = ask(stack, "do i own s controller if what is its price").json()
    assert answer["cited"] == [{"public_id": supernova, "name": "Supernova"}]
    rows = tool_rows(stand_in.requests[1])
    assert [row["name"] for row in rows] == ["Supernova"]
    assert all(set(row) == ROW_KEYS for row in rows)
    everything = "\n".join(r["raw"] for r in stand_in.requests)
    for private in ("gift from Ayaan", str(PRICE), "1,799", "ANT ESPORTS"):
        assert private not in everything, private


@pytest.mark.parametrize("gemini", [(fake.call("search_items", {"q": "Supernova"}),
                                     fake.text("Supernova."))], indirect=True)
def test_a_price_question_shows_the_saved_price_from_this_laptop_only(gemini):
    stack, stand_in = gemini
    household(stack)
    supernova = _controller(stack)
    answer = ask(stack, "check its price").json()
    assert answer["prices"] == [{"public_id": supernova, "name": "Supernova",
                                 "price_paise": PRICE}]
    system = str(stand_in.requests[0]["body"]["systemInstruction"])
    assert "Prices stay on this laptop" in system
    assert "notes" in system
    everything = "\n".join(r["raw"] for r in stand_in.requests)
    assert str(PRICE) not in everything


@pytest.mark.parametrize("gemini", [(fake.call("search_items", {"q": "Supernova"}),
                                     fake.text("Supernova."))], indirect=True)
def test_any_other_question_shows_no_prices(gemini):
    stack, _stand_in = gemini
    household(stack)
    _controller(stack)
    assert ask(stack, "where is Supernova").json()["prices"] == []


@pytest.mark.parametrize("gemini", [(fake.call("search_items", {"q": "lamp"}),
                                     fake.text("Desk lamp."))], indirect=True)
def test_an_item_without_a_price_says_so(gemini):
    stack, _stand_in = gemini
    household(stack)
    lamp = item(stack, "Desk lamp")
    assert ask(stack, "how much did my lamp cost").json()["prices"] == [
        {"public_id": lamp, "name": "Desk lamp", "price_paise": None}]
