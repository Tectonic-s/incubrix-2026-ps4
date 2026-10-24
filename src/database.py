"""SQLite Database layer with WAL mode and transaction support."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import settings
from src.logger import logger


def get_db_path() -> Path:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        path_str = db_url.replace("sqlite:///", "")
    else:
        path_str = "./incubrix_ps4.db"
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db():
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Initializes all database tables."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS destinations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            platform_key TEXT NOT NULL,
            surface TEXT NOT NULL DEFAULT 'topic',
            category TEXT NOT NULL DEFAULT 'general',
            audience_tags TEXT NOT NULL DEFAULT '[]',
            language TEXT NOT NULL DEFAULT 'en',
            geo TEXT NOT NULL DEFAULT 'global',
            est_audience INTEGER NOT NULL DEFAULT 1000,
            rules_url TEXT,
            frequency_cap TEXT NOT NULL DEFAULT '1/7d',
            self_promo_allowed INTEGER NOT NULL DEFAULT 1,
            link_policy TEXT NOT NULL DEFAULT 'allowed',
            disclosure_required INTEGER NOT NULL DEFAULT 0,
            automation_allowed INTEGER NOT NULL DEFAULT 1,
            connector_key TEXT NOT NULL,
            relevance_score INTEGER NOT NULL DEFAULT 3,
            relevance_reason TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT 'L0',
            last_certified_at TEXT,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(url, platform_key)
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            idempotency_key TEXT,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            result_json TEXT,
            error_json TEXT,
            callback_url TEXT,
            correlation_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key);

        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            destination_id TEXT NOT NULL,
            platform_post_id TEXT NOT NULL,
            idempotency_key TEXT,
            status TEXT NOT NULL,
            title TEXT,
            live_url TEXT,
            rendition_json TEXT NOT NULL,
            published_at TEXT NOT NULL,
            deleted_at TEXT,
            FOREIGN KEY (destination_id) REFERENCES destinations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_posts_dest ON posts(destination_id);
        CREATE INDEX IF NOT EXISTS idx_posts_idemp ON posts(idempotency_key);

        CREATE TABLE IF NOT EXISTS certifications (
            id TEXT PRIMARY KEY,
            destination_id TEXT NOT NULL,
            connector_key TEXT NOT NULL,
            status TEXT NOT NULL,
            test_post_id TEXT,
            live_url TEXT,
            evidence_json TEXT NOT NULL,
            certified_at TEXT NOT NULL,
            FOREIGN KEY (destination_id) REFERENCES destinations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cert_dest ON certifications(destination_id);

        CREATE TABLE IF NOT EXISTS recertification_alerts (
            id TEXT PRIMARY KEY,
            destination_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            FOREIGN KEY (destination_id) REFERENCES destinations(id)
        );

        CREATE TABLE IF NOT EXISTS rules_proposals (
            id TEXT PRIMARY KEY,
            community_url TEXT NOT NULL,
            proposed_rules_json TEXT NOT NULL,
            source_text TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            confirmed_rules_json TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT
        );
        """)
    logger.info("Database initialized successfully.")
