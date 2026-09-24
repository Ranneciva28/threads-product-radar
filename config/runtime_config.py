from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings


def _bounded_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


@dataclass(frozen=True)
class RuntimeConfig:
    threads_access_token: str = ""
    threads_api_base_url: str = "https://graph.threads.net/v1.0"
    threads_search_endpoint: str = "/keyword_search"
    max_posts: int = 250
    default_date_days: int = 30
    request_timeout_seconds: int = 30
    default_language: str = ""
    default_search_type: str = "RECENT"

    @classmethod
    def legacy_defaults(cls) -> "RuntimeConfig":
        """Import existing environment values once during the SQLite migration."""
        return cls(
            threads_access_token=settings.threads_access_token,
            threads_api_base_url=settings.threads_api_base_url,
            threads_search_endpoint=settings.threads_search_endpoint,
            max_posts=settings.max_posts,
            default_date_days=settings.default_date_days,
        )

    @classmethod
    def from_mapping(cls, values: dict[str, str]) -> "RuntimeConfig":
        defaults = cls.legacy_defaults()
        return cls(
            threads_access_token=values.get(
                "threads_access_token", defaults.threads_access_token
            ).strip(),
            threads_api_base_url=values.get(
                "threads_api_base_url", defaults.threads_api_base_url
            ).strip().rstrip("/"),
            threads_search_endpoint=values.get(
                "threads_search_endpoint", defaults.threads_search_endpoint
            ).strip(),
            max_posts=_bounded_int(
                values.get("max_posts"), defaults.max_posts, 1, 1000
            ),
            default_date_days=_bounded_int(
                values.get("default_date_days"), defaults.default_date_days, 1, 365
            ),
            request_timeout_seconds=_bounded_int(
                values.get("request_timeout_seconds"), 30, 5, 120
            ),
            default_language=values.get("default_language", "").strip(),
            default_search_type=(
                values.get("default_search_type", "RECENT").strip().upper()
                or "RECENT"
            ),
        )

    @property
    def api_configured(self) -> bool:
        return bool(self.threads_access_token)

    def as_storage(self) -> dict[str, str]:
        return {
            "threads_access_token": self.threads_access_token,
            "threads_api_base_url": self.threads_api_base_url,
            "threads_search_endpoint": self.threads_search_endpoint,
            "max_posts": str(self.max_posts),
            "default_date_days": str(self.default_date_days),
            "request_timeout_seconds": str(self.request_timeout_seconds),
            "default_language": self.default_language,
            "default_search_type": self.default_search_type,
        }


SECRET_SETTING_KEYS = {"threads_access_token"}
