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


class Draft(BaseModel):
    id: str
    status: Literal["open", "committed", "discarded"]
    fields: DraftFields
    photos: list[DraftPhoto]
    ocr_status: Literal["none", "pending", "done", "failed"]
    gemini_status: Literal["none", "pending", "done", "failed", "skipped"]
    proposed: dict  # values read from the photo arrive in Phase 3; empty until then
    raw_text: str | None
    created_at: str


class DraftList(BaseModel):
    items: list[Draft]


class DraftBatch(BaseModel):
    drafts: list[Draft]
