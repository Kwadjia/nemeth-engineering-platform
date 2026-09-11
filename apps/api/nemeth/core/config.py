"""Application settings.

All configuration comes from the environment (prefix ``NEMETH_``) or a local ``.env``
file. Nothing in the code base reads ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    """Locate the monorepo root (the directory holding ``apps/`` and ``docs/``).

    Falls back to the current working directory when the package is installed
    elsewhere (for example at ``/app`` inside the API container), in which case the
    relevant paths are supplied through environment variables anyway.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "apps").is_dir() and (candidate / "docs").is_dir():
            return candidate
    return Path.cwd()


_REPO_ROOT = _find_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEMETH_",
        env_file=(".env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- runtime -----------------------------------------------------------------
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    app_name: str = "NEMETH Engineering Platform"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- database ----------------------------------------------------------------
    database_url: str = "postgresql+psycopg://nemeth:nemeth@localhost:5432/nemeth"
    test_database_url: str = "postgresql+psycopg://nemeth:nemeth@localhost:5432/nemeth_test"
    sql_echo: bool = False

    # --- logging -----------------------------------------------------------------
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    # --- file storage (ADR-003) --------------------------------------------------
    storage_backend: Literal["local"] = "local"
    storage_root: Path = _REPO_ROOT / "storage"
    upload_max_bytes: int = 200 * 1024 * 1024

    # --- auth boundary (single local actor until real auth exists) ---------------
    actor_id: str = "local"
    actor_name: str = "Local User"


@lru_cache
def get_settings() -> Settings:
    return Settings()
