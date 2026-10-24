"""Smart capture through the API: local reading, Re-read, Gemini settings and failures
(API 2.8 extract, 2.9; Phase 3 gates 3, 5 and 6; D-100 to D-102).

The label is drawn in memory and Gemini is never reached (its URL is a closed port, or a stand-in
answer replaces the call): these are regression tests, never accuracy or Gemini evidence (D-056).
"""

import json
import os
import stat
import time

import pytest

from app.integrations.gemini import client as gemini_client
from app.services import gemini as gemini_service
from app.services import reading
from tests import imagekit
from tests.conftest import HEADERS, Stack, drain_readings

pytestmark = pytest.mark.integration

LABEL = ["OAT MILK BARISTA", "1 L  MODEL AB-1234X", "MFD 12/01/2026  EXP 14/03/2027",
         "BATCH L4471  Net Qty 500 ml"]
KEY = "AIzaTestKeyThatIsNotReal_0123456789"


def new_draft(stack: Stack, image: bytes | None = None) -> dict:
    files = [("images[]", ("label.jpg", image or imagekit.label_jpeg(LABEL), "image/jpeg"))]
    response = stack.client.post("/api/v1/drafts", headers=HEADERS, files=files)
    assert response.status_code == 201, response.text
    return response.json()["drafts"][0]


def settled(stack: Stack, draft_id: str, timeout: float = 60.0) -> dict:
    """Poll like the confirm screen does until no reading is pending."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        draft = stack.client.get(f"/api/v1/drafts/{draft_id}").json()
        if "pending" not in (draft["ocr_status"], draft["gemini_status"]):
            return draft
        time.sleep(0.1)
    raise AssertionError("the reading never finished")


def extract(stack: Stack, draft_id: str, engine: str):
    return stack.client.post(f"/api/v1/drafts/{draft_id}/extract", json={"engine": engine},
                             headers=HEADERS)


def set_settings(stack: Stack, **values) -> None:
    response = stack.client.patch("/api/v1/settings", json=values, headers=HEADERS)
    assert response.status_code == 200, response.text


def test_a_new_draft_is_read_and_proposals_never_touch_the_fields(stack: Stack):
    created = new_draft(stack)
    assert created["ocr_status"] == "pending"
    draft = settled(stack, created["id"])
    assert draft["ocr_status"] == "done", draft
    proposed = draft["proposed"]
    assert proposed["name"]["value"] == "Oat Milk Barista"
    assert proposed["model"]["value"] == "AB-1234X"
    assert proposed["size"]["value"] == "500 ml"
    assert proposed["expiry_date"]["value"] == "2027-03-14"
    assert all(p["source"] == "ocr" for p in proposed.values())
    assert "EXP 14/03/2027" in draft["raw_text"]
    assert draft["ocr_info"]["engine"].startswith("RapidOCR")
    assert draft["fields"] == {}  # D-100: the owner's fields stay the owner's


def test_reread_answers_202_and_queues_one_reading_at_a_time(stack: Stack):
    draft = settled(stack, new_draft(stack)["id"])
    first = extract(stack, draft["id"], "local")
    second = extract(stack, draft["id"], "local")
    assert (first.status_code, first.json()) == (202, {"ocr_status": "pending"})
    assert second.status_code == 202
    assert settled(stack, draft["id"])["ocr_status"] == "done"


def test_a_photo_with_no_text_is_done_with_a_note(stack: Stack):
    draft = settled(stack, new_draft(stack, imagekit.jpeg())["id"])
    assert (draft["ocr_status"], draft["proposed"]) == ("done", {})
    assert draft["read_notes"] == ["No text was found in the photo."]


def test_a_reading_lost_in_a_restart_shows_as_interrupted(stack: Stack):
    draft = settled(stack, new_draft(stack)["id"])
    conn = stack.manager.open_connection()
    conn.execute("UPDATE drafts SET ocr_status = 'pending' WHERE id = ?", (draft["id"],))
    conn.close()
    shown = stack.client.get(f"/api/v1/drafts/{draft['id']}").json()
    assert (shown["ocr_status"], shown["ocr_error"]) == ("failed", reading.INTERRUPTED)
    assert extract(stack, draft["id"], "local").status_code == 202
    assert settled(stack, draft["id"])["ocr_status"] == "done"


def test_extract_on_a_committed_or_unknown_draft_is_refused(stack: Stack):
    assert extract(stack, "no-such-draft", "local").status_code == 404
    draft = settled(stack, new_draft(stack)["id"])
    stack.client.patch(f"/api/v1/drafts/{draft['id']}",
                       json={"fields": {"name": "Milk", "expiry_mode": "none"}}, headers=HEADERS)
    assert stack.client.post(f"/api/v1/drafts/{draft['id']}/commit",
                             headers=HEADERS).status_code == 201
    assert extract(stack, draft["id"], "local").json()["error"]["code"] == "conflict"
    bad = stack.client.post(f"/api/v1/drafts/{draft['id']}/extract", json={"engine": "magic"},
                            headers=HEADERS)
    assert bad.status_code == 422


def test_health_stays_fast_while_two_readings_queue(stack: Stack):
    """Gate 5 (regression form; probe 21 measures the real stack)."""
    first, second = new_draft(stack), new_draft(stack)
    slowest = 0.0
    while "pending" in (stack.client.get(f"/api/v1/drafts/{second['id']}").json()["ocr_status"],
                        stack.client.get(f"/api/v1/drafts/{first['id']}").json()["ocr_status"]):
        started = time.perf_counter()
        assert stack.client.get("/health").status_code == 200
        slowest = max(slowest, time.perf_counter() - started)
        time.sleep(0.05)
    assert slowest < 0.2
    assert {settled(stack, d["id"])["ocr_status"] for d in (first, second)} == {"done"}


# ---- Gemini settings and the key (API 2.9, DATA_SAFETY 2) --------------------------------------

def test_the_key_is_write_only_owner_only_and_never_backed_up(stack: Stack):
    assert stack.client.get("/api/v1/gemini").json() == {
        "key_set": False, "model": "gemini-3.5-flash-lite", "mode": "off", "share_images": False}
    refused = stack.client.put("/api/v1/gemini/key", json={"key": "short"}, headers=HEADERS)
    assert refused.json()["error"]["details"]["problems"][0]["field"] == "key"
    saved = stack.client.put("/api/v1/gemini/key", json={"key": f"  {KEY}\n"}, headers=HEADERS)
    assert saved.json() == {"key_set": True}
    path = stack.settings.secrets_dir / "gemini.key"
    assert path.read_text() == KEY
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    shown = stack.client.get("/api/v1/gemini")
    assert shown.json()["key_set"] is True and KEY not in shown.text
    backup = stack.post("/api/v1/backups")
    assert backup.status_code == 201, backup.text
    for file in stack.settings.backups_dir.rglob("*"):
        assert not file.is_file() or KEY.encode() not in file.read_bytes()
    assert stack.client.delete("/api/v1/gemini/key", headers=HEADERS).status_code == 204
    assert stack.client.get("/api/v1/gemini").json()["key_set"] is False


def test_the_model_name_cannot_reshape_the_url(stack: Stack):
    for bad in ("../../other", "model?key=x", "", "a b"):
        response = stack.client.patch("/api/v1/settings", json={"gemini_model": bad},
                                      headers=HEADERS)
        assert response.status_code == 422, bad


def test_gemini_off_or_without_a_key_is_refused_plainly(stack: Stack):
    draft = settled(stack, new_draft(stack)["id"])
    off = extract(stack, draft["id"], "gemini")
    assert (off.status_code, off.json()["error"]["code"]) == (409, "gemini_disabled")
    set_settings(stack, gemini_mode="ask")
    assert extract(stack, draft["id"], "gemini").json()["error"]["code"] == "gemini_disabled"
    no_key = stack.post("/api/v1/gemini/test")
    assert (no_key.status_code, no_key.json()["error"]["code"]) == (409, "gemini_disabled")


def test_gemini_unreachable_is_a_clear_message_and_the_local_result_stays(stack: Stack):
    """Gate 3: no network for Gemini. The test URL is a closed port on this machine."""
    draft = settled(stack, new_draft(stack)["id"])
    stack.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
    set_settings(stack, gemini_mode="ask")
    test = stack.post("/api/v1/gemini/test")
    assert (test.status_code, test.json()["error"]["code"]) == (502, "upstream_unavailable")
    assert "could not be reached" in test.json()["error"]["message"]
    assert extract(stack, draft["id"], "gemini").json() == {"gemini_status": "pending"}
    after = settled(stack, draft["id"])
    assert after["gemini_status"] == "failed"
    assert "could not be reached" in after["gemini_error"]
    assert after["proposed"] == draft["proposed"]  # the local reading is untouched


def test_gemini_fills_only_weak_or_missing_fields(stack: Stack, monkeypatch):
    """D-101 with a stand-in answer (never Gemini evidence)."""
    sent = {}

    def answer(base_url, model, key, text, images, transport=None):
        sent.update(model=model, key=key, text=text, images=len(images))
        return gemini_client.GeminiValues(
            name="Something else", brand="Oatly", model=None, size="1 L", category="Food",
            expiry_text="EXP 03/04/2027", inspection_interval_days=None), 812

    monkeypatch.setattr(gemini_client, "extract", answer)
    stack.post("/api/v1/categories", json={"name": "Food"})
    draft = settled(stack, new_draft(stack)["id"])
    stack.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
    set_settings(stack, gemini_mode="ask")
    extract(stack, draft["id"], "gemini")
    after = settled(stack, draft["id"])
    assert after["gemini_status"] == "done", after
    assert sent == {"model": "gemini-3.5-flash-lite", "key": KEY, "images": 0,
                    "text": after["raw_text"].replace("\n\n", "\n")}
    proposed = after["proposed"]
    assert proposed["name"]["source"] == "ocr"  # the photo reading was sure
    assert proposed["brand"] == {"value": "Oatly", "source": "gemini", "confidence": "medium",
                                 "flags": ["unverified"]}
    assert proposed["category_id"]["source"] == "gemini"
    assert proposed["expiry_date"]["source"] == "ocr"
    assert after["gemini_values"]["expiry_text"] == "EXP 03/04/2027"


def test_photos_go_to_gemini_only_when_sharing_is_on(stack: Stack, monkeypatch):
    sent = []

    def answer(base_url, model, key, text, images, transport=None):
        sent.append(images)
        return gemini_client.GeminiValues(), 5

    monkeypatch.setattr(gemini_client, "extract", answer)
    stack.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
    set_settings(stack, gemini_mode="ask")
    draft = settled(stack, new_draft(stack)["id"])
    extract(stack, draft["id"], "gemini")
    settled(stack, draft["id"])
    set_settings(stack, share_images_with_gemini=True)
    extract(stack, draft["id"], "gemini")
    settled(stack, draft["id"])
    assert [len(images) for images in sent] == [0, 1]
    assert sent[1][0][:2] == b"\xff\xd8"  # a fresh JPEG, re-encoded without metadata


def test_auto_mode_asks_only_when_the_photo_gave_no_name_or_model(stack: Stack, monkeypatch):
    calls = []
    monkeypatch.setattr(gemini_client, "extract",
                        lambda *args, **kwargs: (calls.append(1), (gemini_client.GeminiValues(
                            name="Blue tin"), 5))[1])
    stack.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
    set_settings(stack, gemini_mode="auto", share_images_with_gemini=True)
    labelled = new_draft(stack)
    drain_readings()
    assert settled(stack, labelled["id"])["gemini_status"] == "skipped"
    blank = new_draft(stack, imagekit.jpeg())
    drain_readings()
    after = settled(stack, blank["id"])
    assert (after["gemini_status"], len(calls)) == ("done", 1)
    assert after["proposed"]["name"]["value"] == "Blue tin"


def test_the_stored_answer_holds_no_key(stack: Stack, monkeypatch):
    monkeypatch.setattr(gemini_client, "extract",
                        lambda *args, **kwargs: (gemini_client.GeminiValues(name="Tin"), 5))
    stack.client.put("/api/v1/gemini/key", json={"key": KEY}, headers=HEADERS)
    set_settings(stack, gemini_mode="ask")
    draft = settled(stack, new_draft(stack)["id"])
    extract(stack, draft["id"], "gemini")
    settled(stack, draft["id"])
    conn = stack.manager.open_connection()
    row = conn.execute("SELECT gemini_result, ocr_result FROM drafts WHERE id = ?",
                       (draft["id"],)).fetchone()
    conn.close()
    assert KEY not in row["gemini_result"] and KEY not in row["ocr_result"]
    assert json.loads(row["gemini_result"])["model"] == "gemini-3.5-flash-lite"
    assert gemini_service.read_key(stack.settings) == KEY
