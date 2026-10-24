"""Ownership check and savings models (API 2.14). The frontend types are generated from these."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .items import PRICE_MAX_PAISE
from .text import clean_name, clean_notes


class CheckQuery(BaseModel):
    lines: list[str]  # the text read from the photo, for "What was read"
    fields: dict[str, str]  # name, model, size the check used


class CheckCandidate(BaseModel):
    public_id: str
    name: str
    primary_photo_id: str | None
    location_path: list[str]
    quantity: int
    price_paise: int | None  # pre-fills the "I didn't buy it" price when known
    score: int
    level: Literal["high", "medium", "low"]  # shown as High, Medium, Possible (D-114)
    reasons: list[str]


class CheckEngine(BaseModel):
    ocr: str | None
    gemini_used: bool  # always false in Phase 6 (D-117)


class CheckResult(BaseModel):
    query: CheckQuery
    candidates: list[CheckCandidate]
    engine: CheckEngine


class SavingCreate(BaseModel):
    """A saving exists only after the owner confirms "I didn't buy it" and types the price."""

    model_config = ConfigDict(extra="forbid", strict=True)

    item_public_id: str | None = None
    item_name: str | None = None
    price_paise: int = Field(gt=0, le=PRICE_MAX_PAISE)
    note: str = ""

    @field_validator("item_name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return None if value is None else clean_name(value, "item name")

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        return clean_notes(value)


class SavingCreated(BaseModel):
    id: int
    event_id: int


class SavingView(BaseModel):
    id: int
    item_name: str
    item_public_id: str | None
    price_paise: int
    local_date: str
    note: str


class SavingsPage(BaseModel):
    total_paise: int
    month_paise: int
    items: list[SavingView]
    next_cursor: str | None


class SavingRemoved(BaseModel):
    event_id: int
