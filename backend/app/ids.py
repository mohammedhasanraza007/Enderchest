"""Public item ids: `ENDR-` + 8 Crockford base-32 characters (DATA_MODEL 2.6).

The QR code encodes only this id. The alphabet leaves out I, L, O and U, so a typed id can be
read back even when the owner types the look-alikes (API 2.7, lookup).
"""

import re
import secrets

PREFIX = "ENDR-"
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
BODY_LENGTH = 8
_PUBLIC_ID = re.compile(rf"^ENDR-[{ALPHABET}]{{{BODY_LENGTH}}}$")
_LOOK_ALIKES = str.maketrans({"I": "1", "L": "1", "O": "0"})


def new_public_id() -> str:
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(BODY_LENGTH))


def is_public_id(value: str) -> bool:
    return bool(_PUBLIC_ID.match(value))


def normalise(code: str) -> str | None:
    """Turn a scanned or typed code into a public id, or None when it cannot be one.

    Accepts lowercase, spaces, `I`/`L` for 1 and `O` for 0, and the prefix with or without
    its dash (`endr-7k2m9qxa`, `ENDR7K2M9QXA`) or left out (`7K2M9QXA`).
    """
    text = re.sub(r"\s+", "", code).upper()
    if text.startswith("ENDR"):
        text = text[4:]
    text = text.removeprefix("-").translate(_LOOK_ALIKES)
    candidate = PREFIX + text
    return candidate if is_public_id(candidate) else None
