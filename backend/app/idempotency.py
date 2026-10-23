"""Idempotency-Key for creates (API 1): a repeat within 10 minutes returns the first result.

Kept in memory, which is enough for the one worker process (ARCHITECTURE 6). A failed request
is not remembered, so retrying with the same key tries again. Two requests with the same key
at the same moment run one after the other, and the second gets the first one's result.
"""

import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
TTL_SECONDS = 600
KEY_MAX = 200


class IdempotencyStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._done: dict[tuple[str, str], tuple[float, object]] = {}
        self._gates: dict[tuple[str, str], threading.Lock] = {}

    def _sweep(self, now: float) -> None:
        for key in [k for k, (expires, _) in self._done.items() if expires <= now]:
            del self._done[key]

    def run(self, scope: str, key: str | None, work: Callable[[], T]) -> T:
        if not key:
            return work()
        slot = (scope, key[:KEY_MAX])
        with self._lock:
            self._sweep(time.monotonic())
            if slot in self._done:
                return self._done[slot][1]  # type: ignore[return-value]
            gate = self._gates.setdefault(slot, threading.Lock())
        with gate:
            with self._lock:
                if slot in self._done:
                    return self._done[slot][1]  # type: ignore[return-value]
            try:
                result = work()
            except BaseException:
                with self._lock:
                    self._gates.pop(slot, None)
                raise
            with self._lock:  # remembered before the gate goes, so no third request slips in
                self._done[slot] = (time.monotonic() + TTL_SECONDS, result)
                self._gates.pop(slot, None)
            return result
