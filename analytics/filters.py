from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


def filter_posts(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    keywords: Iterable[str] | None = None,
    categories: Iterable[str] | None = None,
    minimum_engagement: int = 0,
    search_types: Iterable[str] | None = None,
    languages: Iterable[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    if "created_at_dt" not in work:
        work["created_at_dt"] = pd.to_datetime(work["created_at"], errors="coerce", utc=True)
    if start_date and end_date:
        work = work[work["created_at_dt"].dt.date.between(start_date, end_date, inclusive="both")]
    checks = [
        ("keyword_source", list(keywords or [])),
        ("product_category", list(categories or [])),
        ("search_type", list(search_types or [])),
        ("language", list(languages or [])),
    ]
    for column, values in checks:
        if values:
            work = work[work[column].isin(values)]
    return work[work["total_engagement"] >= minimum_engagement]

