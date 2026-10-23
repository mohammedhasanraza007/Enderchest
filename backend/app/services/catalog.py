"""Categories and locations: the rules of API 2.4 and DATA_MODEL 2.4, 2.5, and D-094.

Names are unique case-insensitively (per parent for locations). Locations form a tree at most
5 deep; a move under itself or a descendant is a `cycle`. Deleting one that items use needs
`reassign_to` (an id, or `none`); items in Trash move too, so a restore never points at a
deleted row.
"""

import sqlite3

from .. import clock
from ..db.connection import write_transaction
from ..errors import AppError
from ..repositories import categories as categories_repo
from ..repositories import items as items_repo
from ..repositories import locations as locations_repo

MAX_DEPTH = 5


def _category_view(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"],
            "expires_default": bool(row["expires_default"]),
            "maintenance_default": bool(row["maintenance_default"]),
            "label_default": bool(row["label_default"]), "item_count": row["item_count"]}


def _duplicate(what: str) -> AppError:
    return AppError("conflict", 409, f"A {what} with that name already exists.",
                    {"reason": "duplicate_name", "field": "name"})


def parse_reassign(raw: str | None) -> int | None | str:
    """`reassign_to` from the query: None (not sent), `"none"`, or an id."""
    if raw is None or raw == "none":
        return raw
    if raw.isdigit():
        return int(raw)
    raise AppError("validation_error", 422, "Some values are not valid.",
                   {"problems": [{"field": "reassign_to",
                                  "problem": "Choose where to move the items."}]})


# ---- categories -------------------------------------------------------------------------------

def list_categories(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    return [_category_view(row) for row in categories_repo.list_all(conn, user_id)]


def get_category(conn: sqlite3.Connection, user_id: int, category_id: int) -> dict:
    row = categories_repo.get(conn, user_id, category_id)
    if row is None:
        raise AppError("not_found", 404, "That category does not exist.")
    return _category_view(row)


def create_category(conn: sqlite3.Connection, user_id: int, *, name: str,
                    expires_default: bool, maintenance_default: bool,
                    label_default: bool) -> dict:
    with write_transaction(conn):
        if categories_repo.name_taken(conn, user_id, name):
            raise _duplicate("category")
        new_id = categories_repo.insert(
            conn, user_id, name=name, expires_default=expires_default,
            maintenance_default=maintenance_default, label_default=label_default,
            now=clock.stamp())
    return get_category(conn, user_id, new_id)


def change_category(conn: sqlite3.Connection, user_id: int, category_id: int,
                    changes: dict) -> dict:
    with write_transaction(conn):
        if categories_repo.get(conn, user_id, category_id) is None:
            raise AppError("not_found", 404, "That category does not exist.")
        if "name" in changes and categories_repo.name_taken(conn, user_id, changes["name"],
                                                            except_id=category_id):
            raise _duplicate("category")
        categories_repo.update(conn, user_id, category_id, changes)
    return get_category(conn, user_id, category_id)


def delete_category(conn: sqlite3.Connection, user_id: int, category_id: int,
                    reassign_to: int | None | str) -> None:
    now = clock.stamp()
    with write_transaction(conn):
        if categories_repo.get(conn, user_id, category_id) is None:
            raise AppError("not_found", 404, "That category does not exist.")
        used = items_repo.count_using(conn, user_id, "category_id", [category_id])
        if used and reassign_to is None:
            verb = "uses" if used == 1 else "use"
            raise AppError("in_use", 409, f"{_items(used)} {verb} this category. Choose where "
                           "to move them first.", {"count": used})
        if used:
            target = None if reassign_to == "none" else reassign_to
            if target is not None and (target == category_id
                                       or categories_repo.get(conn, user_id, target) is None):
                raise AppError("not_found", 404, "The category to move items to does not exist.")
            items_repo.reassign(conn, user_id, "category_id", category_id, target, now)
        categories_repo.soft_delete(conn, user_id, category_id, now)


def _items(count: int) -> str:
    return "1 item" if count == 1 else f"{count} items"


# ---- locations --------------------------------------------------------------------------------

def _tree(conn: sqlite3.Connection, user_id: int) -> dict[int, sqlite3.Row]:
    return {row["id"]: row for row in locations_repo.list_all(conn, user_id)}


def _path(rows: dict[int, sqlite3.Row], location_id: int) -> list[str]:
    names, seen, current = [], set(), location_id
    while current is not None and current in rows and current not in seen:
        seen.add(current)
        names.append(rows[current]["name"])
        current = rows[current]["parent_id"]
    return list(reversed(names))


def location_paths(conn: sqlite3.Connection, user_id: int) -> dict[int, list[str]]:
    """Every live location's path, `Garage › Shelf 2 › Blue box` as a list of names."""
    rows = _tree(conn, user_id)
    return {location_id: _path(rows, location_id) for location_id in rows}


def list_locations(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = _tree(conn, user_id)
    views = [{"id": row["id"], "name": row["name"], "parent_id": row["parent_id"],
              "path": _path(rows, row["id"]), "item_count": row["item_count"]}
             for row in rows.values()]
    # Tree order: each location right after its parent, siblings by name.
    return sorted(views, key=lambda view: [name.lower() for name in view["path"]])


def get_location(conn: sqlite3.Connection, user_id: int, location_id: int) -> dict:
    for view in list_locations(conn, user_id):
        if view["id"] == location_id:
            return view
    raise AppError("not_found", 404, "That location does not exist.")


def _height(rows: dict[int, sqlite3.Row], location_id: int) -> int:
    """Levels in the subtree rooted here (1 for a location with no children)."""
    children = [r["id"] for r in rows.values() if r["parent_id"] == location_id]
    return 1 + max((_height(rows, child) for child in children), default=0)


def _too_deep() -> AppError:
    return AppError("validation_error", 422, "Some values are not valid.",
                    {"problems": [{"field": "parent_id",
                                   "problem": f"Places can be nested {MAX_DEPTH} levels deep "
                                              "at most."}]})


def create_location(conn: sqlite3.Connection, user_id: int, *, name: str,
                    parent_id: int | None) -> dict:
    with write_transaction(conn):
        rows = _tree(conn, user_id)
        if parent_id is not None:
            if parent_id not in rows:
                raise AppError("not_found", 404, "The place to put it in does not exist.")
            if len(_path(rows, parent_id)) >= MAX_DEPTH:
                raise _too_deep()
        if locations_repo.name_taken(conn, user_id, name, parent_id):
            raise _duplicate("location here")
        new_id = locations_repo.insert(conn, user_id, name=name, parent_id=parent_id,
                                       now=clock.stamp())
    return get_location(conn, user_id, new_id)


def change_location(conn: sqlite3.Connection, user_id: int, location_id: int, *,
                    name: str | None, parent_id: int | None, move: bool) -> dict:
    """`move` is True when the request sent `parent_id` (null means the top level)."""
    with write_transaction(conn):
        rows = _tree(conn, user_id)
        if location_id not in rows:
            raise AppError("not_found", 404, "That location does not exist.")
        current = rows[location_id]
        new_parent = parent_id if move else current["parent_id"]
        new_name = name if name is not None else current["name"]
        if move and new_parent is not None:
            if new_parent not in rows:
                raise AppError("not_found", 404, "The place to move it to does not exist.")
            if new_parent in locations_repo.descendant_ids(conn, user_id, location_id):
                raise AppError("cycle", 409,
                               "A place cannot go inside itself or a place inside it.")
            if len(_path(rows, new_parent)) + _height(rows, location_id) > MAX_DEPTH:
                raise _too_deep()
        if locations_repo.name_taken(conn, user_id, new_name, new_parent, except_id=location_id):
            raise _duplicate("location here")
        locations_repo.update(conn, user_id, location_id, name=new_name, parent_id=new_parent)
    return get_location(conn, user_id, location_id)


def delete_location(conn: sqlite3.Connection, user_id: int, location_id: int,
                    reassign_to: int | None | str) -> None:
    now = clock.stamp()
    with write_transaction(conn):
        rows = _tree(conn, user_id)
        if location_id not in rows:
            raise AppError("not_found", 404, "That location does not exist.")
        if any(row["parent_id"] == location_id for row in rows.values()):
            raise AppError("in_use", 409, "Move or delete the places inside it first.",
                           {"reason": "has_children"})
        used = items_repo.count_using(conn, user_id, "location_id", [location_id])
        if used and reassign_to is None:
            verb = "is" if used == 1 else "are"
            raise AppError("in_use", 409, f"{_items(used)} {verb} kept here. Choose where to "
                           "move them first.", {"count": used, "reason": "has_items"})
        if used:
            target = None if reassign_to == "none" else reassign_to
            if target is not None and (target == location_id or target not in rows):
                raise AppError("not_found", 404, "The place to move items to does not exist.")
            items_repo.reassign(conn, user_id, "location_id", location_id, target, now)
        locations_repo.soft_delete(conn, user_id, location_id, now)
