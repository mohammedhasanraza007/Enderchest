"""Expiry dates from printed text (Phase 3 spec, "Expiry rules"; the 35 cases in
`tests/fixtures/expiry_cases.csv` are the exact test).

A date after an EXP-type label is the expiry; a date after a manufacture or packing label never
is. Numeric dates are read day first (India); when the month-first reading is also a real and
different date, both are offered (`ambiguous`). Nothing here is trusted: the owner confirms every
date on the confirm screen (P-07).
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date

_MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_MONTH = (r"(JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?"
          r"|SEPT?(?:EMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)")

_EXPIRY_LABEL = re.compile(
    r"\b(?:EXP(?:IRY|IRES|\.)?(?:\s*DATE)?|USE\s+BY|USE\s+BEFORE|BEST\s+BEFORE(?:\s+END)?"
    r"|CONSUME\s+BEFORE|B\.\s?B\.?|BB)(?![A-Z])")
_MADE_LABEL = re.compile(
    r"\b(?:MFG\.?\s*DATE|MFGD|MFG|MFD|MANUFACTURED(?:\s+ON)?|(?:DATE\s+OF\s+)?MANUFACTURE"
    r"|PKG\.?\s*DATE|PACKING\s+DATE|PACKED(?:\s+ON)?|PKD)(?![A-Z])")

# Most specific first; each match is masked so a shorter shape cannot reuse its digits.
_ISO = re.compile(r"(?<!\d)(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(?!\d)")
_DAY_NAME_YEAR = re.compile(
    rf"(?<!\d)(\d{{1,2}})(?:ST|ND|RD|TH)?[\s\-./,]*\b{_MONTH}[\s\-./,']*(\d{{4}}|\d{{2}})(?!\d)")
_DAY_MONTH_YEAR = re.compile(r"(?<![\d/.\-])(\d{1,2})([/\-. ])(\d{1,2})\2(\d{4}|\d{2})(?!\d)")
_NAME_YEAR = re.compile(rf"\b{_MONTH}[\s\-./,']*(\d{{4}}|\d{{2}})(?!\d)")
_MONTH_YEAR = re.compile(r"(?<![\d/.\-])(\d{1,2})[/\-.](\d{4}|\d{2})(?![\d/.\-])")
_SHELF_LIFE = re.compile(r"(?<!\d)(\d{1,3})\s*(MONTHS?|MTHS?|YEARS?|YRS?)(?![A-Z])")

# Look-alike letters inside date-shaped runs only, so words and batch codes are left alone.
_LOOK_ALIKES = str.maketrans({"O": "0", "I": "1", "L": "1"})
_NUMERIC_RUN = re.compile(r"(?<![A-Z0-9])[0-9OIL]{1,4}(?:[/\-.][0-9OIL]{1,4}){1,2}(?![A-Z0-9])")
_NAMED_RUN = re.compile(
    rf"(?<![A-Z0-9])([0-9OIL]{{1,2}})(\s*{_MONTH}\s*)([0-9OIL]{{2,4}})(?![A-Z0-9])")
_GROUP = re.compile(r"[0-9OIL]+")

FAR_PAST_YEARS = 10
FAR_FUTURE_YEARS = 15


@dataclass(frozen=True)
class ExpiryReading:
    date: date | None
    flags: tuple[str, ...] = ()
    alternatives: tuple[date, ...] = ()
    text: str = ""  # the label and date as printed, for the "What was read" drawer


@dataclass(frozen=True)
class _Found:
    start: int
    end: int
    readings: tuple[date, ...]  # the chosen reading first; empty when the date is impossible
    month_only: bool = False


def date_spans(text: str) -> list[tuple[int, int]]:
    """Where date-shaped runs sit in the text, labelled or not, real dates or not."""
    fixed, _ = _fix_look_alikes(_upper(text))
    return [(found.start, found.end) for found in _find_dates(fixed)[0]]


def _upper(text: str) -> str:
    return "".join(c.upper() if len(c.upper()) == 1 else c for c in text)  # keeps positions


def parse_expiry(text: str, today: date) -> ExpiryReading:
    fixed, fixed_at = _fix_look_alikes(_upper(text))
    dates, masked = _find_dates(fixed)
    labels = sorted([(m.start(), m.end(), "expiry") for m in _EXPIRY_LABEL.finditer(fixed)]
                    + [(m.start(), m.end(), "made") for m in _MADE_LABEL.finditer(fixed)])

    def label_before(position: int) -> tuple[int, str] | None:
        found = [(start, kind) for start, end, kind in labels if end <= position]
        return found[-1] if found else None

    expiry, made, unlabelled = [], [], []
    for found in dates:
        label = label_before(found.start)
        if label is None:
            unlabelled.append((found.start, found))
        else:
            (expiry if label[1] == "expiry" else made).append((label[0], found))

    def result(start: int, found: _Found, extra: tuple[str, ...] = ()) -> ExpiryReading:
        flags = list(extra)
        if len(found.readings) > 1:
            flags.append("ambiguous")
        if found.month_only:
            flags.append("month_only")
        return _finish(found.readings[0], flags, found.readings[1:], text[start:found.end],
                       _touches(fixed_at, found.start, found.end), today)

    valid_expiry = [(start, found) for start, found in expiry if found.readings]
    if valid_expiry:
        return result(*valid_expiry[0])
    computed = _computed(masked, text, made, label_before, fixed_at, today)
    if computed is not None:
        return computed
    if expiry:
        return ExpiryReading(None, ("invalid",), text=text[expiry[0][0]:expiry[0][1].end])
    valid_loose = [(start, found) for start, found in unlabelled if found.readings]
    if valid_loose:
        start, found = max(valid_loose, key=lambda pair: pair[1].readings[0])
        return result(start, found, ("unlabelled",))
    if made:
        return ExpiryReading(None, ("mfd_only",), text=text[made[0][0]:made[0][1].end])
    if unlabelled:
        return ExpiryReading(None, ("invalid",), text=text[unlabelled[0][0]:unlabelled[0][1].end])
    return ExpiryReading(None, ("no_date",))


def _computed(masked: str, text: str, made: list, label_before, fixed_at: set[int],
              today: date) -> ExpiryReading | None:
    """A shelf life after an EXP-type label, counted from the manufacture or packing date."""
    base = next(((start, found) for start, found in made if found.readings), None)
    if base is None:
        return None
    for life in _SHELF_LIFE.finditer(masked):
        label = label_before(life.start())
        if label is None or label[1] != "expiry":
            continue
        months = int(life.group(1)) * (12 if life.group(2).startswith("Y") else 1)
        start, found = base
        expiry = _add_months(found.readings[0], months, end_of_month=found.month_only)
        return _finish(expiry, ["computed"], (), text[start:life.end()],
                       _touches(fixed_at, found.start, found.end), today)
    return None


def _finish(chosen: date, flags: list[str], alternatives: tuple[date, ...], text: str,
            ocr_fixed: bool, today: date) -> ExpiryReading:
    if ocr_fixed:
        flags.append("ocr_fix")
    if chosen < _shift_years(today, -FAR_PAST_YEARS):
        flags.append("far_past")
    if chosen > _shift_years(today, FAR_FUTURE_YEARS):
        flags.append("far_future")
    return ExpiryReading(chosen, tuple(flags), alternatives, text.strip())


def _find_dates(text: str) -> tuple[list[_Found], str]:
    """Every date-shaped run in the text, and the text with those runs masked out."""
    found: list[_Found] = []
    masked = text

    def take(pattern: re.Pattern, read) -> None:
        nonlocal masked
        for match in pattern.finditer(masked):
            reading = read(match)
            if reading is None:
                continue
            found.append(reading)
            masked = masked[:match.start()] + "#" * (match.end() - match.start()) \
                + masked[match.end():]

    take(_ISO, lambda m: _Found(m.start(), m.end(),
                                _valid((int(m[1]), int(m[3]), int(m[4])))))
    take(_DAY_NAME_YEAR, lambda m: _Found(m.start(), m.end(),
                                          _valid((_year(m[3]), _month(m[2]), int(m[1])))))
    take(_DAY_MONTH_YEAR, _numeric)
    take(_NAME_YEAR, lambda m: _Found(m.start(), m.end(), (_month_end(_year(m[2]), _month(m[1])),),
                                      month_only=True))
    take(_MONTH_YEAR, lambda m: None if not 1 <= int(m[1]) <= 12 else _Found(
        m.start(), m.end(), (_month_end(_year(m[2]), int(m[1])),), month_only=True))
    found.sort(key=lambda item: item.start)
    return found, masked


def _numeric(match: re.Match) -> _Found:
    first, second, year = int(match[1]), int(match[3]), _year(match[4])
    day_first = _valid((year, second, first))
    month_first = _valid((year, first, second))
    readings = day_first + tuple(d for d in month_first if d not in day_first)
    return _Found(match.start(), match.end(), readings)


def _valid(parts: tuple[int, int, int]) -> tuple[date, ...]:
    try:
        return (date(*parts),)
    except ValueError:
        return ()


def _year(digits: str) -> int:
    return 2000 + int(digits) if len(digits) == 2 else int(digits)


def _month(name: str) -> int:
    return _MONTH_NAMES.index(name[:3]) + 1


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _add_months(day: date, months: int, end_of_month: bool) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    last = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, last if end_of_month else min(day.day, last))


def _shift_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 February in a year that has none
        return day.replace(year=day.year + years, day=28)


def _fix_look_alikes(text: str) -> tuple[str, set[int]]:
    """Read O as 0 and I or l as 1 inside date-shaped runs; return the positions changed."""
    chars = list(text)
    changed: set[int] = set()

    def fix(start: int, end: int) -> None:
        for group in _GROUP.finditer(text, start, end):
            if any(c.isdigit() for c in group[0]):
                for index in range(group.start(), group.end()):
                    digit = chars[index].translate(_LOOK_ALIKES)
                    if digit != chars[index]:
                        chars[index] = digit
                        changed.add(index)

    for run in _NUMERIC_RUN.finditer(text):
        fix(run.start(), run.end())
    for run in _NAMED_RUN.finditer(text):
        fix(run.start(1), run.end(1))
        fix(run.start(4), run.end(4))
    return "".join(chars), changed


def _touches(positions: set[int], start: int, end: int) -> bool:
    return any(start <= index < end for index in positions)
