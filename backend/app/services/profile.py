"""The owner's profile and settings (API.md 2.2). Routes call this; this calls the repositories."""

import json
import sqlite3

from .. import clock
from ..errors import AppError
from ..repositories import settings as settings_repo
from ..repositories import users as users_repo

# DATA_MODEL 2.3. `gemini_model` is the one default that comes from the environment.
SETTING_DEFAULTS: dict[str, object] = {
    "lead_days": 3,
    "coach_enabled": True,
    "gemini_mode": "off",
    "share_images_with_gemini": False,
    "assistant_share_item_text": False,
}


def _now() -> str:
    return clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def get_profile(conn: sqlite3.Connection, user_id: int) -> dict:
    row = users_repo.get(conn, user_id)
    if row is None:  # the single user row is made with the database; it cannot go missing
        raise AppError("not_found", 404, "That does not exist.")
    # First run is complete once a name is saved (D-084): the welcome screen is for the name.
    return {"name": row["name"], "timezone": row["timezone"], "theme": row["theme"],
            "first_run_complete": row["name"] is not None}


def save_profile(conn: sqlite3.Connection, user_id: int, *, name: str, timezone: str,
                 theme: str | None) -> dict:
    users_repo.update_profile(conn, user_id, name=name, timezone=timezone, theme=theme,
                              now=_now())
    return get_profile(conn, user_id)


def get_settings(conn: sqlite3.Connection, user_id: int, gemini_model_default: str) -> dict:
    """Every setting, with the default filled in for keys never written."""
    result = {**SETTING_DEFAULTS, "gemini_model": gemini_model_default}
    for key, raw in settings_repo.all_values(conn, user_id).items():
        if key in result:  # unknown stored keys are ignored, never returned
            try:
                result[key] = json.loads(raw)
            except json.JSONDecodeError:
                pass  # a damaged value falls back to the default instead of failing the page
    return result


def change_settings(conn: sqlite3.Connection, user_id: int, changes: dict,
                    gemini_model_default: str) -> dict:
    if changes:
        settings_repo.upsert_many(
            conn, user_id, {key: json.dumps(value) for key, value in changes.items()}, _now())
    return get_settings(conn, user_id, gemini_model_default)
