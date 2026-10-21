"""The committed OpenAPI file (the source of the frontend's types) must match the backend.

The frontend's `src/api/schema.d.ts` is generated from `frontend/openapi.json`; `test.bat unit`
checks that step too (`npm run api-types:check`). If this test fails, run `test.bat types`.
"""

import json
from pathlib import Path

from scripts.export_openapi import build_document

COMMITTED = Path("/frontend/openapi.json")  # the tools image has the frontend folder at /frontend


def test_the_committed_openapi_document_matches_the_backend():
    assert COMMITTED.is_file(), "frontend/openapi.json is missing; run test.bat types"
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    current = json.loads(json.dumps(build_document(), sort_keys=True))
    assert committed == current, "the API changed; run test.bat types and commit the result"


def test_the_document_describes_the_endpoints_the_frontend_calls():
    paths = build_document()["paths"]
    for path in ("/health", "/api/v1/profile", "/api/v1/settings", "/api/v1/backups"):
        assert path in paths
    assert not [p for p in paths if p.startswith("/api/v1/test")], "test routes never ship"
