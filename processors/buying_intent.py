from __future__ import annotations

import re
from typing import Any


INTENT_PATTERNS = [
    "link dong", "dimana belinya", "beli dimana", "berapa harganya", "harga?",
    "mau", "tertarik", "spill", "info dong", "ada link", "checkout", "available",
    "template-nya dimana", "boleh minta link", "ada versi excel", "ada versi sheets",
    "cara beli", "purchase", "buy", "where can i buy", "how much",
]


def _to_replies(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [part for part in value.split("||") if part.strip()]
    return None


def detect_buying_intent(replies_value: Any) -> dict[str, Any]:
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
        lower = re.sub(r"\s+", " ", reply.lower()).strip()
        if any(pattern in lower for pattern in INTENT_PATTERNS):
            matches.append(reply.strip())
    score = (len(matches) / len(replies) * 100) if replies else 0.0
    return {
        "buying_intent_count": len(matches),
        "buying_intent_score": round(score, 2),
        "buying_intent_status": "AVAILABLE" if replies else "LIMITED_DATA",
        "buying_intent_examples": " || ".join(matches[:3]) or None,
    }


def add_buying_intent(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        row.update(detect_buying_intent(row.get("replies_text")))
    return rows

