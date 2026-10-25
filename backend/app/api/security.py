"""Localhost API hardening (D-050, docs/ARCHITECTURE.md 9).

A local app is still a web server: any web page the owner visits can try to call it.
These checks refuse such calls before any route runs. No CORS headers are ever sent.
"""

import re
from collections.abc import Mapping

from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import INTERNAL_PORT
from ..errors import error_response

SAFE_METHODS = {"GET", "HEAD"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
MB = 1024 * 1024
JSON_BODY_MAX = 1 * MB
_ONE_IMAGE = 12 * MB + 64 * 1024  # one 12 MB photo plus the multipart framing
# Paths allowed to receive multipart bodies, each with the largest body it takes (D-095).
MULTIPART_PATHS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^/api/v1/items/[^/]+/photos$"), _ONE_IMAGE),
    (re.compile(r"^/api/v1/drafts$"), 20 * 12 * MB + MB),
    (re.compile(r"^/api/v1/drafts/[^/]+/photos$"), _ONE_IMAGE),
    (re.compile(r"^/api/v1/ownership/check$"), _ONE_IMAGE),
    (re.compile(r"^/api/v1/capture/frame$"), 200 * 1024 + 64 * 1024),  # one coach frame (API 2.15)
)


def multipart_limit(path: str) -> int | None:
    """The body cap for a path that takes uploads, or None when it takes JSON only."""
    for pattern, limit in MULTIPART_PATHS:
        if pattern.match(path):
            return limit
    return None


def _split_host(host_header: str) -> tuple[str, str]:
    if host_header.startswith("["):  # [::1]:8470
        name, _, rest = host_header.partition("]")
        return name + "]", rest.lstrip(":")
    name, _, port = host_header.partition(":")
    return name, port


def check_request(method: str, path: str, headers: Mapping[str, str],
                  app_port: int) -> tuple[str, int, str] | None:
    """Return (code, http status, message) when the request must be refused, else None."""
    host_header = headers.get("host", "").lower()
    name, port = _split_host(host_header)
    allowed_ports = {str(app_port), str(INTERNAL_PORT)}
    if name not in LOCAL_HOSTS or port not in allowed_ports:
        return ("forbidden_host", 403, "This address is not allowed.")

    if method in SAFE_METHODS:
        return None

    if headers.get("x-enderchest") != "1":
        return ("forbidden_host", 403, "The safety header is missing.")

    origin = headers.get("origin")
    if origin is not None and origin.lower() != f"http://{host_header}":
        return ("forbidden_host", 403, "Requests from other web pages are not allowed.")

    content_type = headers.get("content-type")
    length = headers.get("content-length", "")
    has_body = length not in ("", "0") or "transfer-encoding" in headers
    if content_type is not None or has_body:
        media = (content_type or "").split(";")[0].strip().lower()
        limit = multipart_limit(path) if media == "multipart/form-data" else None
        if limit is None and media != "application/json":
            return ("validation_error", 422, "Requests must be JSON.")
        if has_body and not length.isdigit():
            # Browsers always send the length; without it the cap below could not be checked.
            return ("validation_error", 422, "The request must state its length.")
        if has_body and int(length) > (limit or JSON_BODY_MAX):
            return ("payload_too_large", 413,
                    "That upload is too large. Each photo can be up to 12 MB."
                    if limit else "That request is too large.")
    return None


class SecurityMiddleware:
    """Plain ASGI middleware so it runs before routing and never buffers bodies."""

    def __init__(self, app: ASGIApp, app_port: int) -> None:
        self.app = app
        self.app_port = app_port

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        refusal = check_request(scope["method"], scope["path"], headers, self.app_port)
        if refusal is not None:
            code, status, message = refusal
            await error_response(code, status, message)(scope, receive, send)
            return
        await self.app(scope, receive, send)
