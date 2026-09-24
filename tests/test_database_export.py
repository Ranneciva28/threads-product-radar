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


def test_app_settings_are_seeded_and_updated(tmp_path: Path):
    db = Database(tmp_path / "radar.db")
    db.initialize()
    db.seed_app_settings(
        {"threads_access_token": "old-token", "max_posts": "250"},
        {"threads_access_token"},
    )
    db.seed_app_settings({"threads_access_token": "must-not-overwrite"})
    db.save_app_settings(
        {"threads_access_token": "new-token", "max_posts": "100"},
        {"threads_access_token"},
    )

    assert db.get_app_settings() == {
        "max_posts": "100",
        "threads_access_token": "new-token",
    }


def test_excel_export_has_content():
    frame = score_posts(process_posts(generate_demo_posts()))
    payload = build_excel(frame)
    assert payload[:2] == b"PK"
    assert len(payload) > 5000


def test_existing_database_is_migrated_with_market_research_columns(tmp_path: Path):
    import sqlite3

    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            post_text TEXT NOT NULL,
            created_at TEXT,
            product_category TEXT,
            keyword_source TEXT
        )"""
    )
    connection.commit()
    connection.close()

    db = Database(path)
    db.initialize()
    with db.connect() as connection:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(posts)").fetchall()
        }

    assert "intent_type" in columns
    assert "engagement_available" in columns
    assert "has_replies" in columns


def test_superadmin_and_managed_user_lifecycle(tmp_path: Path):
    from auth.password_auth import hash_password, verify_password

    db = Database(tmp_path / "users.db")
    db.initialize()

    admin_hash = hash_password("super-secret-password")
    db.ensure_superadmin("owner", admin_hash, "Owner")
    admin = db.get_user("OWNER")
    assert admin is not None
    assert admin["role"] == "SUPERADMIN"
    assert admin["active"] == 1
    assert verify_password("super-secret-password", admin["password_hash"])

    user_hash = hash_password("analyst-password")
    db.create_user("analyst01", user_hash, "Analyst")
    user = db.get_user("ANALYST01")
    assert user is not None
    assert user["role"] == "USER"
    assert user["active"] == 1

    db.set_user_active("analyst01", False)
    assert db.get_user("analyst01")["active"] == 0

    new_hash = hash_password("new-analyst-password")
    db.reset_user_password("analyst01", new_hash)
    assert verify_password(
        "new-analyst-password",
        db.get_user("analyst01")["password_hash"],
    )

    db.set_user_active("owner", False)
    assert db.get_user("owner")["active"] == 1
