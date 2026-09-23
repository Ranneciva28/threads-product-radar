from __future__ import annotations

from typing import Iterable

from processors.buying_intent import add_buying_intent
from processors.classifier import classify_posts
from processors.cleaner import clean_posts


def process_posts(rows: Iterable[dict]) -> list[dict]:
    cleaned = clean_posts(rows)
    classified = classify_posts(cleaned)
    return add_buying_intent(classified)

