from __future__ import annotations

import re

import pandas as pd


HOOK_PATTERNS = [
    ("Problem", ("capek", "masih", "sulit", "sepi", "kesalahan", "gagal")),
    ("Story", ("gue bikin", "gue pakai", "pertama gue", "setelah")),
    ("Curiosity", ("akhirnya", "ternyata", "rahasia", "yang jarang")),
    ("Educational", ("belajar", "panduan", "cara", "tips")),
    ("Income", ("gaji", "omzet", "penghasilan", "cuan")),
    ("Fear", ("jangan", "bahaya", "sebelum terlambat")),
    ("Transformation", ("dari nol", "jadi", "berubah", "sebelum")),
    ("Controversial", ("bukan", "stop", "salah besar")),
    ("How-to", ("cara", "tinggal", "langkah")),
]


def category_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["buying_intent_count"] = pd.to_numeric(work.get("buying_intent_count"), errors="coerce")
    ranking = work.groupby("product_category", dropna=False).agg(
        post_count=("post_id", "count"),
        total_engagement=("total_engagement", "sum"),
        average_engagement=("total_engagement", "mean"),
        median_engagement=("total_engagement", "median"),
        buying_intent=("buying_intent_count", "sum"),
        creator_count=("username", "nunique"),
        opportunity_score=("opportunity_score", "mean"),
    ).reset_index()
    ranking["competition"] = ranking["creator_count"].apply(
        lambda value: "Low" if value <= 2 else "Medium" if value <= 5 else "High"
    )
    ranking = ranking.sort_values("opportunity_score", ascending=False).reset_index(drop=True)
    ranking.insert(0, "rank", ranking.index + 1)
    return ranking


def keyword_analytics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.groupby("keyword_source", dropna=False).agg(
        post_count=("post_id", "count"),
        total_engagement=("total_engagement", "sum"),
        average_engagement=("total_engagement", "mean"),
        opportunity_score=("opportunity_score", "mean"),
    ).reset_index().sort_values("opportunity_score", ascending=False)
    return out


def creator_analytics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby("username", dropna=False)
    out = grouped.agg(
        post_count=("post_id", "count"),
        total_engagement=("total_engagement", "sum"),
        average_engagement=("total_engagement", "mean"),
    ).reset_index()
    top_category = grouped["product_category"].agg(
        lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"
    ).reset_index(name="top_product_category")
    return out.merge(top_category, on="username").sort_values("total_engagement", ascending=False)


def hook_analytics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.nlargest(min(50, len(df)), "total_engagement").iterrows():
        text = str(row.get("post_text", ""))
        hook = re.split(r"(?<=[.!?])\s+|\n", text, maxsplit=1)[0][:220]
        lower = hook.lower()
        pattern = "Other"
        for name, markers in HOOK_PATTERNS:
            if any(marker in lower for marker in markers):
                pattern = name
                break
        rows.append({
            "hook_pattern": pattern,
            "hook": hook,
            "category": row.get("product_category"),
            "engagement": row.get("total_engagement", 0),
            "creator": row.get("username"),
        })
    return pd.DataFrame(rows).sort_values("engagement", ascending=False)


def cta_pattern(text: str) -> str:
    lower = (text or "").lower()
    for label, terms in {
        "Link / Bio": ("link", "bio"),
        "Comment keyword": ("komen", "comment", "ketik"),
        "Direct message": ("dm", "chat"),
        "Purchase": ("beli", "checkout", "order"),
    }.items():
        if any(term in lower for term in terms):
            return label
    return "No explicit CTA"

