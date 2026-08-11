import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT '',
    problem TEXT NOT NULL DEFAULT '',
    affiliate_url TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'archived')),
    source TEXT,
    opportunity_score REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    occurred_at TEXT NOT NULL,
    source TEXT,
    medium TEXT,
    content TEXT,
    referrer TEXT,
    user_agent TEXT,
    is_bot INTEGER NOT NULL DEFAULT 0 CHECK (is_bot IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_clicks_campaign_time
    ON clicks(campaign_id, occurred_at);

CREATE TABLE IF NOT EXISTS conversions (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    occurred_at TEXT NOT NULL,
    network TEXT,
    external_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'reversed')),
    sale_amount REAL,
    commission_amount REAL NOT NULL,
    currency TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversions_campaign_time
    ON conversions(campaign_id, occurred_at);

DROP INDEX IF EXISTS idx_conversions_network_external;
CREATE UNIQUE INDEX idx_conversions_network_external
    ON conversions(network, external_id);

CREATE TABLE IF NOT EXISTS campaign_bindings (
    campaign_id TEXT PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
    network TEXT NOT NULL CHECK (network IN ('cj', 'impact')),
    program_id TEXT,
    attribution_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_bindings_network_token
    ON campaign_bindings(network, attribution_token);

CREATE INDEX IF NOT EXISTS idx_campaign_bindings_network_program
    ON campaign_bindings(network, program_id);

CREATE TABLE IF NOT EXISTS network_events (
    id TEXT PRIMARY KEY,
    network TEXT NOT NULL CHECK (network IN ('cj', 'impact')),
    external_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    program_id TEXT,
    advertiser_name TEXT,
    network_status TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'reversed')),
    sale_amount REAL,
    commission_amount REAL NOT NULL,
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    order_id TEXT,
    attribution_token TEXT,
    campaign_id TEXT REFERENCES campaigns(id) ON DELETE SET NULL,
    payload_json TEXT,
    synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_network_events_network_external
    ON network_events(network, external_id);

CREATE INDEX IF NOT EXISTS idx_network_events_group
    ON network_events(network, group_id);

CREATE INDEX IF NOT EXISTS idx_network_events_campaign
    ON network_events(campaign_id, occurred_at);

CREATE TABLE IF NOT EXISTS sync_state (
    network TEXT PRIMARY KEY CHECK (network IN ('cj', 'impact')),
    last_success_at TEXT,
    last_cursor TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
"""


def database_path() -> Path:
    configured = os.getenv("AFFILIATE_DB_PATH", "data/affiliate.db").strip()
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(SCHEMA)
    return connection
