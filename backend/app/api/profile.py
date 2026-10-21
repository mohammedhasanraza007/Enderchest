"""GET and PUT /profile, GET and PATCH /settings (API.md 2.2)."""

import sqlite3

from fastapi import APIRouter, Depends

from ..boot.manager import BootManager
from ..schemas.profile import Profile, ProfileUpdate, SettingsPatch, SettingsView
from ..services import profile as profile_service
from .deps import current_user_id, get_db, require_ok

router = APIRouter(prefix="/api/v1")


@router.get("/profile")
def get_profile(conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> Profile:
    return Profile(**profile_service.get_profile(conn, user_id))


@router.put("/profile")
def put_profile(body: ProfileUpdate, conn: sqlite3.Connection = Depends(get_db),
                user_id: int = Depends(current_user_id)) -> Profile:
    saved = profile_service.save_profile(conn, user_id, name=body.name, timezone=body.timezone,
                                         theme=body.theme)
    return Profile(**saved)


@router.get("/settings")
def get_settings(manager: BootManager = Depends(require_ok),
                 conn: sqlite3.Connection = Depends(get_db),
                 user_id: int = Depends(current_user_id)) -> SettingsView:
    values = profile_service.get_settings(conn, user_id, manager.settings.gemini_model_default)
    return SettingsView(**values)


@router.patch("/settings")
def patch_settings(body: SettingsPatch, manager: BootManager = Depends(require_ok),
                   conn: sqlite3.Connection = Depends(get_db),
                   user_id: int = Depends(current_user_id)) -> SettingsView:
    values = profile_service.change_settings(
        conn, user_id, body.model_dump(exclude_unset=True), manager.settings.gemini_model_default)
    return SettingsView(**values)
