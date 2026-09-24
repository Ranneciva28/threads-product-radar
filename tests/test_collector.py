from datetime import date

import pytest
import requests

from collectors.base_collector import CollectionRequest, CollectorError
from collectors.threads_collector import ThreadsOfficialCollector


class FakeResponse:
    def __init__(self, payload, fail=False):
        self.payload = payload
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise requests.HTTPError("failure", response=self)

    def json(self):
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

    def fake_get(url, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
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
    assert captured["timeout"] == 12


def test_keyword_search_uses_only_supported_public_fields(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
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
