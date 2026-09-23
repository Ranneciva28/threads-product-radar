from pathlib import Path

from data.demo_data import generate_demo_posts
from database.db import Database
from exporters.excel_exporter import build_excel
from pipeline import process_posts
from scoring.opportunity_score import score_posts


def test_database_initialization_and_duplicate_handling(tmp_path: Path):
    db = Database(tmp_path / "radar.db")
    db.initialize()
    rows = process_posts(generate_demo_posts()[:3])
    assert db.insert_posts(rows) == 3
    assert db.insert_posts(rows) == 0
    assert db.count_posts() == 3


def test_excel_export_has_content():
    frame = score_posts(process_posts(generate_demo_posts()))
    payload = build_excel(frame)
    assert payload[:2] == b"PK"
    assert len(payload) > 5000

