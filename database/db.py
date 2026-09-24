from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from config.settings import settings
from database.schema import SCHEMA_SQL


POST_COLUMNS = [
    "post_id", "username", "display_name", "post_text", "post_text_normalized",
    "created_at", "permalink", "like_count", "reply_count", "repost_count",
    "quote_count", "views", "engagement_available", "media_type", "shortcode",
    "is_quote_post", "has_replies", "topic_tag", "is_verified",
    "profile_picture_url", "keyword_source", "search_type", "language",
    "crawl_timestamp", "data_source", "is_digital_product", "product_category",
    "product_subcategory", "classification_confidence", "intent_type",
    "intent_score", "intent_source", "intent_signals", "buying_intent_count",
    "buying_intent_score", "buying_intent_status", "buying_intent_examples",
]

POST_MIGRATION_COLUMNS = {
    "engagement_available": "INTEGER",
    "media_type": "TEXT",
    "shortcode": "TEXT",
    "is_quote_post": "INTEGER",
    "has_replies": "INTEGER",
    "topic_tag": "TEXT",
    "is_verified": "INTEGER",
    "profile_picture_url": "TEXT",
    "intent_type": "TEXT",
    "intent_score": "REAL",
    "intent_source": "TEXT",
    "intent_signals": "TEXT",
}


class Database:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or settings.database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            existing = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(posts)").fetchall()
            }
            for column, ddl in POST_MIGRATION_COLUMNS.items():
                if column not in existing:
                    connection.execute(f"ALTER TABLE posts ADD COLUMN {column} {ddl}")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_posts_intent_type ON posts(intent_type)"
            )
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def ensure_superadmin(
        self, username: str, password_hash: str, display_name: str | None = None
    ) -> None:
        username = username.strip()
        if not username:
            return
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO users
                (username, display_name, password_hash, role, active, updated_at)
                VALUES (?, ?, ?, 'SUPERADMIN', 1, CURRENT_TIMESTAMP)
                ON CONFLICT(username) DO UPDATE SET
                    display_name=COALESCE(excluded.display_name, users.display_name),
                    password_hash=excluded.password_hash,
                    role='SUPERADMIN',
                    active=1,
                    updated_at=CURRENT_TIMESTAMP""",
                (username, display_name, password_hash),
            )

    def get_user(self, username: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT id, username, display_name, password_hash, role, active,
                          created_at, updated_at, last_login_at
                   FROM users
                   WHERE username = ? COLLATE NOCASE""",
                (username.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, username, display_name, role, active,
                          created_at, updated_at, last_login_at
                   FROM users
                   ORDER BY CASE role WHEN 'SUPERADMIN' THEN 0 ELSE 1 END,
                            username COLLATE NOCASE"""
            ).fetchall()
        return [dict(row) for row in rows]

    def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str | None = None,
        role: str = "USER",
    ) -> None:
        username = username.strip()
        role = role.strip().upper()
        if not username:
            raise ValueError("Username wajib diisi.")
        if role not in {"SUPERADMIN", "USER"}:
            raise ValueError("Role tidak valid.")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO users
                (username, display_name, password_hash, role, active)
                VALUES (?, ?, ?, ?, 1)""",
                (username, (display_name or "").strip() or None, password_hash, role),
            )

    def set_user_active(self, username: str, active: bool) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE users
                   SET active = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE username = ? COLLATE NOCASE AND role != 'SUPERADMIN'""",
                (int(active), username.strip()),
            )

    def reset_user_password(self, username: str, password_hash: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE users
                   SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE username = ? COLLATE NOCASE AND role != 'SUPERADMIN'""",
                (password_hash, username.strip()),
            )

    def mark_user_login(self, username: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE users
                   SET last_login_at = CURRENT_TIMESTAMP
                   WHERE username = ? COLLATE NOCASE""",
                (username.strip(),),
            )

    def seed_app_settings(
        self, values: dict[str, str], secret_keys: set[str] | None = None
    ) -> None:
        secret_keys = secret_keys or set()
        with self.connect() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO app_settings(key, value, is_secret) VALUES (?, ?, ?)",
                [
                    (key, str(value), int(key in secret_keys))
                    for key, value in values.items()
                ],
            )

    def get_app_settings(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM app_settings ORDER BY key"
            ).fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def save_app_settings(
        self, values: dict[str, str], secret_keys: set[str] | None = None
    ) -> None:
        secret_keys = secret_keys or set()
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO app_settings(key, value, is_secret, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    is_secret=excluded.is_secret,
                    updated_at=CURRENT_TIMESTAMP""",
                [
                    (key, str(value), int(key in secret_keys))
                    for key, value in values.items()
                ],
            )

    def insert_posts(self, rows: Iterable[dict]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        placeholders = ",".join("?" for _ in POST_COLUMNS)
        columns = ",".join(POST_COLUMNS)
        before = self.count_posts()
        with self.connect() as connection:
            connection.executemany(
                f"INSERT OR IGNORE INTO posts ({columns}) VALUES ({placeholders})",
                [tuple(row.get(column) for column in POST_COLUMNS) for row in rows],
            )
        return self.count_posts() - before

    def count_posts(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0])

    def get_posts(self, data_source: str | None = None) -> list[dict]:
        query = "SELECT * FROM posts"
        params: tuple = ()
        if data_source:
            query += " WHERE data_source = ?"
            params = (data_source,)
        query += " ORDER BY created_at DESC"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def add_keyword(self, keyword: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO keywords(keyword) VALUES (?) ON CONFLICT(keyword) DO UPDATE SET active=1",
                (keyword.strip().lower(),),
            )

    def get_keywords(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT keyword FROM keywords WHERE active=1 ORDER BY keyword"
            ).fetchall()
        return [row[0] for row in rows]

    def log_search_run(
        self, keyword: str, search_type: str, start_date: str, end_date: str,
        status: str, post_count: int = 0, error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO search_runs
                (keyword, search_type, start_date, end_date, started_at, completed_at,
                 status, post_count, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (keyword, search_type, start_date, end_date, now, now, status, post_count, error_message),
            )

    def status(self) -> dict:
        with self.connect() as connection:
            post_count = connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            last_crawl = connection.execute("SELECT MAX(crawl_timestamp) FROM posts").fetchone()[0]
            last_run = connection.execute("SELECT MAX(completed_at) FROM search_runs").fetchone()[0]
        return {
            "path": str(self.path),
            "post_count": int(post_count),
            "last_collection": last_run or last_crawl,
        }

    def dataframe(self, data_source: str | None = None) -> pd.DataFrame:
        return pd.DataFrame(self.get_posts(data_source=data_source))
