"""Runtime settings, read once from the environment (docs/ARCHITECTURE.md 5)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_VERSION = "0.1.0"
INTERNAL_PORT = 8470
DEFAULT_FRONTEND_DIR = Path("/app/frontend-dist")
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"  # D-102
DEFAULT_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
# The Ryzen 5 5500 has 6 cores: 4 reading threads leave room for the API and the browser.
DEFAULT_OCR_THREADS = 4


@dataclass(frozen=True)
class Settings:
    env: str  # "live" or "test"; must equal meta.env_marker (DATA_SAFETY 8)
    port: int  # the port the browser uses (published port), for the Host check
    data_dir: Path
    backups_dir: Path
    backup_dir_hint: str  # the host folder, shown to the owner only
    app_version: str = APP_VERSION
    gemini_model_default: str = DEFAULT_GEMINI_MODEL  # ENDERCHEST_GEMINI_MODEL
    gemini_url: str = DEFAULT_GEMINI_URL  # ENDERCHEST_GEMINI_URL; tests point it at a closed port
    ocr_threads: int = DEFAULT_OCR_THREADS  # ENDERCHEST_OCR_THREADS
    frontend_dir: Path = DEFAULT_FRONTEND_DIR  # the built frontend, copied into the image
    build_date: str | None = None  # ENDERCHEST_BUILD_DATE, set by build.bat; None if not recorded

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "enderchest.sqlite3"

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / "thumbs"

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "backup-staging"

    @property
    def upload_tmp_dir(self) -> Path:
        """Uploads are written here first, then renamed into `photos/` (same volume)."""
        return self.data_dir / "upload-tmp"

    @property
    def lock_path(self) -> Path:
        return self.data_dir / "lock"

    @property
    def backup_photos_dir(self) -> Path:
        return self.backups_dir / "photos"


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    mode = env.get("ENDERCHEST_ENV", "live")
    if mode not in ("live", "test"):
        raise ValueError(f"ENDERCHEST_ENV must be 'live' or 'test', not {mode!r}")
    backups_dir = Path(env.get("ENDERCHEST_BACKUPS_MOUNT", "/backups"))
    return Settings(
        env=mode,
        port=int(env.get("ENDERCHEST_PORT", str(INTERNAL_PORT))),
        data_dir=Path(env.get("ENDERCHEST_DATA_DIR", "/data")),
        backups_dir=backups_dir,
        backup_dir_hint=env.get("ENDERCHEST_BACKUP_DIR", str(backups_dir)),
        gemini_model_default=env.get("ENDERCHEST_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        gemini_url=env.get("ENDERCHEST_GEMINI_URL") or DEFAULT_GEMINI_URL,
        ocr_threads=int(env.get("ENDERCHEST_OCR_THREADS") or DEFAULT_OCR_THREADS),
        frontend_dir=Path(env.get("ENDERCHEST_FRONTEND_DIR", str(DEFAULT_FRONTEND_DIR))),
        build_date=(env.get("ENDERCHEST_BUILD_DATE") or None),
    )
