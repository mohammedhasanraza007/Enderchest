"""Categories and locations (API 2.4)."""

import sqlite3

from fastapi import APIRouter, Depends, Response

from ..schemas.catalog import (
    Category,
    CategoryCreate,
    CategoryPatch,
    Location,
    LocationCreate,
    LocationPatch,
)
from ..services import catalog
from .deps import current_user_id, get_db

router = APIRouter(prefix="/api/v1")


@router.get("/categories")
def list_categories(conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> list[Category]:
    return [Category(**view) for view in catalog.list_categories(conn, user_id)]


@router.post("/categories", status_code=201)
def create_category(body: CategoryCreate, conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Category:
    return Category(**catalog.create_category(conn, user_id, **body.model_dump()))


@router.patch("/categories/{category_id}")
def change_category(category_id: int, body: CategoryPatch,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Category:
    changes = body.model_dump(exclude_unset=True)
    return Category(**catalog.change_category(conn, user_id, category_id, changes))


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, reassign_to: str | None = None,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Response:
    catalog.delete_category(conn, user_id, category_id, catalog.parse_reassign(reassign_to))
    return Response(status_code=204)


@router.get("/locations")
def list_locations(conn: sqlite3.Connection = Depends(get_db),
                   user_id: int = Depends(current_user_id)) -> list[Location]:
    return [Location(**view) for view in catalog.list_locations(conn, user_id)]


@router.post("/locations", status_code=201)
def create_location(body: LocationCreate, conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Location:
    return Location(**catalog.create_location(conn, user_id, name=body.name,
                                              parent_id=body.parent_id))


@router.patch("/locations/{location_id}")
def change_location(location_id: int, body: LocationPatch,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Location:
    view = catalog.change_location(conn, user_id, location_id, name=body.name,
                                   parent_id=body.parent_id,
                                   move="parent_id" in body.model_fields_set)
    return Location(**view)


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(location_id: int, reassign_to: str | None = None,
                    conn: sqlite3.Connection = Depends(get_db),
                    user_id: int = Depends(current_user_id)) -> Response:
    catalog.delete_location(conn, user_id, location_id, catalog.parse_reassign(reassign_to))
    return Response(status_code=204)
