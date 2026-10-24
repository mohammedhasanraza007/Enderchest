"""The Gemini REST call against a stand-in transport: the request it sends and how every kind
of failure reads (D-102). Regression only: the real round trip is the owner's gate 4."""

import json

import httpx
import pytest

from app.integrations.gemini import client

BASE = "https://gemini.test/v1beta"
KEY = "AIzaTestKeyThatIsNotReal_0123456789"
ANSWER = {"name": "Oat milk", "brand": "Oatly", "model": None, "size": "1 L",
          "category": "Food", "expiry_text": "EXP 14/03/2027", "inspection_interval_days": None}


def replying(status: int = 200, body: object = None, seen: list | None = None):
    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handle)


def answer_body(values: object) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(values)}]}}]}


def test_the_request_carries_the_key_in_a_header_and_asks_for_strict_json():
    seen: list[httpx.Request] = []
    values, _ = client.extract(BASE, "gemini-3.5-flash-lite", KEY, "OAT MILK\nEXP 14/03/2027",
                               [b"\xff\xd8jpeg"], transport=replying(200, answer_body(ANSWER),
                                                                    seen))
    assert values.name == "Oat milk" and values.model is None
    request = seen[0]
    assert str(request.url) == f"{BASE}/models/gemini-3.5-flash-lite:generateContent"
    assert request.headers["x-goog-api-key"] == KEY and KEY not in str(request.url)
    body = json.loads(request.content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"]["required"] == list(ANSWER)
    parts = body["contents"][0]["parts"]
    assert "EXP 14/03/2027" in parts[0]["text"]
    assert parts[1]["inline_data"]["mime_type"] == "image/jpeg"


def test_text_only_sends_no_image_part():
    seen: list[httpx.Request] = []
    client.extract(BASE, "m", KEY, "text", [], transport=replying(200, answer_body(ANSWER), seen))
    assert len(json.loads(seen[0].content)["contents"][0]["parts"]) == 1


@pytest.mark.parametrize(("status", "body", "words"), [
    (400, {"error": {"message": "API key not valid. Please pass a valid API key."}},
     "did not accept the key"),
    (403, {"error": {"message": "denied"}}, "did not accept the key"),
    (404, {"error": {"message": "not found"}}, 'does not know the model "m"'),
    (429, {"error": {"message": "quota"}}, "limit for this key is used up"),
    (500, {"error": {"message": "boom"}}, "problem on its side"),
    (400, {"error": {"message": "Invalid JSON payload"}}, "refused the request: Invalid JSON"),
    (200, {"promptFeedback": {"blockReason": "SAFETY"}}, "declined to answer (SAFETY)"),
    (200, {"candidates": []}, "empty answer"),
    (200, answer_body("not an object"), "expected fields"),
    (200, answer_body({**ANSWER, "inspection_interval_days": 0}), "expected fields"),
    (200, {"candidates": [{"content": {"parts": [{"text": "{not json"}]}}]}, "expected fields"),
])
def test_every_failure_has_a_plain_message(status, body, words):
    with pytest.raises(client.GeminiError) as failed:
        client.extract(BASE, "m", KEY, "text", [], transport=replying(status, body))
    assert words in failed.value.message
    assert KEY not in failed.value.message


def test_no_network_and_a_timeout_read_plainly():
    def offline(request):
        raise httpx.ConnectError("no route", request=request)

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(client.GeminiError, match="could not be reached"):
        client.ping(BASE, "m", KEY, transport=httpx.MockTransport(offline))
    with pytest.raises(client.GeminiError, match="within 20 seconds"):
        client.ping(BASE, "m", KEY, transport=httpx.MockTransport(slow))


def test_ping_reports_the_time_taken():
    assert client.ping(BASE, "m", KEY, transport=replying(200, answer_body("OK"))) >= 0
