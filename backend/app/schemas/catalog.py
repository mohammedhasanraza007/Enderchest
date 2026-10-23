"""Categories and locations (API 2.4, DATA_MODEL 2.4 and 2.5)."""

from pydantic import BaseModel, ConfigDict, field_validator

from .text import clean_name, not_null


class Category(BaseModel):
    id: int
    name: str
    expires_default: bool
    maintenance_default: bool
    label_default: bool
    item_count: int


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    expires_default: bool = False
    maintenance_default: bool = False
    label_default: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value, "category name")


class CategoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = None
    expires_default: bool | None = None
    maintenance_default: bool | None = None
    label_default: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _sent_means_set(cls, value):
        return not_null(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value, "category name")


class Location(BaseModel):
    id: int
    name: str
    parent_id: int | None
    path: list[str]
    item_count: int


class LocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value, "location name")


class LocationPatch(BaseModel):
    """`parent_id: null` moves the location to the top level; leaving it out keeps it."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = None
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_sent(cls, value):
        return not_null(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_name(value, "location name")
