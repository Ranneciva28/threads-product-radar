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

