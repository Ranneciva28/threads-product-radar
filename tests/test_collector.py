from datetime import date

import pytest
import requests

from collectors.base_collector import CollectionRequest, CollectorError
from collectors.threads_collector import ThreadsOfficialCollector


class FakeResponse:
    def __init__(self, payload, fail=False, status_code=None, text=""):
        self.payload = payload
        self.fail = fail
        self.status_code = status_code or (400 if fail else 200)
        self.text = text

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        if isinstance(self.payload, ValueError):
            raise self.payload
        return self.payload


def request():
    return CollectionRequest("template excel", date.today(), date.today(), limit=10)


def test_empty_api_response(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse({"data": []}))
    assert ThreadsOfficialCollector("token").collect(request()) == []


def test_api_error_is_wrapped(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse({"error": {"message": "bad token"}}, True))
    with pytest.raises(CollectorError):
        ThreadsOfficialCollector("token").collect(request())


def test_runtime_api_settings_are_used(monkeypatch):
    captured = {}

    def fake_get(url, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse({"data": []})

    monkeypatch.setattr(requests, "get", fake_get)
    collector = ThreadsOfficialCollector(
        token="token",
        base_url="https://example.test/v9/",
        search_endpoint="/search",
        max_posts=7,
        timeout_seconds=12,
    )
    today = date.today()
    collection_request = CollectionRequest(
        "template excel", today, today, limit=99
    )
    collector.collect(collection_request)

    assert captured["url"] == "https://example.test/v9/search"
    assert captured["params"]["limit"] == 7
    assert "access_token" not in captured["params"]
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["timeout"] == 12


def test_keyword_search_uses_only_supported_public_fields(monkeypatch):
    captured = {}

    def fake_get(url, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse({"data": []})

    monkeypatch.setattr(requests, "get", fake_get)
    ThreadsOfficialCollector(
        token="token",
        base_url="https://graph.threads.net",
        search_endpoint="/keyword_search",
    ).collect(request())

    requested_fields = set(captured["params"]["fields"].split(","))
    assert {"id", "username", "text", "timestamp", "permalink"}.issubset(requested_fields)
    assert {"media_type", "shortcode", "is_quote_post", "has_replies"}.issubset(requested_fields)
    assert "like_count" not in requested_fields
    assert "views" not in requested_fields
    assert "since" in captured["params"]
    assert "until" in captured["params"]


def test_validate_token_uses_me_endpoint_and_normalizes_bearer(monkeypatch):
    captured = {}

    def fake_get(url, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse({"id": "123", "username": "avicenna"})

    monkeypatch.setattr(requests, "get", fake_get)
    collector = ThreadsOfficialCollector(
        token='  "Bearer token-value"  ',
        base_url="https://graph.threads.net/v1.0",
    )

    assert collector.validate_token()["username"] == "avicenna"
    assert captured["url"] == "https://graph.threads.net/v1.0/me"
    assert captured["headers"]["Authorization"] == "Bearer token-value"


def test_non_json_server_error_is_actionable_and_retried(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse(ValueError("not json"), status_code=500, text="")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("collectors.threads_collector.time.sleep", lambda *_: None)

    with pytest.raises(CollectorError, match="Meta Threads API HTTP 500"):
        ThreadsOfficialCollector("token").collect(request())

    # Two attempts on the configured base plus two attempts on the alternate
    # Threads host form.
    assert len(calls) == 4


def test_versioned_500_falls_back_to_unversioned_host(monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(url)
        if "/v1.0/" in url:
            return FakeResponse(ValueError("not json"), status_code=500, text="")
        return FakeResponse({"id": "123", "username": "avicenna"})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("collectors.threads_collector.time.sleep", lambda *_: None)

    collector = ThreadsOfficialCollector(
        token="token",
        base_url="https://graph.threads.net/v1.0",
    )
    identity = collector.validate_token()

    assert identity["username"] == "avicenna"
    assert calls[-1] == "https://graph.threads.net/me"
    assert collector.last_success_base_url == "https://graph.threads.net"


def test_keyword_search_follows_after_cursor_until_limit(monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(dict(params))
        if len(calls) == 1:
            return FakeResponse({
                "data": [
                    {
                        "id": "1",
                        "username": "one",
                        "text": "need a notion template",
                        "timestamp": "2026-09-24T01:00:00+0000",
                        "permalink": "https://threads.net/t/1",
                        "has_replies": True,
                    }
                ],
                "paging": {"cursors": {"after": "NEXT"}},
            })
        return FakeResponse({
            "data": [
                {
                    "id": "2",
                    "username": "two",
                    "text": "looking for a budget planner",
                    "timestamp": "2026-09-24T02:00:00+0000",
                    "permalink": "https://threads.net/t/2",
                    "has_replies": False,
                }
            ],
            "paging": {"cursors": {}},
        })

    monkeypatch.setattr(requests, "get", fake_get)
    today = date(2026, 9, 24)
    collector = ThreadsOfficialCollector(
        "token", base_url="https://graph.threads.net", max_posts=10
    )
    rows = collector.collect(
        CollectionRequest("template", today, today, limit=2)
    )

    assert [row["post_id"] for row in rows] == ["1", "2"]
    assert calls[1]["after"] == "NEXT"
    assert collector.last_pages_fetched == 2
    assert collector.last_raw_count == 2
    assert rows[0]["engagement_available"] == 0


def test_keyword_search_deduplicates_pages(monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(dict(params))
        if len(calls) == 1:
            return FakeResponse({
                "data": [{
                    "id": "1", "username": "one", "text": "template",
                    "timestamp": "2026-09-24T01:00:00+0000",
                    "permalink": "https://threads.net/t/1",
                }],
                "paging": {"cursors": {"after": "NEXT"}},
            })
        return FakeResponse({
            "data": [{
                "id": "1", "username": "one", "text": "template",
                "timestamp": "2026-09-24T01:00:00+0000",
                "permalink": "https://threads.net/t/1",
            }],
            "paging": {"cursors": {}},
        })

    monkeypatch.setattr(requests, "get", fake_get)
    today = date(2026, 9, 24)
    rows = ThreadsOfficialCollector(
        "token", base_url="https://graph.threads.net", max_posts=10
    ).collect(CollectionRequest("template", today, today, limit=5))
    assert len(rows) == 1
