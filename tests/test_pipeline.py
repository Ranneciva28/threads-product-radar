from datetime import date, datetime, timezone

import pandas as pd

from analytics.filters import filter_posts
from data.demo_data import generate_demo_posts
from pipeline import process_posts
from processors.buying_intent import detect_buying_intent
from processors.classifier import classify_post
from scoring.opportunity_score import score_posts


def test_classifier_and_intent():
    result = classify_post("Dashboard template Excel untuk cashflow UMKM")
    assert result["product_category"] in {"Finance Spreadsheet", "Excel Template"}
    intent = detect_buying_intent(["link dong", "bagus banget", "berapa harganya?"])
    assert intent["buying_intent_count"] == 2
    assert intent["buying_intent_status"] == "AVAILABLE"


def test_buying_intent_is_not_fabricated():
    intent = detect_buying_intent(None)
    assert intent["buying_intent_score"] is None
    assert intent["buying_intent_status"] == "UNAVAILABLE"


def test_missing_engagement_and_duplicate_are_safe():
    rows = [
        {"post_id": "1", "post_text": "template notion untuk kerja", "like_count": None},
        {"post_id": "1", "post_text": "template notion untuk kerja", "like_count": 5},
    ]
    processed = process_posts(rows)
    assert len(processed) == 1
    scored = score_posts(processed)
    assert int(scored.iloc[0]["total_engagement"]) == 0
    assert 0 <= scored.iloc[0]["opportunity_score"] <= 100


def test_filter_posts():
    scored = score_posts(process_posts(generate_demo_posts()))
    category = scored.iloc[0]["product_category"]
    filtered = filter_posts(
        scored,
        start_date=date.today().replace(day=1),
        end_date=date.today(),
        categories=[category],
        minimum_engagement=1,
    )
    assert not filtered.empty
    assert filtered["product_category"].eq(category).all()
    assert filtered["total_engagement"].ge(1).all()

