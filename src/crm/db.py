"""SQLite connection and schema. Artifacts are JSON keyed by job_id (== lead.id)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL,
    url_canonical TEXT NOT NULL, content_hash TEXT, title TEXT, company TEXT,
    discovered_at TEXT, raw_snippet TEXT, status TEXT NOT NULL, data TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_canonical ON leads(url_canonical);
CREATE INDEX IF NOT EXISTS idx_leads_hash ON leads(content_hash);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS fit (job_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tailored (job_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS drafts (job_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, job_id TEXT NOT NULL, data TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY, job_id TEXT NOT NULL, outcome TEXT NOT NULL, ts TEXT
);
CREATE INDEX IF NOT EXISTS idx_outcomes_job ON outcomes(job_id);

CREATE TABLE IF NOT EXISTS audit (
    id TEXT PRIMARY KEY, ts TEXT, action TEXT, job_id TEXT, model TEXT,
    cost_usd REAL, input_summary TEXT, output_summary TEXT
);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)",
                 (str(SCHEMA_VERSION),))
    conn.commit()
