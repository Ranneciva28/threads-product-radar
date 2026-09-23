from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development").lower()
    username: str = os.getenv("APP_USERNAME", "")
    password: str = os.getenv("APP_PASSWORD", "")
    threads_access_token: str = os.getenv("THREADS_ACCESS_TOKEN", "")
    threads_api_base_url: str = os.getenv(
        "THREADS_API_BASE_URL", "https://graph.threads.net/v1.0"
    ).rstrip("/")
    threads_search_endpoint: str = os.getenv(
        "THREADS_SEARCH_ENDPOINT", "/keyword_search"
    )
    database_path: Path = ROOT / os.getenv(
        "DATABASE_PATH", "data/threads_product_radar.db"
    )
    default_date_days: int = _as_int("DEFAULT_DATE_DAYS", 30)
    max_posts: int = _as_int("MAX_POSTS", 250)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def api_configured(self) -> bool:
        return bool(self.threads_access_token)


settings = Settings()

