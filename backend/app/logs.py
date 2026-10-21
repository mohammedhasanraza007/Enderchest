"""Structured log lines to stdout. Never log keys, photos or note text (ARCHITECTURE 6)."""

import json
import sys
from datetime import UTC, datetime


def log_event(level: str, event: str, **fields: object) -> None:
    line = {"ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "level": level, "event": event}
    line.update(fields)
    print(json.dumps(line, default=str), file=sys.stdout, flush=True)
