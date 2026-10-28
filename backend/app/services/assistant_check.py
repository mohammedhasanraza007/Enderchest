"""The assistant's post-check (Phase 9 spec): the answer may name only what this turn's tools
returned. Pure functions, no database and no network, so every rule is unit-tested.

An answer is replaced by MISS when
  0. no tool ran in this turn: nothing was looked up, so nothing in it can be checked (D-137);
  1. it carries an item id (`ENDR-…`) that is not in this turn's rows;
  2. it names an item the owner has (any state, Trash included) that is not in this turn's
     rows, unless those words also appear in a row's own text or in the owner's question;
  3. a search or `get_item` ran and the turn found no rows at all (the "do I have…?" trap).
A made-up name that matches nothing the owner has can only be caught by rule 3; the prompt
forbids it (D-136 notes this limit). The names of the turn's rows become links (`segments`).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .. import ids

MISS = "I couldn't find that in your inventory."
REPLY_MAX = 4000
NAME_MIN = 3  # shorter names ("TV", "AA") would match ordinary words
_ID = re.compile(r"\bENDR-?[0-9A-Z]{8}\b", re.IGNORECASE)


@dataclass(frozen=True)
class Checked:
    reply: str
    segments: list[dict]  # [{"text", "public_id" (None for plain text)}], in order
    cited: list[dict]  # [{"public_id", "name"}], each item once, in order of first mention
    replaced: str | None  # the rule that replaced the answer, for the log; None when kept


def _whole(name: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE)


def _unknown_id(reply: str, rows: dict[str, dict]) -> bool:
    return any(ids.normalise(found) not in rows for found in _ID.findall(reply))


def _name_outside_rows(reply: str, rows: dict[str, dict], inventory_names: Iterable[str],
                       question: str) -> bool:
    folded = reply.casefold()
    allowed = " | ".join([question, *(" ".join(str(row[key] or "") for key in
                                               ("name", "category", "location"))
                                      for row in rows.values())]).casefold()
    row_names = {row["name"].casefold() for row in rows.values()}
    for name in inventory_names:
        wanted = name.strip().casefold()
        if len(wanted) < NAME_MIN or wanted in row_names or wanted not in folded:
            continue
        if wanted in allowed:  # "Milk" inside the row "Oat Milk", or the owner's own word
            continue
        if _whole(wanted).search(folded):
            return True
    return False


def link(reply: str, rows: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Split the answer into plain text and row names (longest name first at each place)."""
    by_name: dict[str, dict] = {}
    for row in rows.values():
        by_name.setdefault(row["name"].casefold(), row)
    names = sorted((row["name"] for row in by_name.values() if row["name"].strip()),
                   key=len, reverse=True)
    if not names:
        return [{"text": reply, "public_id": None}], []
    pattern = re.compile("|".join(rf"(?<!\w){re.escape(name)}(?!\w)" for name in names),
                         re.IGNORECASE)
    segments, cited, seen, start = [], [], set(), 0
    for match in pattern.finditer(reply):
        row = by_name.get(match.group(0).casefold())
        if row is None:  # a case match casefold does not repeat (rare letters): plain text
            continue
        if match.start() > start:
            segments.append({"text": reply[start:match.start()], "public_id": None})
        segments.append({"text": match.group(0), "public_id": row["public_id"]})
        if row["public_id"] not in seen:
            seen.add(row["public_id"])
            cited.append({"public_id": row["public_id"], "name": row["name"]})
        start = match.end()
    if start < len(reply):
        segments.append({"text": reply[start:], "public_id": None})
    return segments, cited


def check(answer: str, rows: dict[str, dict], searched: bool, inventory_names: Iterable[str],
          question: str, *, looked: bool = True) -> Checked:
    reply = answer.strip()
    if len(reply) > REPLY_MAX:
        reply = reply[:REPLY_MAX - 1].rstrip() + "…"
    if not looked:
        replaced = "no_tool"
    elif searched and not rows:
        replaced = "nothing_found"
    elif _unknown_id(reply, rows):
        replaced = "unknown_id"
    elif _name_outside_rows(reply, rows, inventory_names, question):
        replaced = "name_outside_rows"
    else:
        segments, cited = link(reply, rows)
        return Checked(reply, segments, cited, None)
    return Checked(MISS, [{"text": MISS, "public_id": None}], [], replaced)
