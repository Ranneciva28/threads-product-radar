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
    assert captured["params"]["search_mode"] == "KEYWORD"
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
    assert requested_fields == {"id", "username", "text", "timestamp", "permalink"}
    assert "like_count" not in requested_fields
    assert "views" not in requested_fields


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

    assert len(calls) == 2


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
