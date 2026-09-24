from __future__ import annotations

import re
from typing import Any


INTENT_PATTERNS = [
    "link dong", "dimana belinya", "beli dimana", "berapa harganya", "harga?",
    "mau", "tertarik", "spill", "info dong", "ada link", "checkout", "available",
    "template-nya dimana", "boleh minta link", "ada versi excel", "ada versi sheets",
    "cara beli", "purchase", "buy", "where can i buy", "how much",
]

# Ordered from strongest demand signal to more descriptive market signals.
MARKET_INTENT_RULES: list[tuple[str, tuple[str, ...], float]] = [
    (
        "PURCHASE_INTENT",
        (
            "mau beli", "pengen beli", "ingin beli", "cara beli", "beli dimana",
            "dimana belinya", "berapa harganya", "harga berapa", "checkout",
            "where can i buy", "how much", "want to buy", "purchase",
        ),
        92.0,
    ),
    (
        "PRODUCT_SEARCH",
        (
            "butuh", "lagi cari", "mencari", "ada yang punya", "ada template",
            "need a", "need an", "looking for", "anyone have", "where can i find",
        ),
        86.0,
    ),
    (
        "RECOMMENDATION_REQUEST",
        (
            "rekomendasi", "recommend", "recommendation", "suggest", "saran dong",
            "ada saran", "yang bagus apa", "bagus yang mana",
        ),
        82.0,
    ),
    (
        "CONSIDERATION",
        (
            "worth it", "mending", "pilih mana", "vs", "versus", "bandingin",
            "compare", "comparison", "lebih bagus", "better than",
        ),
        76.0,
    ),
    (
        "PAIN_POINT",
        (
            "capek", "ribet", "susah", "kesulitan", "manual", "repot", "gagal",
            "struggle", "pain", "problem", "too hard", "takes too long",
        ),
        72.0,
    ),
    (
        "SELLER_SUPPLY",
        (
            "jual", "dijual", "tersedia", "available now", "order sekarang",
            "promo", "diskon", "launch", "baru rilis", "for sale", "buy now",
            "produk saya", "template saya",
        ),
        68.0,
    ),
    (
        "POST_PURCHASE_VALIDATION",
        (
            "baru beli", "sudah beli", "udah beli", "puas", "ngebantu banget",
            "recommended", "works well", "worth every", "best purchase",
        ),
        70.0,
    ),
]


DEMAND_INTENTS = {
    "PURCHASE_INTENT",
    "PRODUCT_SEARCH",
    "RECOMMENDATION_REQUEST",
    "CONSIDERATION",
}


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _to_replies(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [part for part in value.split("||") if part.strip()]
    return None


def detect_buying_intent(replies_value: Any) -> dict[str, Any]:
    """Legacy reply-intent detector retained for compatibility and enrichment."""
    replies = _to_replies(replies_value)
    if replies is None:
        return {
            "buying_intent_count": None,
            "buying_intent_score": None,
            "buying_intent_status": "UNAVAILABLE",
            "buying_intent_examples": None,
        }
    matches = []
    for reply in replies:
        lower = _normalize(reply).lower()
        if any(pattern in lower for pattern in INTENT_PATTERNS):
            matches.append(reply.strip())
    score = (len(matches) / len(replies) * 100) if replies else 0.0
    return {
        "buying_intent_count": len(matches),
        "buying_intent_score": round(score, 2),
        "buying_intent_status": "AVAILABLE" if replies else "LIMITED_DATA",
        "buying_intent_examples": " || ".join(matches[:3]) or None,
    }


def detect_post_intent(text: Any) -> dict[str, Any]:
    normalized = _normalize(text)
    lower = normalized.lower()
    best_type = "NO_CLEAR_INTENT"
    best_score = 0.0
    best_matches: list[str] = []

    for intent_type, patterns, base_score in MARKET_INTENT_RULES:
        matches = [pattern for pattern in patterns if pattern in lower]
        if not matches:
            continue
        score = min(base_score + (len(matches) - 1) * 3.0, 99.0)
        if score > best_score:
            best_type = intent_type
            best_score = score
            best_matches = matches

    return {
        "intent_type": best_type,
        "intent_score": round(best_score, 2),
        "intent_source": "POST_TEXT",
        "intent_signals": " | ".join(best_matches[:5]) or None,
    }


def add_buying_intent(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add market intent from public post text, enriched by replies when available.

    Keyword search reliably provides post text, while public reply bodies may not
    be available for arbitrary posts. Therefore the primary signal comes from
    the public post itself and reply intent is treated as optional enrichment.
    """
    for row in rows:
        post_intent = detect_post_intent(row.get("post_text"))
        reply_intent = detect_buying_intent(row.get("replies_text"))

        row.update(post_intent)
        post_is_demand = post_intent["intent_type"] in DEMAND_INTENTS
        post_score = float(post_intent["intent_score"]) if post_is_demand else 0.0
        reply_score = reply_intent["buying_intent_score"]
        reply_count = reply_intent["buying_intent_count"]

        scores = [post_score]
        if reply_score is not None:
            scores.append(float(reply_score))
        combined_score = max(scores) if scores else 0.0
        if post_score > 0 and reply_score not in (None, 0):
            combined_score = min(100.0, combined_score + 5.0)

        count = (1 if post_is_demand else 0) + int(reply_count or 0)
        examples: list[str] = []
        if post_is_demand:
            excerpt = _normalize(row.get("post_text"))[:220]
            if excerpt:
                examples.append(excerpt)
        if reply_intent.get("buying_intent_examples"):
            examples.extend(
                part.strip()
                for part in str(reply_intent["buying_intent_examples"]).split("||")
                if part.strip()
            )

        if reply_intent["buying_intent_status"] in {"AVAILABLE", "LIMITED_DATA"}:
            status = "POST_AND_REPLIES" if post_is_demand else "REPLIES_CHECKED"
            source = "POST_AND_REPLIES"
        else:
            status = "POST_TEXT" if post_is_demand else "POST_TEXT_NO_BUY_SIGNAL"
            source = "POST_TEXT"

        row["intent_source"] = source
        row.update(
            {
                "buying_intent_count": count,
                "buying_intent_score": round(combined_score, 2),
                "buying_intent_status": status,
                "buying_intent_examples": " || ".join(examples[:3]) or None,
            }
        )
    return rows
