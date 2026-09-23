from __future__ import annotations

from typing import Any


CATEGORY_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("Finance Spreadsheet", ("budget planner", "financial planner", "cashflow", "keuangan"), "Personal finance"),
    ("Google Sheets Template", ("google sheets", "g-sheet", "gsheet"), "Spreadsheet"),
    ("Excel Template", ("template excel", "excel template", "dashboard excel"), "Spreadsheet"),
    ("Notion Template", ("notion template", "template notion"), "Productivity"),
    ("Canva Template", ("canva template", "template canva"), "Design"),
    ("AI Prompt / Prompt Pack", ("prompt ai", "ai prompt", "prompt pack", "chatgpt prompt"), "AI"),
    ("CV / Resume Template", ("cv template", "resume template", "template cv", "ats cv"), "Career"),
    ("Digital Planner", ("digital planner", "planner digital"), "Planning"),
    ("Education Worksheet", ("worksheet", "lembar kerja", "printable anak"), "Education"),
    ("Mini Course", ("mini course", "mini class", "kelas mini"), "Education"),
    ("Online Course", ("online course", "kelas online", "kursus online"), "Education"),
    ("Social Media Template", ("content calendar", "template instagram", "social media template"), "Marketing"),
    ("Marketing Template", ("marketing template", "sales funnel", "ads template"), "Marketing"),
    ("Business Template", ("business plan", "invoice template", "sop template"), "Business"),
    ("Productivity Template", ("habit tracker", "productivity template", "to-do template"), "Productivity"),
    ("Design Asset", ("preset", "lightroom", "design asset", "mockup", "font bundle"), "Design"),
    ("Ebook", ("ebook", "e-book", "buku digital"), "Publishing"),
]


def classify_post(text: str) -> dict[str, Any]:
    lower = (text or "").lower()
    matches: list[tuple[str, str, int]] = []
    for category, keywords, subcategory in CATEGORY_RULES:
        count = sum(keyword in lower for keyword in keywords)
        if count:
            matches.append((category, subcategory, count))
    if not matches:
        return {
            "product_category": "Other Digital Product",
            "product_subcategory": "Other",
            "classification_confidence": 0.45,
        }
    category, subcategory, count = max(matches, key=lambda item: item[2])
    return {
        "product_category": category,
        "product_subcategory": subcategory,
        "classification_confidence": min(0.62 + (count * 0.12), 0.98),
    }


def classify_posts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        row.update(classify_post(row.get("post_text", "")))
    return rows

