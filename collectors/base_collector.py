from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class CollectionRequest:
    keyword: str
    start_date: date
    end_date: date
    search_type: str = "RECENT"
    limit: int = 100
    language: str = "id"


class CollectorError(RuntimeError):
    """Safe collector error suitable for showing in the dashboard."""


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, request: CollectionRequest) -> list[dict[str, Any]]:
        raise NotImplementedError

