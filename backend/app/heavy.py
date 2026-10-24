"""The one executor for heavy work: photo processing and OCR (ARCHITECTURE 6, Process model).

It has a single worker, so heavy jobs run one at a time and queue behind each other while the
request threads, and with them `/health`, stay free.
"""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="heavy")


def run[T](work: Callable[..., T], *args) -> T:
    """Run in the heavy worker and wait for the answer (the caller is a request thread)."""
    return _executor.submit(work, *args).result()


def submit(work: Callable[..., object], *args) -> Future:
    """Queue in the heavy worker and return at once (background jobs such as a reading)."""
    return _executor.submit(work, *args)
