SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE,
    username TEXT,
    display_name TEXT,
    post_text TEXT NOT NULL,
    post_text_normalized TEXT,
    created_at TEXT,
    permalink TEXT UNIQUE,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    repost_count INTEGER DEFAULT 0,
    quote_count INTEGER DEFAULT 0,
    views INTEGER,
    keyword_source TEXT,
    search_type TEXT,
    language TEXT,
    crawl_timestamp TEXT,
    data_source TEXT NOT NULL DEFAULT 'THREADS_API',
    is_digital_product INTEGER NOT NULL DEFAULT 0,
    product_category TEXT,
    product_subcategory TEXT,
    classification_confidence REAL,
    buying_intent_count INTEGER,
    buying_intent_score REAL,
    buying_intent_status TEXT,
    buying_intent_examples TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(product_category);
CREATE INDEX IF NOT EXISTS idx_posts_keyword ON posts(keyword_source);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    search_type TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    post_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS product_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS creator_stats (
    username TEXT PRIMARY KEY,
    post_count INTEGER NOT NULL DEFAULT 0,
    total_engagement INTEGER NOT NULL DEFAULT 0,
    average_engagement REAL NOT NULL DEFAULT 0,
    top_product_category TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

