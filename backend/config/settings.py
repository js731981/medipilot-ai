from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel
from dotenv import load_dotenv


_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_REPO_ROOT / ".env", override=False)


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    service_port: int = int(os.getenv("SERVICE_PORT", "3000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]

