from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, time as dt_time, timezone
from typing import Any

import requests

from config.settings import settings
from collectors.base_collector import BaseCollector, CollectionRequest, CollectorError

logger = logging.getLogger(__name__)


class ThreadsOfficialCollector(BaseCollector):
    """Official Threads keyword-search collector for public market research.

    The collector only asks Meta for fields documented on Threads media objects.
    Engagement counters are intentionally left unavailable when keyword search
    does not return them; downstream scoring re-weights around missing metrics
    instead of inventing zero engagement.
    """

    FIELD_MAP = {
        "id": "post_id",
        "username": "username",
        "text": "post_text",
        "timestamp": "created_at",
        "permalink": "permalink",
        "media_type": "media_type",
        "shortcode": "shortcode",
        "is_quote_post": "is_quote_post",
        "has_replies": "has_replies",
        "topic_tag": "topic_tag",
        "is_verified": "is_verified",
        "profile_picture_url": "profile_picture_url",
    }

    ENGAGEMENT_FIELDS = (
        "like_count",
        "reply_count",
        "repost_count",
        "quote_count",
        "views",
    )

    RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
    PAGE_SIZE = 50

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
        self.last_success_base_url: str | None = None
        self.last_pages_fetched = 0
        self.last_raw_count = 0

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
                "Server Meta tidak memberi error JSON."
            )
        return f"Threads API HTTP {response.status_code}: {excerpt}"

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "ThreadsProductRadar/2.0",
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

    def _base_candidates(self) -> list[str]:
        candidates = [self.base_url]
        bare = "https://graph.threads.net"
        versioned = f"{bare}/v1.0"
        if self.base_url == versioned:
            candidates.append(bare)
        elif self.base_url == bare:
            candidates.append(versioned)
        return candidates

    def _get_json_path(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: CollectorError | None = None
        attempted: list[str] = []
        for index, base in enumerate(self._base_candidates()):
            url = f"{base}{path}"
            attempted.append(url)
            try:
                payload = self._get_json(url, params)
                self.last_success_base_url = base
                return payload
            except CollectorError as exc:
                last_error = exc
                message = str(exc)
                if index == 0 and any(
                    f"HTTP {code}" in message for code in self.RETRYABLE_STATUS_CODES
                ):
                    continue
                raise
        detail = str(last_error) if last_error else "unknown error"
        raise CollectorError(
            f"{detail} | Endpoint dicoba: {' -> '.join(attempted)}"
        )

    @staticmethod
    def _date_window_params(request: CollectionRequest) -> tuple[int, int]:
        start_dt = datetime.combine(request.start_date, dt_time.min, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if request.end_date >= now.date():
            end_dt = now
        else:
            end_dt = datetime.combine(
                request.end_date, dt_time.max, tzinfo=timezone.utc
            )
        if end_dt <= start_dt:
            end_dt = start_dt.replace(microsecond=0) + __import__("datetime").timedelta(seconds=1)
        return int(start_dt.timestamp()), int(end_dt.timestamp())

    @staticmethod
    def _sqlite_value(value: Any) -> Any:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return value

    def validate_token(self) -> dict[str, Any]:
        if not self.token:
            raise CollectorError("Threads access token belum dikonfigurasi.")
        return self._get_json_path(
            "/me",
            {"fields": "id,username"},
        )

    def collect(self, request: CollectionRequest) -> list[dict[str, Any]]:
        if not self.token:
            raise CollectorError("Threads access token belum dikonfigurasi.")
        if request.start_date > request.end_date:
            raise CollectorError("Start date tidak boleh melewati end date.")

        target = min(max(request.limit, 1), self.max_posts)
        since, until = self._date_window_params(request)
        base_params: dict[str, Any] = {
            "q": request.keyword,
            "search_type": request.search_type.upper(),
            "fields": ",".join(self.FIELD_MAP),
            "since": since,
            "until": until,
        }

        rows: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_links: set[str] = set()
        seen_cursors: set[str] = set()
        after: str | None = None
        self.last_pages_fetched = 0
        self.last_raw_count = 0

        while len(rows) < target:
            params = dict(base_params)
            params["limit"] = min(self.PAGE_SIZE, target - len(rows))
            if after:
                params["after"] = after

            payload = self._get_json_path(self.search_endpoint, params)
            self.last_pages_fetched += 1
            items = payload.get("data", []) or []
            if not isinstance(items, list):
                raise CollectorError("Threads API mengembalikan field data yang tidak valid.")
            self.last_raw_count += len(items)

            for item in items:
                if not isinstance(item, dict):
                    continue
                post_id = str(item.get("id") or "").strip()
                permalink = str(item.get("permalink") or "").strip()
                if post_id and post_id in seen_ids:
                    continue
                if permalink and permalink in seen_links:
                    continue

                row = {
                    target_field: self._sqlite_value(item.get(source_field))
                    for source_field, target_field in self.FIELD_MAP.items()
                }
                row.update({field: None for field in self.ENGAGEMENT_FIELDS})
                row.update(
                    {
                        "display_name": item.get("display_name"),
                        "keyword_source": request.keyword,
                        "search_type": request.search_type.upper(),
                        "language": request.language,
                        "crawl_timestamp": datetime.now(timezone.utc).isoformat(),
                        "data_source": "THREADS_API",
                        "replies_text": None,
                        "engagement_available": 0,
                    }
                )
                rows.append(row)
                if post_id:
                    seen_ids.add(post_id)
                if permalink:
                    seen_links.add(permalink)
                if len(rows) >= target:
                    break

            paging = payload.get("paging") or {}
            cursors = paging.get("cursors") if isinstance(paging, dict) else {}
            next_after = cursors.get("after") if isinstance(cursors, dict) else None
            if (
                not items
                or not next_after
                or next_after == after
                or str(next_after) in seen_cursors
                or len(rows) >= target
            ):
                break
            seen_cursors.add(str(next_after))
            after = str(next_after)

        return rows
