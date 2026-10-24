"""Items, photos, events and labels (API 1 shared shapes, 2.5 to 2.7; DATA_MODEL 2.6).

Rules that need two fields at once (an expiry date only with mode `date`) live in the items
service, so a create, an edit and a draft commit share one check and one field name.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from .text import clean_date, clean_name, clean_notes, not_null

ExpiryMode = Literal["unknown", "none", "date"]
ExpiryStatus = Literal["no_expiry", "unknown", "expired", "today", "soon", "ok"]
ItemState = Literal["active", "used", "expired", "discarded"]
AttrScalar = str | int | float
AttrValue = AttrScalar | list[AttrScalar]

QUANTITY_MAX = 1_000_000
PRICE_MAX_PAISE = 10**12  # ₹1,000 crore: far above anything a person stores
ATTR_KEYS_MAX = 40
ATTR_VALUE_MAX = 500
_ATTR_KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def clean_attributes(value: dict[str, AttrValue]) -> dict[str, AttrValue]:
    """Lower snake case keys, at most 40; each value at most 500 characters (D-041)."""
    if len(value) > ATTR_KEYS_MAX:
        raise PydanticCustomError("attr_count", "Keep to 40 attributes or fewer.")
    cleaned: dict[str, AttrValue] = {}
    for key, raw in value.items():
        if not _ATTR_KEY.match(key):
            raise PydanticCustomError(
                "attr_key", "Attribute names use lowercase letters, digits and _ (like part_no).")
        items = raw if isinstance(raw, list) else [raw]
        items = [v.strip() if isinstance(v, str) else v for v in items]
        if not items or any(v == "" for v in items):
            raise PydanticCustomError("attr_empty", "Give each attribute a value.")
        if len(", ".join(str(v) for v in items)) > ATTR_VALUE_MAX:
            raise PydanticCustomError("attr_long",
                                      "An attribute value can be up to 500 characters.")
        cleaned[key] = items if isinstance(raw, list) else items[0]
    return cleaned


class ItemFields(BaseModel):
    """The editable fields of an item, shared by create and edit."""

    model_config = ConfigDict(extra="forbid", strict=True)

    category_id: int | None = None
    location_id: int | None = None
    quantity: int | None = Field(default=None, ge=0, le=QUANTITY_MAX)
    expiry_mode: ExpiryMode | None = None
    expiry_date: str | None = None
    price_paise: int | None = Field(default=None, ge=0, le=PRICE_MAX_PAISE)
    notes: str | None = None
    attributes: dict[str, AttrValue] | None = None
    no_label_needed: bool | None = None

    @field_validator("expiry_date")
    @classmethod
    def _date(cls, value: str | None) -> str | None:
        return None if value is None else clean_date(value)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return None if value is None else clean_notes(value)

    @field_validator("attributes")
    @classmethod
    def _attributes(cls, value: dict | None) -> dict | None:
        return None if value is None else clean_attributes(value)


class ItemCreate(ItemFields):
    name: str

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value)


class ItemPatch(ItemFields):
    """Any editable field; never `state`. `null` clears category, location, price or date."""

    name: str | None = None

    @field_validator("name", "quantity", "expiry_mode", "notes", "attributes", "no_label_needed",
                     mode="before")
    @classmethod
    def _sent_means_set(cls, value):
        return not_null(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value)


class ExpiryView(BaseModel):
    mode: ExpiryMode
    date: str | None
    status: ExpiryStatus
    days_left: int | None
    word: str


class ItemSummary(BaseModel):
    public_id: str
    name: str
    category_name: str | None
    location_path: list[str]
    quantity: int
    state: ItemState
    expiry: ExpiryView
    primary_photo_id: str | None
    has_photo: bool
    deleted_at: str | None


class Ref(BaseModel):
    id: int
    name: str


class LabelView(BaseModel):
    printed_at: str | None
    no_label_needed: bool


class PhotoView(BaseModel):
    id: str
    is_primary: bool
    width: int
    height: int


class MaintenanceView(BaseModel):
    """The item's maintenance task (API 1, ItemDetail); `enabled` is the per-item toggle."""

    task_id: int
    enabled: bool
    interval_days: int | None
    next_due: str
    last_done: str | None
    source: Literal["user", "gemini"]


class MaintenanceSuggestion(BaseModel):
    """Gemini's inspection interval from the draft that made the item (D-102): shown as
    "suggested, unverified", never applied without the owner."""

    interval_days: int


class ItemDetail(ItemSummary):
    category: Ref | None
    location: Ref | None
    price_paise: int | None
    notes: str
    attributes: dict[str, AttrValue]
    label: LabelView
    photos: list[PhotoView]
    maintenance: MaintenanceView | None
    maintenance_suggestion: MaintenanceSuggestion | None
    created_at: str
    updated_at: str


class ItemPage(BaseModel):
    items: list[ItemSummary]
    next_cursor: str | None
    total: int


class DeletedItem(BaseModel):
    event_id: int


class PermanentDelete(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    confirm: Literal["DELETE"]


class EventView(BaseModel):
    kind: str
    payload: dict
    at: str
    local_date: str


class EventPage(BaseModel):
    items: list[EventView]
    next_cursor: str | None


class UndoDone(BaseModel):
    ok: bool


class PrimaryPhoto(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    photo_id: str


class LabelPrinted(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    public_ids: list[str] = Field(min_length=1, max_length=200)


class LabelPrintedDone(BaseModel):
    updated: int
