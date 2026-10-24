"""The ownership check's scoring, pure functions only (Phase 6 spec, Build 3).

A candidate earns points from signals: model or part number, size, name and brand words,
category and image similarity. The points give a level, High, Medium or Possible (API `low`,
D-114), never "certain": the owner decides. A candidate that only looks similar is at most
Possible, because a photo cannot tell a 13 mm spanner from a 14 mm one.
"""

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

# Starting values from the spec; the measurement on the owner's 20 photos may tune them (D-115).
MODEL_EQUAL = 60
MODEL_FUZZY = 35
MODEL_FUZZY_RATIO = 92
SIZE_EQUAL = 20
SIZE_DIFFERENT = -30
NAME_MAX = 30
CATEGORY = 5
IMAGE_STRONG, IMAGE_STRONG_POINTS = 0.80, 15
IMAGE_WEAK, IMAGE_WEAK_POINTS = 0.70, 8

HIGH, MEDIUM, POSSIBLE = 75, 45, 25
HIGH_NAME_OVERLAP = 80
MAX_CANDIDATES = 5

MODEL_KEYS = ("model", "part_no", "part_number", "model_no", "mpn")
SIZE_KEYS = ("size", "sizes")
BRAND_KEYS = ("brand", "make", "manufacturer")

# Units to one base per kind, so "1 L" equals "1000 ml" and "1.5 kg" equals "1500 g".
_UNIT_BASE = {
    "mm": ("length", 1.0), "cm": ("length", 10.0), "m": ("length", 1000.0),
    "in": ("length", 25.4), '"': ("length", 25.4),
    "ml": ("volume", 1.0), "l": ("volume", 1000.0),
    "g": ("mass", 1.0), "kg": ("mass", 1000.0),
    "mah": ("charge", 1.0), "v": ("voltage", 1.0), "a": ("current", 1.0), "w": ("power", 1.0),
    "gb": ("storage", 1.0), "tb": ("storage", 1000.0), "pcs": ("count", 1.0),
}
# "in" followed by a number is a name ("2 in 1 cable"), not inches.
_SIZE = re.compile(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*"
                   r"(mah|mm|cm|ml|kg|gb|tb|pcs|in(?!\s*\d)|m|l|g|v|a|w|\")(?![a-z])",
                   re.IGNORECASE)
# "10,000" and "1,00,000" group thousands (English and Indian labels); "1,5" is a decimal comma.
_GROUPED = re.compile(r"\d{1,3}(?:,\d{2})*,\d{3}(?:\.\d+)?")


def _number(text: str) -> float:
    if _GROUPED.fullmatch(text) or "." in text:
        return float(text.replace(",", ""))
    whole, _, rest = text.partition(",")
    return float(f"{whole}.{rest.replace(',', '')}" if rest else whole)


@dataclass(frozen=True)
class Query:
    """What the check knows about the thing on the desk."""
    name: str = ""  # typed text, or the name read from the photo
    model: str = ""
    sizes: tuple[tuple[str, float], ...] = ()  # normalised (kind, value)
    vector_score: dict[int, float] = field(default_factory=dict)  # item id -> best cosine


@dataclass(frozen=True)
class Candidate:
    item_id: int
    score: int
    level: str | None  # "high", "medium", "low" (shown as Possible), or None: hidden
    reasons: list[str]


def normalise_model(value: str) -> str:
    """Model numbers compare without case, spaces, dashes, dots or slashes."""
    return re.sub(r"[^0-9A-Z]", "", value.upper())


def sizes_in(text: str) -> tuple[tuple[str, float], ...]:
    """Every size in a text as (kind, value in the base unit), in order, without repeats."""
    found: list[tuple[str, float]] = []
    for number, unit in _SIZE.findall(text or ""):
        kind, factor = _UNIT_BASE[unit.lower()]
        entry = (kind, round(_number(number) * factor, 3))
        if entry not in found:
            found.append(entry)
    return tuple(found)


def _texts(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(part) for part in value if part is not None]
    return [] if value is None else [str(value)]


def item_models(attributes: dict) -> list[str]:
    return [m for key in MODEL_KEYS for m in map(normalise_model, _texts(attributes.get(key))) if m]


def item_sizes(attributes: dict) -> tuple[tuple[str, float], ...]:
    found: list[tuple[str, float]] = []
    for key in SIZE_KEYS:
        for text in _texts(attributes.get(key)):
            found.extend(size for size in sizes_in(text) if size not in found)
    return tuple(found)


def _model_points(query: Query, models: list[str]) -> tuple[int, str | None]:
    wanted = normalise_model(query.model)
    if not wanted or not models:
        return 0, None
    if wanted in models:
        return MODEL_EQUAL, "Same model number"
    if max(fuzz.ratio(wanted, model) for model in models) >= MODEL_FUZZY_RATIO:
        return MODEL_FUZZY, "Similar model number"
    return 0, None


def _size_points(query: Query, sizes: tuple[tuple[str, float], ...]) -> tuple[int, str | None]:
    kinds = {kind for kind, _ in query.sizes} & {kind for kind, _ in sizes}
    if not kinds:
        return 0, None  # sizes of different kinds (ml and mm) say nothing about each other
    if set(query.sizes) & set(sizes):
        return SIZE_EQUAL, "Same size"
    return SIZE_DIFFERENT, "Different size"


def score(query: Query, item: dict, category_name: str | None) -> Candidate:
    """Points and level for one active item (`item`: id, name, attributes)."""
    attributes = item.get("attributes") or {}
    points, reasons = 0, []
    model, why = _model_points(query, item_models(attributes))
    points += model
    reasons += [why] if why else []
    size, why = _size_points(query, item_sizes(attributes))
    points += size
    reasons += [why] if why else []
    overlap = 0.0
    if query.name.strip():
        brands = [text for key in BRAND_KEYS for text in _texts(attributes.get(key))]
        words = " ".join([item["name"], *brands])
        overlap = fuzz.token_set_ratio(query.name.lower(), words.lower())
        name_points = round(overlap * NAME_MAX / 100)
        points += name_points
        if overlap >= HIGH_NAME_OVERLAP:
            reasons.append("Same name")
        elif name_points >= NAME_MAX // 2:
            reasons.append("Similar name")
        if category_name and fuzz.partial_ratio(category_name.lower(), query.name.lower()) >= 90:
            points += CATEGORY
            reasons.append("Same category")
    similarity = query.vector_score.get(item["id"], 0.0)
    image = (IMAGE_STRONG_POINTS if similarity >= IMAGE_STRONG
             else IMAGE_WEAK_POINTS if similarity >= IMAGE_WEAK else 0)
    points += image
    if image:
        reasons.append("Looks similar" if image == IMAGE_STRONG_POINTS
                       else "Looks a little similar")
    text_support = model > 0 or size > 0 or overlap >= 50
    found = level(points, model > 0, size > 0, overlap, text_support)
    if found is None and not text_support and size == 0 and image == IMAGE_STRONG_POINTS:
        found = "low"  # a strong look-alike is worth a glance unless its size differs (D-119)
    return Candidate(item["id"], points, found, reasons)


def level(points: int, model_match: bool, size_match: bool, overlap: float,
          text_support: bool) -> str | None:
    """High needs 75 points and a model match, or a size match with name overlap of 80 or more;
    a candidate only an image supports is at most Possible; below 25 it is hidden (None)."""
    if points < POSSIBLE:
        return None
    if not text_support:
        return "low"
    if points >= HIGH and (model_match or (size_match and overlap >= HIGH_NAME_OVERLAP)):
        return "high"
    return "medium" if points >= MEDIUM else "low"


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Visible candidates, best first, at most five."""
    shown = [c for c in candidates if c.level is not None]
    return sorted(shown, key=lambda c: (-c.score, c.item_id))[:MAX_CANDIDATES]
