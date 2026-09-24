from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable


DIGITAL_TERMS = {
    "template", "spreadsheet", "excel", "google sheets", "notion", "canva",
    "ebook", "e-book", "prompt", "planner", "worksheet", "cv", "resume",
    "course", "kelas online", "preset", "dashboard", "digital product",
}
SPAM_TERMS = {"follow for follow", "follback", "slot gacor", "judi online"}
ENGAGEMENT_FIELDS = ("like_count", "reply_count", "repost_count", "quote_count")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def detect_language(text: str) -> str:
    lower = text.lower()
    id_markers = {"yang", "dan", "untuk", "dengan", "ini", "bisa", "gue", "kamu"}
    en_markers = {"the", "and", "for", "with", "this", "your", "how"}
    id_score = sum(bool(re.search(rf"\b{re.escape(w)}\b", lower)) for w in id_markers)
    en_score = sum(bool(re.search(rf"\b{re.escape(w)}\b", lower)) for w in en_markers)
    return "id" if id_score >= en_score else "en"


def is_probable_spam(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in SPAM_TERMS) or lower.count("http") > 3


def mentions_digital_product(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in DIGITAL_TERMS)


def clean_posts(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_links: set[str] = set()
    seen_texts: list[str] = []

    for raw in rows:
        row = dict(raw)
        text = normalize_text(row.get("post_text"))
        post_id = normalize_text(row.get("post_id"))
        permalink = normalize_text(row.get("permalink"))
        if not text or is_probable_spam(text):
            continue
        if post_id and post_id in seen_ids:
            continue
        if permalink and permalink in seen_links:
            continue
        lower = text.lower()
        if any(SequenceMatcher(None, lower, previous).ratio() >= 0.94 for previous in seen_texts):
            continue

        row["post_id"] = post_id or None
        row["permalink"] = permalink or None
        row["post_text"] = text
        row["post_text_normalized"] = lower
        row["language"] = row.get("language") or detect_language(text)
        row["is_digital_product"] = int(mentions_digital_product(text))

        explicit_availability = row.get("engagement_available")
        if explicit_availability is None:
            engagement_available = any(
                row.get(field) not in (None, "") for field in ENGAGEMENT_FIELDS
            )
        else:
            engagement_available = bool(explicit_availability)
        row["engagement_available"] = int(engagement_available)

        for field in ENGAGEMENT_FIELDS:
            value = row.get(field)
            if value in (None, ""):
                row[field] = 0
                continue
            try:
                row[field] = max(int(value), 0)
            except (TypeError, ValueError):
                row[field] = 0

        cleaned.append(row)
        if post_id:
            seen_ids.add(post_id)
        if permalink:
            seen_links.add(permalink)
        seen_texts.append(lower)
    return cleaned
