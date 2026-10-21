"""The home page and the app's files.

State `ok`: every app route gets the built frontend's index.html, with the stored theme written
into it so the first paint is right. Any other state: the boot page (P-16), which works without
the database. Built files (scripts, styles, fonts, icons) are served in every state because the
boot pages use the same tokens CSS.
"""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from ..boot.manager import BootManager, Status
from ..errors import AppError
from ..services import profile as profile_service
from .deps import current_user_id, get_manager

router = APIRouter()
BOOT_PAGE = Path(__file__).parent.parent / "static" / "boot" / "boot.html"
ANY_METHOD = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
NO_STORE = {"Cache-Control": "no-store"}  # the same URL shows different pages as the state changes
_THEME_PREF = re.compile(r'data-theme-pref="[a-z]*"')


def _static_file(root: Path, path: str) -> Path | None:
    """A built file under `root`, or None. Never a path that climbs out of `root`."""
    if not path or path == "index.html":
        return None  # index.html is always served through the shell, with the theme written in
    try:
        base = root.resolve()
        candidate = (base / path).resolve()
    except (OSError, ValueError):  # for example an embedded NUL byte
        return None
    return candidate if candidate.is_file() and candidate.is_relative_to(base) else None


def _file_headers(path: str) -> dict[str, str]:
    # Vite names files under assets/ by content hash, so they can be cached for ever;
    # everything else (tokens.css, icons) is revalidated.
    cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
    return {"Cache-Control": cache, "X-Content-Type-Options": "nosniff"}


def _app_shell(manager: BootManager, user_id: int) -> Response:
    index = manager.settings.frontend_dir / "index.html"
    if not index.is_file():
        raise AppError("internal_error", 500,
                       "The app files are missing from this build. Run build.bat again.")
    theme = profile_service.get_profile(manager.db(), user_id)["theme"]
    html = _THEME_PREF.sub(f'data-theme-pref="{theme}"', index.read_text(encoding="utf-8"), count=1)
    return HTMLResponse(html, headers=NO_STORE)


@router.api_route("/", methods=ANY_METHOD, include_in_schema=False)
@router.api_route("/{path:path}", methods=ANY_METHOD, include_in_schema=False)
def app_page(request: Request, path: str = "", manager: BootManager = Depends(get_manager),
             user_id: int = Depends(current_user_id)) -> Response:
    # Every method is routed here so an unknown path answers 404 in the one error shape
    # instead of 405; only GET and HEAD can ever be a page.
    if request.method not in ("GET", "HEAD") or path == "api" or path.startswith("api/"):
        raise AppError("not_found", 404, "That does not exist.")
    built = _static_file(manager.settings.frontend_dir, path)
    if built is not None:
        return FileResponse(built, headers=_file_headers(path))
    last = path.rsplit("/", 1)[-1]
    if "." in last and path != "index.html":  # a missing file is a 404, never the app shell
        raise AppError("not_found", 404, "That does not exist.")
    if manager.state.status is not Status.OK:
        return FileResponse(BOOT_PAGE, headers=NO_STORE)
    return _app_shell(manager, user_id)
