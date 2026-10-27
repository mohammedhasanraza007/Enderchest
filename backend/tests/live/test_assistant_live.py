"""Phase 9 gates 1 to 3 against the REAL Gemini (owner-run; skipped without GEMINI_API_KEY).

Runs on a throwaway in-process stack with test data, never the live app. The owner supplies the
key in the environment; it is written only to the throwaway data folder and never printed:

  docker run --rm -e GEMINI_API_KEY -v <repo>/backend:/app -w /app enderchest-tools:latest \
      pytest -q -s tests/live
"""

import dataclasses
import os

import pytest

from app.config import DEFAULT_GEMINI_URL
from tests.conftest import HEADERS, Stack
from tests.integration.test_assistant import MISS, ask, household

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
pytestmark = pytest.mark.skipif(not KEY, reason="needs the owner's GEMINI_API_KEY")


@pytest.fixture
def real(settings):
    with Stack(dataclasses.replace(settings, gemini_url=DEFAULT_GEMINI_URL)) as running:
        household(running)
        running.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
        yield running


def test_real_what_expires_this_week(real):
    answer = ask(real, "What expires this week?").json()
    print("\nexpires:", answer)
    assert {c["name"] for c in answer["cited"]} == {"Oat Milk", "Greek Yogurt", "Baby Spinach"}


def test_real_trap_absent_spanner(real):
    answer = ask(real, "Do I have a 13 mm spanner?").json()
    print("\ntrap:", answer)
    assert answer["reply"] == MISS or not answer["cited"]


def test_real_bad_key(real):
    real.client.put("/api/v1/gemini/key", json={"key": "AIzaThisKeyIsWrong_0123456789"},
                    headers=HEADERS)
    response = ask(real, "What expires this week?")
    assert response.status_code == 502 and "key" in response.json()["error"]["message"]
