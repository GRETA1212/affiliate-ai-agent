from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

from .models import AffiliateProgram

SCHEMA = """
CREATE TABLE IF NOT EXISTS affiliate_programs (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    product_url TEXT NOT NULL,
    affiliate_url TEXT,
    commission_type TEXT NOT NULL,
    commission_rate_pct REAL,
    commission_amount REAL,
    recurring_months INTEGER,
    lifetime_recurring INTEGER NOT NULL,
    cookie_days INTEGER,
    monthly_price_from REAL,
    monthly_price_to REAL,
    niche_fit REAL NOT NULL,
    conversion_confidence REAL NOT NULL,
    competition_penalty REAL NOT NULL,
    approval_friction REAL NOT NULL,
    verification_status TEXT NOT NULL,
    source_url TEXT,
    source_checked_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunity_scores (
    slug TEXT PRIMARY KEY REFERENCES affiliate_programs(slug) ON DELETE CASCADE,
    total REAL NOT NULL,
    economics REAL NOT NULL,
    attribution REAL NOT NULL,
    fit REAL NOT NULL,
    conversion REAL NOT NULL,
    competition REAL NOT NULL,
    friction REAL NOT NULL,
    verification_multiplier REAL NOT NULL,
    scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_slug TEXT NOT NULL REFERENCES affiliate_programs(slug),
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    asset_type TEXT NOT NULL,
    title TEXT,
    url TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS affiliate_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_slug TEXT NOT NULL REFERENCES affiliate_programs(slug),
    campaign_id INTEGER REFERENCES campaigns(id),
    destination_url TEXT NOT NULL,
    tracking_code TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affiliate_link_id INTEGER NOT NULL REFERENCES affiliate_links(id),
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    referrer TEXT,
    visitor_key TEXT
);

CREATE TABLE IF NOT EXISTS conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affiliate_link_id INTEGER REFERENCES affiliate_links(id),
    external_conversion_id TEXT,
    conversion_type TEXT NOT NULL,
    revenue REAL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversion_id INTEGER REFERENCES conversions(id),
    program_slug TEXT NOT NULL REFERENCES affiliate_programs(slug),
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    status TEXT NOT NULL DEFAULT 'pending',
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    day TEXT NOT NULL,
    program_slug TEXT NOT NULL REFERENCES affiliate_programs(slug),
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    trials INTEGER NOT NULL DEFAULT 0,
    purchases INTEGER NOT NULL DEFAULT 0,
    commission REAL NOT NULL DEFAULT 0,
    PRIMARY KEY(day, program_slug)
);
"""


class Repository:
    def __init__(self, path: str | Path = "affiliate_intel.db") -> None:
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)

    def upsert_program(self, program: AffiliateProgram) -> None:
        program.validate()
        values = asdict(program)
        values["lifetime_recurring"] = int(program.lifetime_recurring)
        columns = list(values)
        placeholders = ", ".join(f":{c}" for c in columns)
        updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in {"slug", "created_at"})
        sql = f"""
        INSERT INTO affiliate_programs ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT(slug) DO UPDATE SET {updates}
        """
        with self.connect() as con:
            con.execute(sql, values)

    def list_programs(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM affiliate_programs ORDER BY name").fetchall()
        return [dict(row) for row in rows]
