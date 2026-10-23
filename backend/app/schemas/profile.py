"""Request and response shapes for /profile and /settings (API.md 2.2, DATA_MODEL 2.2 and 2.3).

These models are also the source of the generated frontend types, so every field is explicit.
"""

import unicodedata
from functools import cache
from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

Theme = Literal["system", "light", "dark"]
GeminiMode = Literal["off", "ask", "auto"]

NAME_MAX = 40  # P-01: a name is 1 to 40 characters


@cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones())


class Profile(BaseModel):
    name: str | None
    timezone: str
    theme: Theme
    first_run_complete: bool
    first_run_step: Literal["name", "categories", "done"]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    timezone: str
    theme: Theme | None = None  # left out: the stored theme stays

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= NAME_MAX:
            raise PydanticCustomError("name_length", "Enter a name of 1 to 40 characters.")
        if any(unicodedata.category(ch) == "Cc" for ch in value):
            raise PydanticCustomError("name_chars", "A name cannot contain control characters.")
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        if value not in _zones():
            raise PydanticCustomError("timezone_unknown", "Choose a time zone from the list.")
        return value


class SettingsView(BaseModel):
    lead_days: int
    coach_enabled: bool
    gemini_mode: GeminiMode
    gemini_model: str
    share_images_with_gemini: bool
    assistant_share_item_text: bool


class SettingsPatch(BaseModel):
    """Any subset of the settings; a key that is present must carry a real value.

    Strict: the string "yes" is not a boolean and "7" is not a number of days.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    lead_days: int | None = Field(default=None, ge=1, le=14)
    coach_enabled: bool | None = None
    gemini_mode: GeminiMode | None = None
    gemini_model: str | None = Field(default=None, max_length=100)
    share_images_with_gemini: bool | None = None
    assistant_share_item_text: bool | None = None
    # P-01 step 2 is finished (Continue or Skip); the only value a client may write (D-093).
    first_run_step: Literal["done"] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _not_null(cls, value):
        # Defaults are not validated, so this only sees keys the caller actually sent.
        if value is None:
            raise PydanticCustomError("not_null", "This setting needs a value.")
        return value
