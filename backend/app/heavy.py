"""The one executor for heavy work: photo processing, OCR and embeddings (ARCHITECTURE 6).

It has a single worker, so heavy jobs run one at a time and queue behind each other while the
request threads, and with them `/health`, stay free. A camera-coach frame must never queue
(D-121): `try_submit` refuses at once while any job is running or waiting.
"""

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="heavy")
_lock = threading.Lock()
_pending = 0  # jobs counted in and not yet finished, running or waiting


class Busy(Exception):
    """The worker has a job; the caller drops its work instead of waiting (D-121)."""


def _finished() -> None:
    global _pending
    with _lock:
        _pending -= 1


def _start(work: Callable[..., object], *args) -> Future:
    """Hand an already counted job to the worker. It counts itself out before its answer is
    set, so a caller that has the answer sees the worker idle."""
    def job():
        try:
            return work(*args)
        finally:
            _finished()

    try:
        return _executor.submit(job)
    except RuntimeError:
        _finished()
        raise


def _count_in() -> None:
    global _pending
    with _lock:
        _pending += 1


def run[T](work: Callable[..., T], *args) -> T:
    """Run in the heavy worker and wait for the answer (the caller is a request thread)."""
    _count_in()
    return _start(work, *args).result()


def submit(work: Callable[..., object], *args) -> Future:
    """Queue in the heavy worker and return at once (background jobs such as a reading)."""
    _count_in()
    return _start(work, *args)


def try_submit(work: Callable[..., object], *args) -> Future:
    """Start at once in an idle worker, or raise `Busy` without queueing anything."""
    global _pending
    with _lock:
        if _pending:
            raise Busy
        _pending += 1
    return _start(work, *args)
