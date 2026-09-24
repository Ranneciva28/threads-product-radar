from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from config.settings import settings
from collectors.base_collector import BaseCollector, CollectionRequest, CollectorError

logger = logging.getLogger(__name__)


class ThreadsOfficialCollector(BaseCollector):
    """Official Threads API adapter.

    The endpoint is configurable because Meta versions and availability may differ
    by app review status. Unknown API fields remain ``None``; nothing is inferred.
    """

    # Keep keyword-search fields to the public media fields supported by Meta.
    # Engagement metrics are exposed via the separate Insights API, not as
    # fields on /keyword_search.
    FIELD_MAP = {
        "id": "post_id",
        "username": "username",
        "text": "post_text",
        "timestamp": "created_at",
        "permalink": "permalink",
    }

    ENGAGEMENT_FIELDS = (
        "like_count",
        "reply_count",
        "repost_count",
        "quote_count",
        "views",
    )

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        search_endpoint: str | None = None,
        max_posts: int | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.token = token or settings.threads_access_token
        self.base_url = (base_url or settings.threads_api_base_url).rstrip("/")
        self.search_endpoint = search_endpoint or settings.threads_search_endpoint
        self.max_posts = max_posts or settings.max_posts
        self.timeout_seconds = timeout_seconds

    def collect(self, request: CollectionRequest) -> list[dict[str, Any]]:
        if not self.token:
            raise CollectorError("Threads access token belum dikonfigurasi.")
        if request.start_date > request.end_date:
            raise CollectorError("Start date tidak boleh melewati end date.")

        url = f"{self.base_url}{self.search_endpoint}"
        params = {
            "q": request.keyword,
            "search_type": request.search_type.upper(),
            "limit": min(max(request.limit, 1), self.max_posts),
            "fields": ",".join(self.FIELD_MAP),
            "access_token": self.token,
        }
        try:
            response = requests.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.exception("Threads API request failed")
            message = "Threads API gagal diakses. Periksa token, izin aplikasi, dan endpoint."
            if getattr(exc, "response", None) is not None:
                try:
                    detail = exc.response.json().get("error", {}).get("message")
                    if detail:
                        message = f"Threads API: {detail}"
                except ValueError:
                    status = getattr(exc.response, "status_code", None)
                    raw = (getattr(exc.response, "text", "") or "").strip()
                    raw = raw[:300]
                    if status or raw:
                        message = f"Threads API gagal (HTTP {status or 'unknown'}): {raw or 'respons non-JSON'}"
            raise CollectorError(message) from exc
        except ValueError as exc:
            raise CollectorError("Respons Threads API bukan JSON yang valid.") from exc

        rows: list[dict[str, Any]] = []
        for item in payload.get("data", []) or []:
            row = {target: item.get(source) for source, target in self.FIELD_MAP.items()}
            row.update({field: None for field in self.ENGAGEMENT_FIELDS})
            row.update(
                {
                    "display_name": item.get("display_name"),
                    "keyword_source": request.keyword,
                    "search_type": request.search_type.upper(),
                    "language": request.language,
                    "crawl_timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_source": "THREADS_API",
                    "replies_text": item.get("replies_text"),
                }
            )
            timestamp = row.get("created_at")
            if timestamp:
                try:
                    created_date = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).date()
                    if not request.start_date <= created_date <= request.end_date:
                        continue
                except ValueError:
                    pass
            rows.append(row)
        return rows
