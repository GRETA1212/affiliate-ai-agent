from __future__ import annotations

import sqlite3
import uuid
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
    click_id TEXT UNIQUE,
    affiliate_link_id INTEGER NOT NULL REFERENCES affiliate_links(id),
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    referrer TEXT,
    visitor_key TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT
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
            columns = {row[1] for row in con.execute("PRAGMA table_info(clicks)")}
            migrations = {
                "click_id": "ALTER TABLE clicks ADD COLUMN click_id TEXT",
                "utm_source": "ALTER TABLE clicks ADD COLUMN utm_source TEXT",
                "utm_medium": "ALTER TABLE clicks ADD COLUMN utm_medium TEXT",
                "utm_campaign": "ALTER TABLE clicks ADD COLUMN utm_campaign TEXT",
                "utm_content": "ALTER TABLE clicks ADD COLUMN utm_content TEXT",
            }
            for column, sql in migrations.items():
                if column not in columns:
                    con.execute(sql)
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clicks_click_id ON clicks(click_id)")

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

    def get_program(self, slug: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM affiliate_programs WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None

    def create_campaign(self, program_slug: str, name: str, channel: str, status: str = "active") -> int:
        with self.connect() as con:
            cur = con.execute(
                "INSERT INTO campaigns (program_slug, name, channel, status) VALUES (?, ?, ?, ?)",
                (program_slug, name, channel, status),
            )
            return int(cur.lastrowid)

    def list_campaigns(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def ensure_affiliate_link(self, program_slug: str, destination_url: str, campaign_id: int | None = None) -> dict:
        tracking_code = f"{program_slug}:{campaign_id or 0}"
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM affiliate_links WHERE tracking_code = ?", (tracking_code,)
            ).fetchone()
            if row:
                return dict(row)
            cur = con.execute(
                "INSERT INTO affiliate_links (program_slug, campaign_id, destination_url, tracking_code) VALUES (?, ?, ?, ?)",
                (program_slug, campaign_id, destination_url, tracking_code),
            )
            link_id = int(cur.lastrowid)
            row = con.execute("SELECT * FROM affiliate_links WHERE id = ?", (link_id,)).fetchone()
            return dict(row)

    def record_click(
        self,
        affiliate_link_id: int,
        *,
        referrer: str | None = None,
        visitor_key: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
    ) -> str:
        click_id = uuid.uuid4().hex
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO clicks (
                    click_id, affiliate_link_id, referrer, visitor_key,
                    utm_source, utm_medium, utm_campaign, utm_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    click_id,
                    affiliate_link_id,
                    referrer,
                    visitor_key,
                    utm_source,
                    utm_medium,
                    utm_campaign,
                    utm_content,
                ),
            )
        return click_id

    def recent_clicks(self, limit: int = 20) -> list[dict]:
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT c.*, l.program_slug, l.campaign_id
                FROM clicks c
                JOIN affiliate_links l ON l.id = c.affiliate_link_id
                ORDER BY c.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def analytics_summary(self) -> dict:
        with self.connect() as con:
            clicks = con.execute("SELECT COUNT(*) FROM clicks").fetchone()[0]
            conversions = con.execute("SELECT COUNT(*) FROM conversions").fetchone()[0]
            revenue = con.execute("SELECT COALESCE(SUM(amount), 0) FROM commissions").fetchone()[0]
            impressions = con.execute("SELECT COALESCE(SUM(impressions), 0) FROM daily_metrics").fetchone()[0]
        epc = revenue / clicks if clicks else 0.0
        conversion_rate = conversions / clicks if clicks else 0.0
        ctr = clicks / impressions if impressions else 0.0
        rpm = (revenue / impressions * 1000.0) if impressions else 0.0
        return {
            "impressions": int(impressions),
            "clicks": int(clicks),
            "conversions": int(conversions),
            "revenue": float(revenue),
            "ctr": ctr,
            "conversion_rate": conversion_rate,
            "epc": epc,
            "rpm": rpm,
        }

    def analytics_offers(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT
                    p.slug,
                    p.name,
                    COUNT(DISTINCT c.id) AS clicks,
                    COUNT(DISTINCT v.id) AS conversions,
                    COALESCE(SUM(DISTINCT cm.amount), 0) AS revenue
                FROM affiliate_programs p
                LEFT JOIN affiliate_links l ON l.program_slug = p.slug
                LEFT JOIN clicks c ON c.affiliate_link_id = l.id
                LEFT JOIN conversions v ON v.affiliate_link_id = l.id
                LEFT JOIN commissions cm ON cm.conversion_id = v.id
                GROUP BY p.slug, p.name
                ORDER BY revenue DESC, clicks DESC
                """
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["epc"] = item["revenue"] / item["clicks"] if item["clicks"] else 0.0
            item["conversion_rate"] = item["conversions"] / item["clicks"] if item["clicks"] else 0.0
            result.append(item)
        return result
