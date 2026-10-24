"""Which readings are queued in this process (one worker, so memory is the truth).

A draft row that says `pending` while nothing here holds it was queued before a restart; the
draft view shows it as interrupted and Re-read can queue it again.
"""

import threading

_guard = threading.Lock()
_queued: set[tuple[str, str]] = set()  # (draft id, "ocr" or "gemini")


def claim(draft_id: str, kind: str) -> bool:
    """True if the caller may queue this reading; False if one is already queued."""
    with _guard:
        if (draft_id, kind) in _queued:
            return False
        _queued.add((draft_id, kind))
        return True


def release(draft_id: str, kind: str) -> None:
    with _guard:
        _queued.discard((draft_id, kind))


def is_queued(draft_id: str, kind: str) -> bool:
    with _guard:
        return (draft_id, kind) in _queued
