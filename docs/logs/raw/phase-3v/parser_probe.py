"""P2: adversarial expiry inputs beyond the 35 supplied cases (verification only)."""
from datetime import date
from app.services.expiry_parser import parse_expiry

T = date(2026, 10, 17)
CASES = [
    "MFD 12/01/2026",                       # only a manufacture date: no expiry
    "MFD 01/02/2026 BEST BEFORE 12 MONTHS FROM MFD",
    "EXP 31/02/2027",                       # impossible date
    "EXP 13/13/2027",
    "USE BY 05 JAN 27",
    "BB 02/2027",                           # month only
    "EXP: 2027-03-14",
    "BATCH 12/34/56 EXP 01/06/2027",
    "Net 500 ml",                           # no date at all
    "PKD 10/2026 EXP 10/2025",              # expiry before packing
    "EXP 1O/O3/2O27",                       # look-alike O
    "EXP 03/04/2099",                       # far future
    "",
]
for c in CASES:
    r = parse_expiry(c, T)
    print(f"{c!r:50} -> {r.date} flags={r.flags} alt={r.alternatives}")
