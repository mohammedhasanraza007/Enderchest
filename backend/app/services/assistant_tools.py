"""The assistant's four read-only tools (Phase 9 spec, D-134).

Gemini never receives the inventory: it asks for these, the backend runs them here, and only
their rows go back. Every tool sees **active items only** (not used up, expired-and-marked,
discarded or in Trash) and returns at most 20 rows. A row is the public id, the name, the
category, the location path, the quantity and the expiry word (DATA_MODEL 3.2): never notes,
photos, prices or attributes. Nothing here writes.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import timedelta

from .. import ids
from ..derived import expiry_view
from ..repositories import categories as categories_repo
from ..repositories import items as items_repo
from ..repositories import locations as locations_repo
from . import catalog
from . import profile as profile_service

ROW_LIMIT = 20
DAYS_MAX = 365
TEXT_MAX = 120
WORDS_MAX = 8
EXPIRY_FILTERS = {"expired": "past", "expires_today": "today", "no_expiry": "none",
                  "date_not_set": "unknown"}

_TEXT = {"type": "STRING"}
DECLARATIONS = [
    {"name": "search_items",
     "description": "Find the owner's items that are in use (not used up, thrown away or in "
                    "Trash). Every word of q must appear in the item's name, id or details; an "
                    "empty q lists the newest items. category and location are names the owner "
                    "uses; a location includes the places inside it. Returns at most 20 rows "
                    "and the total number found.",
     "parameters": {"type": "OBJECT",
                    "properties": {"q": {"type": "STRING",
                                         "description": "Words to look for, such as "
                                                        "'spanner 13'."},
                                   "category": _TEXT, "location": _TEXT},
                    "required": ["q"]}},
    {"name": "items_expiring",
     "description": "Items in use whose expiry date is from today up to `days` days ahead "
                    "(0 is today only, 7 is the coming week), soonest first. At most 20 rows "
                    "and the total.",
     "parameters": {"type": "OBJECT",
                    "properties": {"days": {"type": "INTEGER",
                                            "description": "0 to 365."}},
                    "required": ["days"]}},
    {"name": "count_items",
     "description": "How many items in use match. Every filter is optional: q (words), "
                    "category and location names, and an expiry state.",
     "parameters": {"type": "OBJECT",
                    "properties": {"q": _TEXT, "category": _TEXT, "location": _TEXT,
                                   "expiry": {"type": "STRING",
                                              "enum": sorted(EXPIRY_FILTERS)}}}},
    {"name": "get_item",
     "description": "One item in use by its id (ENDR- and 8 characters).",
     "parameters": {"type": "OBJECT",
                    "properties": {"public_id": _TEXT},
                    "required": ["public_id"]}},
]


class ToolInputError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class Found:
    """What this turn's tools returned: the post-check compares the answer with it."""

    rows: dict[str, dict] = field(default_factory=dict)  # public_id -> row, first seen first
    tools: list[str] = field(default_factory=list)  # tool names in the order first called
    searched: bool = False  # search_items or get_item ran


def _text(args: dict, name: str, *, required: bool = False) -> str:
    value = args.get(name)
    if value is None:
        if required:
            raise ToolInputError(f"{name} is required.")
        return ""
    if not isinstance(value, str):
        raise ToolInputError(f"{name} must be text.")
    return " ".join(value.split())[:TEXT_MAX]


def _days(args: dict) -> int:
    value = args.get("days")
    # JSON numbers may arrive as 7.0; anything that is not a whole number is refused.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise ToolInputError("days must be a whole number from 0 to 365.")
    return max(0, min(DAYS_MAX, int(value)))


class Toolbox:
    """Runs the tools for one turn of one owner, and remembers what they returned."""

    def __init__(self, conn: sqlite3.Connection, user_id: int) -> None:
        self.conn, self.user_id = conn, user_id
        self.today = profile_service.local_today(conn, user_id)
        self.lead_days = profile_service.lead_days(conn, user_id)
        self.paths = catalog.location_paths(conn, user_id)
        self.found = Found()

    def run(self, name: str, args: dict) -> dict:
        handlers = {"search_items": self._search, "items_expiring": self._expiring,
                    "count_items": self._count, "get_item": self._get}
        handler = handlers.get(name)
        if handler is None:
            return {"error": f"There is no tool named {name}."}
        if name not in self.found.tools:
            self.found.tools.append(name)
        if name in ("search_items", "get_item"):
            self.found.searched = True
        try:
            return handler(args)
        except ToolInputError as bad:
            return {"error": bad.message}

    # ---- the tools ----------------------------------------------------------------------------

    def _search(self, args: dict) -> dict:
        query, note = self._query(args, sort="name_asc")
        if note:
            return {"total": 0, "rows": [], "note": note}
        return self._rows(query)

    def _expiring(self, args: dict) -> dict:
        until = self.today + timedelta(days=_days(args))
        return self._rows(self._base(expiry="within", soon_until=until.isoformat(),
                                     sort="expiry_asc"))

    def _count(self, args: dict) -> dict:
        expiry = args.get("expiry")
        if expiry is not None and expiry not in EXPIRY_FILTERS:
            raise ToolInputError(f"expiry must be one of {', '.join(sorted(EXPIRY_FILTERS))}.")
        query, note = self._query(args, sort="created_desc",
                                  expiry=EXPIRY_FILTERS.get(expiry, "any"))
        if note:
            return {"count": 0, "note": note}
        return {"count": items_repo.count(self.conn, self.user_id, query)}

    def _get(self, args: dict) -> dict:
        public_id = ids.normalise(_text(args, "public_id", required=True))
        row = items_repo.get(self.conn, self.user_id, public_id) if public_id else None
        if row is None or row["state"] != "active" or row["deleted_at"] is not None:
            return {"rows": [], "note": "No item in use has that id."}
        return {"rows": [self._keep(row)]}

    # ---- helpers ------------------------------------------------------------------------------

    def _base(self, **values) -> items_repo.ItemQuery:
        values.setdefault("today", self.today.isoformat())
        return items_repo.ItemQuery(state="active", deleted="exclude", **values)

    def _query(self, args: dict, *, sort: str,
               expiry: str = "any") -> tuple[items_repo.ItemQuery, str | None]:
        """The filters from the tool's words and names; a name nobody uses is a note."""
        words = tuple(_text(args, "q").split())[:WORDS_MAX]
        category_id = None
        category = _text(args, "category")
        if category:
            wanted = category.casefold()
            match = [row["id"] for row in categories_repo.list_all(self.conn, self.user_id)
                     if row["name"].casefold() == wanted]
            if not match:
                return self._base(), f'There is no category named "{category}".'
            category_id = match[0]
        location_ids = None
        location = _text(args, "location")
        if location:
            wanted = location.casefold()
            places = [row["id"] for row in locations_repo.list_all(self.conn, self.user_id)
                      if row["name"].casefold() == wanted]
            if not places:
                return self._base(), f'There is no location named "{location}".'
            location_ids = tuple(sorted({place for found in places for place in
                                         locations_repo.descendant_ids(self.conn, self.user_id,
                                                                       found)}))
        soon_until = (self.today + timedelta(days=self.lead_days)).isoformat()
        return self._base(words=words, category_id=category_id, location_ids=location_ids,
                          expiry=expiry, soon_until=soon_until, sort=sort), None

    def _rows(self, query: items_repo.ItemQuery) -> dict:
        rows = items_repo.search(self.conn, self.user_id, query, ROW_LIMIT, 0)
        return {"total": items_repo.count(self.conn, self.user_id, query),
                "rows": [self._keep(row) for row in rows]}

    def _keep(self, row: sqlite3.Row) -> dict:
        """The row as Gemini sees it, remembered for the post-check."""
        view = row_view(row, self.paths, self.today, self.lead_days)
        self.found.rows.setdefault(view["public_id"], view)
        return view


def row_view(row, paths: dict[int, list[str]], today, lead_days: int) -> dict:
    """The only item fields that ever leave the machine (Phase 9 spec, D-134)."""
    path = paths.get(row["location_id"], []) if row["location_id"] is not None else []
    return {"public_id": row["public_id"], "name": row["name"],
            "category": row["category_name"],
            "location": " › ".join(path) or None,
            "quantity": row["quantity"],
            "expiry": expiry_view(row["expiry_mode"], row["expiry_date"], today,
                                  lead_days)["word"]}
