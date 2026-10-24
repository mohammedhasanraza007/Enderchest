"""The dashboard (API 2.13, D-110 to D-113)."""

from typing import Literal

from pydantic import BaseModel

from .lifecycle import NotificationView

RingName = Literal["documented", "located", "fresh", "on_time"]


class Greeting(BaseModel):
    part: Literal["morning", "afternoon", "evening", "night"]
    name: str


class Ring(BaseModel):
    value: int | None
    num: int
    den: int


class Rings(BaseModel):
    documented: Ring
    located: Ring
    fresh: Ring
    on_time: Ring


class Attention(BaseModel):
    rows: list[NotificationView]
    total: int


class RoadEntry(BaseModel):
    kind: Literal["expiry", "task"]
    label: str
    public_id: str | None
    task_id: int | None


class RoadEvent(BaseModel):
    date: str
    kind: Literal["expiry", "task", "mixed"]
    label: str
    count: int
    entries: list[RoadEntry]


class Road(BaseModel):
    start: str
    end: str
    events: list[RoadEvent]
    truck_date: str


class Savings(BaseModel):
    month_paise: int
    pill_date: str | None


class Streak(BaseModel):
    days: int


class Dashboard(BaseModel):
    today: str
    greeting: Greeting
    subtitle: str
    item_count: int
    score: int | None
    rings: Rings
    attention: Attention
    road: Road
    savings: Savings | None
    streak: Streak | None


class BreakdownEntry(BaseModel):
    kind: Literal["item", "task"]
    name: str
    public_id: str | None
    task_id: int | None
    note: str


class RingBreakdown(BaseModel):
    ring: RingName
    value: int | None
    num: int
    den: int
    qualifying: list[BreakdownEntry]
    failing: list[BreakdownEntry]
