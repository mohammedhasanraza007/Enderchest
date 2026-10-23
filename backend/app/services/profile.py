"""The owner's profile and settings (API.md 2.2). Routes call this; this calls the repositories."""

import json
import sqlite3
from datetime import date

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
# The first-run step marker (D-093). Stored like a setting, never returned as one.
FIRST_RUN_STEP_KEY = "first_run_step"


def _now() -> str:
    return clock.stamp()


def local_today(conn: sqlite3.Connection, user_id: int) -> date:
    """`today` in the owner's time zone (DATA_MODEL 3.1)."""
    row = users_repo.get(conn, user_id)
    return clock.local_date(row["timezone"] if row else "UTC")


def lead_days(conn: sqlite3.Connection, user_id: int) -> int:
    raw = settings_repo.all_values(conn, user_id).get("lead_days")
    try:
        value = json.loads(raw) if raw is not None else None
    except json.JSONDecodeError:
        value = None
    return value if isinstance(value, int) and 1 <= value <= 14 else SETTING_DEFAULTS["lead_days"]


def _first_run_step(conn: sqlite3.Connection, user_id: int, name: str | None) -> str:
    """`name`, then `categories` (P-01 step 2), then `done` (D-084, D-093).

    An owner named before the marker existed has no marker and counts as done.
    """
    if name is None:
        return "name"
    stored = settings_repo.all_values(conn, user_id).get(FIRST_RUN_STEP_KEY)
    return "categories" if stored == json.dumps("categories") else "done"


def get_profile(conn: sqlite3.Connection, user_id: int) -> dict:
    row = users_repo.get(conn, user_id)
    if row is None:  # the single user row is made with the database; it cannot go missing
        raise AppError("not_found", 404, "That does not exist.")
    step = _first_run_step(conn, user_id, row["name"])
    return {"name": row["name"], "timezone": row["timezone"], "theme": row["theme"],
            "first_run_complete": step == "done", "first_run_step": step}


def save_profile(conn: sqlite3.Connection, user_id: int, *, name: str, timezone: str,
                 theme: str | None) -> dict:
    row = users_repo.get(conn, user_id)
    if row is not None and row["name"] is None:
        # The first name ever saved: step 2 comes next. The marker is written before the name,
        # so a crash in between still shows step 1, never skips step 2.
        settings_repo.upsert_many(conn, user_id, {FIRST_RUN_STEP_KEY: json.dumps("categories")},
                                  _now())
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
