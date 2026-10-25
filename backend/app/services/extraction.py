"""Proposals from read text lines (Phase 3 spec, Build 3 and 4; API `Draft.proposed`).

Each proposal is `{value, source, confidence, flags, text, alternatives?}`: what was read, where
it came from (`ocr` here), how sure the reading is (`high`, `medium`, `low`), the parser's flags
and the line it came from. A proposal is only a suggestion; the owner confirms every value on
the confirm screen, and an expiry date only by tapping it (CLAUDE.md 6).
"""

import re
from datetime import date

from ..integrations.ocr.pipeline import Line
from .expiry_parser import date_spans, parse_expiry

NAME_MAX = 120

_SIZE = re.compile(
    r"(?<![\w./-])(\d+(?:[.,]\d+)?(?:/\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?"
    r"(?:\s*[x×]\s*\d+(?:[.,]\d+)?)*)\s*(MAH|MM|CM|ML|KG|GB|TB|PCS|IN|M|L|G|V|A|W|\")(?![A-Z])",
    re.IGNORECASE)
_UNITS = {"MAH": "mAh", "MM": "mm", "CM": "cm", "ML": "ml", "KG": "kg", "GB": "GB", "TB": "TB",
          "PCS": "pcs", "IN": "in", "M": "m", "L": "L", "G": "g", "V": "V", "A": "A", "W": "W"}
_NET_LINE = re.compile(r"\b(?:NET|NETT|QTY|QUANTITY|CONTENTS?|VOL(?:UME)?|WT|WEIGHT)\b",
                       re.IGNORECASE)

_TOKEN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9\-./]*[A-Za-z0-9])?")
_MODEL_LABEL = re.compile(
    r"\b(?:MODEL(?:\s*NO\.?)?|MOD\.|PART\s*(?:NO\.?|NUMBER)|P/N|PN|TYPE|REF\.?|ART\.?\s*NO\.?"
    r"|SKU|ITEM\s*NO\.?)\s*[:#.\-]?\s*$", re.IGNORECASE)
_NOT_MODEL_LABEL = re.compile(
    r"\b(?:LOT|BATCH|B\.?\s?NO\.?|MRP|RS\.?|INR|FSSAI|LIC(?:ENSE)?\.?\s*NO\.?|S/?N|SERIAL"
    r"(?:\s*NO\.?)?|EAN|UPC|TEL|PH|MOB(?:ILE)?|PIN)\s*[:#.\-]?\s*$", re.IGNORECASE)
_WEB = re.compile(r"WWW|\.(?:COM|IN|ORG|NET|CO)\b", re.IGNORECASE)

_BOILERPLATE = re.compile(
    r"\b(?:INGREDIENTS?|NUTRI\w*|NETT?|MRP|PRICE|BATCH|LOT|MFD|MFG|PKD|PACKED|EXP\w*|BEST\s+BEFORE"
    r"|USE\s+BY|USE\s+BEFORE|CONSUME|FSSAI|LIC(?:ENSE)?|MADE\s+IN|MANUFACTURED|MARKETED"
    r"|DISTRIBUTED|CUSTOMER|CARE|WWW|HTTPS?|E-?MAIL|TEL|PHONE|STORE|KEEP|WARNING|CAUTION"
    r"|DIRECTIONS?|INCL|TAX(?:ES)?|BARCODE|CONTAINS|ALLERGENS?|ENERGY|PROTEIN|CARBOHYDRATES?"
    r"|FAT|SUGARS?|SODIUM|SERIAL|ROHS|PATENT|COPYRIGHT)\b|@|₹|©", re.IGNORECASE)
_EDGE_PUNCTUATION = " -–:;,.|*•"


def propose(lines: list[Line], today: date) -> dict:
    """`{"proposed": {field: proposal}, "notes": [sentence]}` for one reading."""
    if not lines:
        return {"proposed": {}, "notes": ["No text was found in the photo."]}
    proposed: dict[str, dict] = {}
    notes: list[str] = []
    model = _model(lines)
    for field, found in (("expiry_date", _expiry(lines, today, notes)), ("model", model),
                         ("size", _size(lines)), ("name", _name(lines, model))):
        if found is not None:
            proposed[field] = found
    return {"proposed": proposed, "notes": notes}


def _proposal(value, confidence: str, text: str, flags: list[str] | None = None) -> dict:
    return {"value": value, "source": "ocr", "confidence": confidence, "flags": flags or [],
            "text": text}


def _clean(text: str) -> str:
    return " ".join(text.split())


def _sure(confidence: float, labelled: bool) -> str:
    if confidence < 0.75:
        return "low"
    return "high" if labelled and confidence >= 0.9 else "medium"


def _expiry(lines: list[Line], today: date, notes: list[str]) -> dict | None:
    joined = "\n".join(_clean(line.text) for line in lines)
    reading = parse_expiry(joined, today)
    if reading.date is None:
        if "mfd_only" in reading.flags:
            notes.append(f"Only a manufacture or packing date was found ({reading.text}); "
                         "it is never used as the expiry.")
        elif "invalid" in reading.flags:
            notes.append(f"A date was found that is not a real date ({reading.text}); "
                         "check it on the pack.")
        return None
    flags = list(reading.flags)
    if {"ambiguous", "unlabelled", "far_past", "far_future"} & set(flags):
        confidence = "low"
    elif {"month_only", "computed", "ocr_fix"} & set(flags):
        confidence = "medium"
    else:
        confidence = "high"
    start = joined.find(reading.text)
    covering = [line.confidence for line, (first, last) in zip(lines, _line_spans(lines),
                                                               strict=True)
                if first < start + len(reading.text) and start < last]
    worst = min(covering, default=1.0)
    if worst < 0.75:
        confidence = "low"
    elif worst < 0.9 and confidence == "high":
        confidence = "medium"
    found = _proposal(reading.date.isoformat(), confidence, reading.text, flags)
    if reading.alternatives:
        found["alternatives"] = [other.isoformat() for other in reading.alternatives]
    return found


def _line_spans(lines: list[Line]) -> list[tuple[int, int]]:
    spans, position = [], 0
    for line in lines:
        length = len(_clean(line.text))
        spans.append((position, position + length))
        position += length + 1
    return spans


def covering(lines: list[Line], text: str) -> list[int]:
    """Indexes of the lines that hold `text` once the lines are joined, as `_expiry` joins them
    (a date may run over two lines). The camera coach marks those boxes as the date."""
    start = "\n".join(_clean(line.text) for line in lines).find(text)
    if start < 0 or not text:
        return []
    return [index for index, (first, last) in enumerate(_line_spans(lines))
            if first < start + len(text) and start < last]


def _sizes(text: str) -> list[re.Match]:
    return list(_SIZE.finditer(text))


def _size(lines: list[Line]) -> dict | None:
    found = [(bool(_NET_LINE.search(line.text)), index, match, line)
             for index, line in enumerate(lines) for match in _sizes(_clean(line.text))]
    if not found:
        return None
    on_net_line, _, match, line = min(found, key=lambda entry: (not entry[0], entry[1]))
    number = " ".join(match.group(1).split())
    unit = match.group(2)
    value = f'{number}"' if unit == '"' else f"{number} {_UNITS[unit.upper()]}"
    return _proposal(value, _sure(line.confidence, on_net_line), _clean(line.text))


def _model(lines: list[Line]) -> dict | None:
    best = None
    for index, line in enumerate(lines):
        text = _clean(line.text)
        taken = date_spans(text) + [match.span() for match in _sizes(text)]
        for token in _TOKEN.finditer(text):
            word = token.group()
            alnum = sum(c.isalnum() for c in word)
            has_digit = any(c.isdigit() for c in word)
            has_letter = any(c.isalpha() for c in word)
            if alnum < 4 or not has_digit or not (has_letter or "-" in word):
                continue
            if any(start < token.end() and token.start() < end for start, end in taken):
                continue
            before = text[:token.start()]
            if _NOT_MODEL_LABEL.search(before) or _WEB.search(word):
                continue
            labelled = bool(_MODEL_LABEL.search(before))
            rank = (labelled, has_letter and has_digit, len(word), -index)
            if best is None or rank > best[0]:
                best = (rank, word, line, text)
    if best is None:
        return None
    (labelled, mixed, length, _), word, line, text = best
    if labelled:
        confidence = _sure(line.confidence, True)
    else:
        confidence = "medium" if mixed and length >= 5 and line.confidence >= 0.9 else "low"
    return _proposal(word, confidence, text)


def _name_part(line: Line, model: dict | None) -> str | None:
    """What is left of a line once dates, sizes and the model are taken out, if it can be a name."""
    text = _clean(line.text)
    if _BOILERPLATE.search(text):
        return None
    rest = text
    for start, end in sorted(date_spans(text) + [m.span() for m in _sizes(text)], reverse=True):
        rest = rest[:start] + " " + rest[end:]
    if model is not None:
        rest = _MODEL_LABEL.sub(" ", rest.replace(model["value"], " "))
    letters = sum(c.isalpha() for c in rest)
    digits = sum(c.isdigit() for c in rest)
    return text if letters >= 3 and letters >= digits else None


def _name(lines: list[Line], model: dict | None) -> dict | None:
    candidates = sorted(((line.height * line.confidence, index, line)
                         for index, line in enumerate(lines)
                         if _name_part(line, model) is not None),
                        key=lambda entry: (-entry[0], entry[1]))
    if not candidates:
        return None
    score, _, line = candidates[0]
    runner_up = candidates[1][0] if len(candidates) > 1 else 0.0
    clear_winner = score >= 1.25 * runner_up
    value = _clean(line.text).strip(_EDGE_PUNCTUATION)
    if value.upper() == value and sum(c.isalpha() for c in value) >= 4:
        value = " ".join(word.capitalize() if word.isalpha() else word for word in value.split())
    return _proposal(value[:NAME_MAX], _sure(line.confidence, clear_winner), _clean(line.text))
