"""Write the OpenAPI document that the frontend's API types are generated from.

    python scripts/export_openapi.py <output.json>

It builds the app (live settings, so no test-only routes) without starting it and without
touching any data. `openapi-typescript` turns the file into `frontend/src/api/schema.d.ts`
(ARCHITECTURE 7). Keys are sorted so the output only changes when the API does.
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def build_document() -> dict:
    return create_app(start_scheduler=False).openapi()


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python scripts/export_openapi.py <output.json>", file=sys.stderr)
        return 2
    Path(argv[0]).write_text(json.dumps(build_document(), indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
