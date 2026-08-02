"""HOS-4C Database Schema — SQLite"""

import sqlite3, os
from contextlib import contextmanager
from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'AWAITING_AMJAD',
    version INTEGER NOT NULL DEFAULT 1,
    owner TEXT NOT NULL DEFAULT 'amjad',
    project TEXT NOT NULL DEFAULT 'hermes-os',
    decision_text TEXT,
    reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    session_id TEXT,
    previous_state TEXT NOT NULL,
    resulting_state TEXT NOT NULL,
    rationale TEXT,
    reason_code TEXT,
    decision_version INTEGER NOT NULL,
    expected_version INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_timestamp TEXT NOT NULL,
    confirmation_timestamp TEXT,
    execution_timestamp TEXT NOT NULL,
    result TEXT NOT NULL,
    failure_reason TEXT,
    correlation_id TEXT,
    client_context TEXT,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_events(decision_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_idempotency ON audit_events(idempotency_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_hash ON audit_events(event_hash);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL DEFAULT 'AMJAD_OWNER',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    action TEXT NOT NULL,
    result TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""

def init_db(path: str = DATABASE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

@contextmanager
def get_db(path: str = DATABASE_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()