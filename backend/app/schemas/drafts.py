"""Drafts, the add flow (API 2.8, DATA_MODEL 2.8). A draft's fields are an item's fields being
filled in, so each may still be missing; the item rules apply on commit.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from .items import ItemFields
from .text import NAME_MAX


class DraftFields(ItemFields):
    """Keys as in POST /items plus `expiry_confirmed`. A name may be empty while typing."""

    name: str | None = None
    expiry_confirmed: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > NAME_MAX:
            raise PydanticCustomError("name_length", "Enter a name of 1 to 120 characters.")
        return value


class DraftPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    fields: DraftFields


class DraftPhoto(BaseModel):
    id: str
    width: int
    height: int


class Proposal(BaseModel):
    """A value read from the photo (`ocr`) or suggested by Gemini, never trusted unconfirmed."""

    value: str | int
    source: Literal["ocr", "gemini"]
    confidence: Literal["high", "medium", "low"]
    flags: list[str]
    text: str | None = None  # the line or Gemini text the value came from
    alternatives: list[str] | None = None  # the other reading of an ambiguous date


class ReadingInfo(BaseModel):
    engine: str
    ms: int
    photos: int


class GeminiAnswer(BaseModel):
    """Gemini's validated answer, shown in the "What was read" drawer."""

    name: str | None = None
    brand: str | None = None
    model: str | None = None
    size: str | None = None
    category: str | None = None
    expiry_text: str | None = None
    inspection_interval_days: int | None = None


class Draft(BaseModel):
    id: str
    status: Literal["open", "committed", "discarded"]
    fields: DraftFields
    photos: list[DraftPhoto]
    ocr_status: Literal["none", "pending", "done", "failed"]
    gemini_status: Literal["none", "pending", "done", "failed", "skipped"]
    # Keys: name, model, size, brand, expiry_date, category_id, inspection_interval_days.
    proposed: dict[str, Proposal]
    raw_text: str | None
    ocr_error: str | None
    gemini_error: str | None
    read_notes: list[str]
    ocr_info: ReadingInfo | None
    gemini_values: GeminiAnswer | None
    created_at: str


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    engine: Literal["local", "gemini"]


class ExtractQueued(BaseModel):
    ocr_status: Literal["pending"] | None = None
    gemini_status: Literal["pending"] | None = None


class DraftList(BaseModel):
    items: list[Draft]


class DraftBatch(BaseModel):
    drafts: list[Draft]
