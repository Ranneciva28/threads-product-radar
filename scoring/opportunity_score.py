from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd


WEIGHTS = {
    "engagement": 0.30,
    "buying_intent": 0.25,
    "recency_growth": 0.20,
    "demand_frequency": 0.15,
    "competition_gap": 0.10,
}


def _minmax(series: pd.Series, neutral: float = 50.0) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return pd.Series(neutral, index=series.index, dtype=float)
    low, high = valid.min(), valid.max()
    if high == low:
        return pd.Series(neutral, index=series.index, dtype=float)
    return ((values.fillna(low) - low) / (high - low) * 100).clip(0, 100)


def score_posts(rows: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(list(rows))
    if df.empty:
        return df
    for field in ("like_count", "reply_count", "repost_count", "quote_count"):
        df[field] = pd.to_numeric(df.get(field, 0), errors="coerce").fillna(0).clip(lower=0)
    df["total_engagement"] = (
        df["like_count"] + df["reply_count"] + df["repost_count"] + df["quote_count"]
    )
    df["weighted_engagement"] = (
        df["like_count"] + 2 * df["reply_count"] + 3 * df["repost_count"] + 3 * df["quote_count"]
    )
    df["engagement_component"] = _minmax(df["weighted_engagement"])

    intent = pd.to_numeric(df.get("buying_intent_score"), errors="coerce")
    df["buying_intent_component"] = intent.fillna(0).clip(0, 100)

    created_source = df["created_at"] if "created_at" in df else pd.Series(pd.NaT, index=df.index)
    created = pd.to_datetime(created_source, errors="coerce", utc=True)
    now = pd.Timestamp(datetime.now(timezone.utc))
    age_days = (now - created).dt.total_seconds().div(86400).clip(lower=0)
    df["recency_growth_component"] = (100 * (0.5 ** (age_days.fillna(365) / 30))).clip(0, 100)

    category = df.get("product_category", pd.Series("Other Digital Product", index=df.index))
    cat_posts = category.map(category.value_counts()).astype(float)
    df["demand_frequency_component"] = _minmax(cat_posts)

    creator = df.get("username", pd.Series("unknown", index=df.index)).fillna("unknown")
    creator_counts = pd.DataFrame({"category": category, "creator": creator}).groupby("category")["creator"].nunique()
    creators = category.map(creator_counts).replace(0, 1)
    demand_per_creator = cat_posts / creators
    df["competition_gap_component"] = _minmax(demand_per_creator)

    df["opportunity_score"] = sum(
        df[column] * weight
        for column, weight in [
            ("engagement_component", WEIGHTS["engagement"]),
            ("buying_intent_component", WEIGHTS["buying_intent"]),
            ("recency_growth_component", WEIGHTS["recency_growth"]),
            ("demand_frequency_component", WEIGHTS["demand_frequency"]),
            ("competition_gap_component", WEIGHTS["competition_gap"]),
        ]
    ).round(2)
    return df
