from __future__ import annotations

from io import BytesIO

import pandas as pd

from analytics.product_analytics import category_ranking, creator_analytics, keyword_analytics


def _safe(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    for column in clean.select_dtypes(include=["datetimetz"]).columns:
        clean[column] = clean[column].dt.tz_localize(None)
    return clean


def build_excel(df: pd.DataFrame) -> bytes:
    ranking = category_ranking(df)
    keywords = keyword_analytics(df)
    creators = creator_analytics(df)
    top_threads = df.sort_values("opportunity_score", ascending=False).head(100)
    buying = df[[
        c for c in [
            "product_category", "intent_type", "intent_score", "intent_source",
            "intent_signals", "buying_intent_score", "buying_intent_count",
            "buying_intent_status", "buying_intent_examples", "post_text",
            "username", "permalink",
        ] if c in df
    ]]
    overview = pd.DataFrame({
        "Metric": ["Total Posts", "Digital Product Posts", "Product Categories", "Average Engagement"],
        "Value": [len(df), int(df.get("is_digital_product", pd.Series(dtype=int)).sum()),
                  int(df.get("product_category", pd.Series(dtype=str)).nunique()),
                  round(float(df.get("total_engagement", pd.Series([0])).mean()), 2)],
    })
    sheets = {
        "Overview": overview,
        "Product Ranking": ranking,
        "Top Threads": top_threads,
        "Keywords": keywords,
        "Creators": creators,
        "Market Intent": buying,
        "Raw Data": df,
    }
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            "bold": True, "font_color": "#FFFFFF", "bg_color": "#18181B",
            "border": 0, "align": "left", "valign": "vcenter",
        })
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        for sheet_name, frame in sheets.items():
            frame = _safe(frame)
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            if len(frame.columns):
                worksheet.autofilter(0, 0, max(len(frame), 1), len(frame.columns) - 1)
            worksheet.set_row(0, 24, header_format)
            for idx, column in enumerate(frame.columns):
                sample = frame[column].astype(str).head(100)
                width = min(max(len(str(column)) + 2, sample.map(len).max() + 2 if len(sample) else 12), 48)
                fmt = number_format if pd.api.types.is_numeric_dtype(frame[column]) else None
                worksheet.set_column(idx, idx, width, fmt)
    return output.getvalue()

