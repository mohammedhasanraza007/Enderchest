"""Lifecycle, tasks, maintenance, inspections and notifications (API 2.10 to 2.12; DATA_MODEL
2.9, 2.10, 2.12; D-104 to D-107)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .items import QUANTITY_MAX, ItemDetail
from .text import clean_date, clean_name, clean_notes, not_null

INTERVAL_MAX = 3650
ScheduleMode = Literal["from_completion", "fixed"]
TaskKind = Literal["maintenance", "chore"]
TaskSource = Literal["user", "gemini"]
NotificationKind = Literal["expiry_soon", "expired", "inspection_due", "task_due",
                           "inspection_finding"]


# ---- lifecycle --------------------------------------------------------------------------------

class UseBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    amount: int = Field(default=1, ge=1, le=QUANTITY_MAX)


class ReactivateBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    quantity: int | None = Field(default=None, ge=1, le=QUANTITY_MAX)


class LifecycleDone(BaseModel):
    item: ItemDetail
    event_id: int


# ---- tasks ------------------------------------------------------------------------------------

class ItemRefShort(BaseModel):
    public_id: str
    name: str


class TaskView(BaseModel):
    id: int
    title: str
    kind: TaskKind
    item: ItemRefShort | None
    interval_days: int | None
    schedule_mode: ScheduleMode
    next_due: str
    last_done: str | None
    enabled: bool
    source: TaskSource
    notes: str
    word: str


class TaskList(BaseModel):
    items: list[TaskView]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str
    item_public_id: str | None = None
    kind: TaskKind = "chore"
    interval_days: int | None = Field(default=None, ge=1, le=INTERVAL_MAX)
    schedule_mode: ScheduleMode = "from_completion"
    first_due: str
    notes: str = ""
    enabled: bool = True

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return clean_name(value, "title")

    @field_validator("first_due")
    @classmethod
    def _due(cls, value: str) -> str:
        return clean_date(value)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str) -> str:
        return clean_notes(value)


class TaskPatch(BaseModel):
    """Any of these; `null` clears the repeat (one-off) or the item link."""

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str | None = None
    item_public_id: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=INTERVAL_MAX)
    schedule_mode: ScheduleMode | None = None
    next_due: str | None = None
    notes: str | None = None
    enabled: bool | None = None

    @field_validator("title", "schedule_mode", "next_due", "notes", "enabled", mode="before")
    @classmethod
    def _sent_means_set(cls, value):
        return not_null(value)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return clean_name(value, "title")

    @field_validator("next_due")
    @classmethod
    def _due(cls, value: str) -> str:
        return clean_date(value)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value: str) -> str:
        return clean_notes(value)


class TaskDone(BaseModel):
    task: TaskView
    event_id: int


class TaskDeleted(BaseModel):
    event_id: int


class MaintenanceBody(BaseModel):
    """Creates or updates the item's maintenance task (API 2.11)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    enabled: bool
    interval_days: int | None = Field(default=None, ge=1, le=INTERVAL_MAX)
    first_due: str | None = None
    source: TaskSource | None = None

    @field_validator("first_due")
    @classmethod
    def _due(cls, value: str | None) -> str | None:
        return None if value is None else clean_date(value)


# ---- inspections ------------------------------------------------------------------------------

InspectionResultValue = Literal["ok", "worn", "defective"]


class InspectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    result: InspectionResultValue
    note: str = ""
    photo_id: str | None = Field(default=None, max_length=64)

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        return clean_notes(value)


class InspectionView(BaseModel):
    id: int
    performed_at: str
    local_date: str
    result: InspectionResultValue
    note: str
    photo_id: str | None


class InspectionDone(BaseModel):
    inspection: InspectionView
    task: TaskView | None
    event_id: int


class InspectionList(BaseModel):
    items: list[InspectionView]


# ---- notifications ----------------------------------------------------------------------------

class NotificationItem(BaseModel):
    public_id: str
    name: str
    primary_photo_id: str | None


class NotificationTask(BaseModel):
    id: int
    title: str


class NotificationAction(BaseModel):
    key: Literal["use", "mark_expired", "discard", "snooze", "inspect", "skip", "done", "keep"]
    label: str
    primary: bool


class NotificationView(BaseModel):
    id: int
    kind: NotificationKind
    item: NotificationItem | None
    task: NotificationTask | None
    due_date: str
    word: str
    urgency: Literal["overdue", "today", "upcoming"]
    status: Literal["open", "snoozed", "resolved"]
    snoozed_until: str | None
    read_at: str | None
    resolution: str | None
    actions: list[NotificationAction]


class NotificationPage(BaseModel):
    items: list[NotificationView]
    next_cursor: str | None


class NotificationCount(BaseModel):
    open: int
    unread: int
    unshown: list[NotificationView]


class SnoozeBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    option: Literal["tomorrow", "3days", "week"]


class ShownResult(BaseModel):
    claimed: bool


class ReadAllDone(BaseModel):
    updated: int
