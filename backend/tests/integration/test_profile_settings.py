"""GET and PUT /profile, GET and PATCH /settings (API.md 2.2, DATA_MODEL 2.2 and 2.3)."""

import pytest

from app.config import Settings
from tests.conftest import HEADERS, Stack

pytestmark = pytest.mark.integration

DEFAULTS = {
    "lead_days": 3,
    "coach_enabled": True,
    "gemini_mode": "off",
    "gemini_model": "gemini-3.5-flash-lite",  # D-102
    "share_images_with_gemini": False,
    "assistant_share_item_text": False,
}


def put_profile(stack: Stack, body: dict):
    return stack.client.put("/api/v1/profile", json=body, headers=HEADERS)


def patch_settings(stack: Stack, body: dict):
    return stack.client.patch("/api/v1/settings", json=body, headers=HEADERS)


def problems(response) -> list[str]:
    return [p["field"] for p in response.json()["error"]["details"]["problems"]]


# ----- profile ------------------------------------------------------------------------------

def test_a_new_database_has_no_name_and_first_run_is_not_complete(stack: Stack):
    body = stack.client.get("/api/v1/profile").json()
    assert body == {"name": None, "timezone": "UTC", "theme": "system", "first_run_complete": False,
                    "first_run_step": "name"}


def test_the_first_name_leads_to_step_2_and_survives_a_read(stack: Stack):
    """D-093: saving the first name stores the step marker, so a reopened tab resumes at step 2."""
    response = put_profile(stack, {"name": "  Mohammed  ", "timezone": "Asia/Kolkata"})
    assert response.status_code == 200
    expected = {"name": "Mohammed", "timezone": "Asia/Kolkata", "theme": "system",
                "first_run_complete": False, "first_run_step": "categories"}
    assert response.json() == expected
    assert stack.client.get("/api/v1/profile").json() == expected


def test_finishing_step_2_completes_first_run_and_a_later_save_keeps_it(stack: Stack):
    put_profile(stack, {"name": "Mohammed", "timezone": "Asia/Kolkata"})
    assert patch_settings(stack, {"first_run_step": "done"}).status_code == 200
    profile = stack.client.get("/api/v1/profile").json()
    assert (profile["first_run_complete"], profile["first_run_step"]) == (True, "done")
    put_profile(stack, {"name": "Mo", "timezone": "Asia/Kolkata"})
    assert stack.client.get("/api/v1/profile").json()["first_run_step"] == "done"
    assert "first_run_step" not in stack.client.get("/api/v1/settings").json()


@pytest.mark.parametrize("value", ["categories", "name", None, True])
def test_only_done_can_be_written_as_the_first_run_step(stack: Stack, value):
    assert patch_settings(stack, {"first_run_step": value}).status_code == 422


def test_an_owner_named_before_the_marker_existed_is_not_sent_back(stack: Stack):
    """A Phase 1 database: the name is set and there is no marker at all."""
    conn = stack.manager.db()
    conn.execute("UPDATE users SET name = 'Mohammed' WHERE id = 1")
    profile = stack.client.get("/api/v1/profile").json()
    assert (profile["first_run_complete"], profile["first_run_step"]) == (True, "done")


def test_a_theme_is_stored_and_kept_when_a_later_save_leaves_it_out(stack: Stack):
    put_profile(stack, {"name": "Mohammed", "timezone": "UTC", "theme": "dark"})
    again = put_profile(stack, {"name": "Mo", "timezone": "Asia/Kolkata"})
    assert again.json()["theme"] == "dark"


@pytest.mark.parametrize("body, field", [
    ({"timezone": "UTC"}, "name"),
    ({"name": "", "timezone": "UTC"}, "name"),
    ({"name": "   ", "timezone": "UTC"}, "name"),
    ({"name": "x" * 41, "timezone": "UTC"}, "name"),
    ({"name": "bad\x07name", "timezone": "UTC"}, "name"),
    ({"name": "Mo"}, "timezone"),
    ({"name": "Mo", "timezone": "Mars/Olympus"}, "timezone"),
    ({"name": "Mo", "timezone": "../etc/passwd"}, "timezone"),
    ({"name": "Mo", "timezone": "UTC", "theme": "purple"}, "theme"),
    ({"name": "Mo", "timezone": "UTC", "colour": "red"}, "colour"),
])
def test_a_bad_profile_is_refused_and_nothing_is_saved(stack: Stack, body: dict, field: str):
    response = put_profile(stack, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert field in problems(response)
    assert stack.client.get("/api/v1/profile").json()["name"] is None


def test_a_forty_character_name_is_accepted(stack: Stack):
    assert put_profile(stack, {"name": "x" * 40, "timezone": "UTC"}).status_code == 200


def test_saving_the_profile_needs_the_safety_header(stack: Stack):
    response = stack.client.put("/api/v1/profile", json={"name": "Mo", "timezone": "UTC"})
    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden_host")


def test_the_profile_is_locked_when_the_data_volume_is_missing(settings: Settings):
    with Stack(settings, is_mount=lambda p: False) as stack:
        response = stack.client.get("/api/v1/profile")
        assert (response.status_code, response.json()["error"]["code"]) == (503, "locked")


# ----- settings -----------------------------------------------------------------------------

def test_settings_come_back_with_every_default_filled(stack: Stack):
    assert stack.client.get("/api/v1/settings").json() == DEFAULTS


def test_a_partial_patch_changes_only_what_it_names_and_persists(stack: Stack):
    response = patch_settings(stack, {"lead_days": 7, "coach_enabled": False})
    assert response.status_code == 200
    assert response.json() == {**DEFAULTS, "lead_days": 7, "coach_enabled": False}
    assert stack.client.get("/api/v1/settings").json() == response.json()
    patch_settings(stack, {"gemini_mode": "ask"})
    assert stack.client.get("/api/v1/settings").json()["lead_days"] == 7


def test_an_empty_patch_changes_nothing(stack: Stack):
    assert patch_settings(stack, {}).json() == DEFAULTS


@pytest.mark.parametrize("body, field", [
    ({"lead_days": 0}, "lead_days"),
    ({"lead_days": 15}, "lead_days"),
    ({"lead_days": "three"}, "lead_days"),
    ({"coach_enabled": "yes"}, "coach_enabled"),
    ({"gemini_mode": "sometimes"}, "gemini_mode"),
    ({"lead_days": None}, "lead_days"),
    ({"favourite_colour": "clay"}, "favourite_colour"),
])
def test_a_bad_settings_patch_is_refused_whole(stack: Stack, body: dict, field: str):
    # A valid change rides along, to prove a refused patch is not half applied.
    response = patch_settings(stack, {"share_images_with_gemini": True, **body})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert field in problems(response)
    assert stack.client.get("/api/v1/settings").json() == DEFAULTS  # nothing was half-applied


def test_the_gemini_model_default_comes_from_the_environment(settings: Settings):
    configured = Settings(env=settings.env, port=settings.port, data_dir=settings.data_dir,
                          backups_dir=settings.backups_dir, backup_dir_hint="x",
                          gemini_model_default="a-model-name")
    with Stack(configured) as stack:
        assert stack.client.get("/api/v1/settings").json()["gemini_model"] == "a-model-name"
        patch_settings(stack, {"gemini_model": "another"})
        assert stack.client.get("/api/v1/settings").json()["gemini_model"] == "another"
