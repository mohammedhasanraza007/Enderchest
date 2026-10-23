"""Text rules shared by the inventory schemas (DATA_MODEL 1, Text)."""

import unicodedata
from datetime import date

from pydantic_core import PydanticCustomError

NAME_MAX = 120
NOTES_MAX = 2000


def _has_control(value: str, allowed: str = "") -> bool:
    return any(unicodedata.category(ch) == "Cc" and ch not in allowed for ch in value)


def clean_name(value: str, what: str = "name") -> str:
    """Trimmed, 1 to 120 characters, no control characters."""
    value = value.strip()
    if not 1 <= len(value) <= NAME_MAX:
        raise PydanticCustomError("name_length", f"Enter a {what} of 1 to 120 characters.")
    if _has_control(value):
        raise PydanticCustomError("name_chars", "Use letters, numbers and punctuation only.")
    return value


def clean_notes(value: str) -> str:
    """Up to 2000 characters; line breaks and tabs are fine, other control characters are not."""
    value = value.strip()
    if len(value) > NOTES_MAX:
        raise PydanticCustomError("notes_length", "Notes can be up to 2000 characters.")
    if _has_control(value, allowed="\n\t\r"):
        raise PydanticCustomError("notes_chars", "Notes cannot contain control characters.")
    return value


def clean_date(value: str) -> str:
    """A real calendar date written YYYY-MM-DD."""
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        parsed = None
    if parsed is None or len(value) != 10:
        raise PydanticCustomError("date_format", "Enter a date as YYYY-MM-DD.")
    return value


def not_null(value):
    """For PATCH bodies: a key that is sent must carry a value (defaults are not validated)."""
    if value is None:
        raise PydanticCustomError("not_null", "This needs a value.")
    return value
