from __future__ import annotations

import logging
import re
import time
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

    RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        search_endpoint: str | None = None,
        max_posts: int | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.token = self._normalize_token(token or settings.threads_access_token)
        self.base_url = (base_url or settings.threads_api_base_url).rstrip("/")
        self.search_endpoint = search_endpoint or settings.threads_search_endpoint
        self.max_posts = max_posts or settings.max_posts
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _normalize_token(token: str) -> str:
        normalized = token.strip().strip('"').strip("'")
        if normalized.lower().startswith("bearer "):
            normalized = normalized[7:].strip()
        return normalized

    @staticmethod
    def _safe_response_excerpt(response: requests.Response) -> str:
        raw = (response.text or "").strip()
        if not raw:
            return "respons kosong/non-JSON"
        raw = re.sub(r"\s+", " ", raw)
        return raw[:300]

    @staticmethod
    def _api_error_message(response: requests.Response, payload: Any) -> str:
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                detail = str(error.get("message") or "Unknown Meta API error")
                metadata = []
                for label, key in (
                    ("code", "code"),
                    ("subcode", "error_subcode"),
                    ("trace", "fbtrace_id"),
                ):
                    if error.get(key) not in (None, ""):
                        metadata.append(f"{label}={error[key]}")
                suffix = f" ({', '.join(metadata)})" if metadata else ""
                return f"Threads API HTTP {response.status_code}: {detail}{suffix}"

        excerpt = ThreadsOfficialCollector._safe_response_excerpt(response)
        if response.status_code >= 500:
            return (
                f"Meta Threads API HTTP {response.status_code}: {excerpt}. "
                "Server Meta tidak memberi error JSON; coba lagi setelah token "
                "terverifikasi."
            )
        return f"Threads API HTTP {response.status_code}: {excerpt}"

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "ThreadsProductRadar/1.0",
        }
        response: requests.Response | None = None
        for attempt in range(2):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                logger.warning("Threads API network request failed: %s", type(exc).__name__)
                raise CollectorError(
                    "Threads API tidak dapat dijangkau dari server. Periksa koneksi "
                    "outbound/DNS VPS lalu coba lagi."
                ) from exc

            if response.status_code not in self.RETRYABLE_STATUS_CODES or attempt == 1:
                break
            time.sleep(0.4)

        assert response is not None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if not response.ok:
            raise CollectorError(self._api_error_message(response, payload))
        if not isinstance(payload, dict):
            raise CollectorError(
                "Threads API mengembalikan respons sukses yang bukan JSON object."
            )
        return payload

    def validate_token(self) -> dict[str, Any]:
        """Validate that the saved credential is a Threads user access token."""
        if not self.token:
            raise CollectorError("Threads access token belum dikonfigurasi.")
        return self._get_json(
            f"{self.base_url}/me",
            {"fields": "id,username"},
        )

    def collect(self, request: CollectionRequest) -> list[dict[str, Any]]:
        if not self.token:
            raise CollectorError("Threads access token belum dikonfigurasi.")
        if request.start_date > request.end_date:
            raise CollectorError("Start date tidak boleh melewati end date.")

        url = f"{self.base_url}{self.search_endpoint}"
        params = {
            "q": request.keyword,
            "search_type": request.search_type.upper(),
            "search_mode": "KEYWORD",
            "limit": min(max(request.limit, 1), self.max_posts),
            "fields": ",".join(self.FIELD_MAP),
        }
        payload = self._get_json(url, params)

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
