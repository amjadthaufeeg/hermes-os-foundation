"""
HOS-4D.3: Authoritative Decision Adapter
SQLite operational store + append-only audit ledger.
Git projection is read-only, not authoritative.
ISOLATED_TEST_MODE only — no production writes authorized.
"""

import json, os, uuid, sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional

from backend.hos4c.database import get_db as _runtime_get_db
from backend.hos4c.state_machine import validate_transition, ROLE_PERMISSIONS
from backend.hos4c.environment import mutations_disabled


def _compute_hash(data: str) -> str:
    """SHA-256 hash for audit chain."""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()

AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", os.environ.get("DATABASE_PATH", ":memory:"))

@contextmanager
def get_auth_db():
    """Get authoritative database connection. Reads path from env at call time."""
    path = os.environ.get("AUTH_DB_PATH", os.environ.get("DATABASE_PATH", ":memory:"))
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_auth_db():
    """Create authoritative schema."""
    with get_auth_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS authoritative_decisions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                project TEXT NOT NULL, workflow_state TEXT NOT NULL,
                display_status TEXT, owner TEXT NOT NULL DEFAULT 'amjad',
                risk TEXT DEFAULT 'NOT_ASSESSED', recommendation TEXT,
                requested_action TEXT, rationale TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                due_at TEXT, version INTEGER NOT NULL DEFAULT 1,
                source_origin TEXT DEFAULT 'LEGACY_IMPORT',
                source_reference TEXT, evidence_ids TEXT,
                last_action TEXT, last_actor_id TEXT,
                last_audit_event_id TEXT,
                export_status TEXT DEFAULT 'NOT_EXPORTED',
                export_version INTEGER DEFAULT 0, archived_at TEXT
            );
            CREATE TABLE IF NOT EXISTS migration_history (
                migration_id TEXT PRIMARY KEY, checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL, status TEXT DEFAULT 'APPLIED'
            );
            CREATE TABLE IF NOT EXISTS projection_status (
                decision_id TEXT PRIMARY KEY, export_version INTEGER,
                last_exported_at TEXT, status TEXT, error TEXT
            );
            CREATE TABLE IF NOT EXISTS idempotency_records (
                key TEXT PRIMARY KEY, result TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
                decision_id TEXT, action TEXT, actor_id TEXT,
                actor_role TEXT, previous_state TEXT, resulting_state TEXT,
                decision_version INTEGER, idempotency_key TEXT,
                event_hash TEXT, prev_hash TEXT, result TEXT,
                rationale TEXT, created_at TEXT NOT NULL
            );
        """)
        db.commit()

def get_decision(decision_id: str) -> Optional[dict]:
    with get_auth_db() as db:
        row = db.execute("SELECT * FROM authoritative_decisions WHERE id = ?",
                        (decision_id,)).fetchone()
        return dict(row) if row else None

def list_decisions(filters: dict = None) -> list:
    with get_auth_db() as db:
        q = "SELECT * FROM authoritative_decisions WHERE archived_at IS NULL"
        params = []
        if filters:
            if 'state' in filters:
                q += " AND workflow_state = ?"
                params.append(filters['state'])
            if 'project' in filters:
                q += " AND project = ?"
                params.append(filters['project'])
        q += " ORDER BY updated_at DESC"
        return [dict(r) for r in db.execute(q, params).fetchall()]

# --- Mutation ---
class TransitionError(Exception):
    def __init__(self, reason: str, code: str = "TRANSITION_FAILED"):
        self.reason = reason
        self.code = code

def apply_transition(decision_id: str, action: str, expected_state: str,
                    expected_version: int, actor_id: str, actor_role: str,
                    rationale: str, idempotency_key: str,
                    evidence_ids: list = None, correlation_id: str = "") -> dict:
    """Atomic authoritative transition. State + audit + idempotency in one transaction."""

    # Gate: mutations must be enabled
    if mutations_disabled():
        raise TransitionError("Mutations disabled — simulation only", "MUTATIONS_DISABLED")

    # Gate: actor role must have permission
    if action not in ROLE_PERMISSIONS.get(actor_role, []):
        raise TransitionError(f"Role {actor_role} cannot perform {action}", "UNAUTHORIZED")

    with get_auth_db() as db:
        # Idempotency check
        existing = db.execute(
            "SELECT result FROM idempotency_records WHERE key = ?",
            (idempotency_key,)).fetchone()
        if existing:
            return json.loads(existing["result"])

        # Read current state
        row = db.execute("SELECT * FROM authoritative_decisions WHERE id = ?",
                        (decision_id,)).fetchone()
        if not row:
            raise TransitionError(f"Decision {decision_id} not found", "NOT_FOUND")

        decision = dict(row)
        if decision["workflow_state"] != expected_state:
            raise TransitionError(
                f"Expected {expected_state} but decision is {decision['workflow_state']}",
                "STATE_MISMATCH")
        if decision["version"] != expected_version:
            raise TransitionError(
                f"Expected version {expected_version} but is {decision['version']}",
                "VERSION_MISMATCH")

        # Validate transition
        try:
            target = validate_transition(decision["workflow_state"], action, actor_role)
        except ValueError as e:
            raise TransitionError(str(e), "TRANSITION_FAILED")
        new_version = expected_version + 1
        now = datetime.now(timezone.utc).isoformat()

        # Atomic transaction
        db.execute("BEGIN IMMEDIATE")
        try:
            # Update decision
            db.execute("""
                UPDATE authoritative_decisions
                SET workflow_state = ?, version = ?, updated_at = ?,
                    last_action = ?, last_actor_id = ?, rationale = ?,
                    evidence_ids = ?
                WHERE id = ?
            """, (target, new_version, now, action, actor_id, rationale,
                  json.dumps(evidence_ids or []), decision_id))

            # Append audit event
            audit_id = str(uuid.uuid4())
            prev_events = db.execute(
                "SELECT event_hash FROM audit_events ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            prev_hash = prev_events["event_hash"] if prev_events else "GENESIS"

            event_data = json.dumps({
                "decision_id": decision_id, "action": action, "actor_id": actor_id,
                "actor_role": actor_role, "previous_state": expected_state,
                "resulting_state": target, "version": new_version,
                "idempotency_key": idempotency_key
            }, sort_keys=True)
            event_hash = _compute_hash(f"{prev_hash}|{event_data}|{now}")

            db.execute("""
                INSERT INTO audit_events (event_id, event_type, decision_id, action,
                    actor_id, actor_role, previous_state, resulting_state,
                    decision_version, idempotency_key, event_hash, prev_hash,
                    result, created_at)
                VALUES (?, 'decision.transition', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', ?)
            """, (audit_id, decision_id, action, actor_id, actor_role,
                  expected_state, target, new_version, idempotency_key,
                  event_hash, prev_hash, now))

            # Persist idempotency
            db.execute(
                "INSERT INTO idempotency_records (key, result, created_at) VALUES (?, ?, ?)",
                (idempotency_key, json.dumps({"result": "success", "new_state": target,
                    "new_version": new_version, "audit_id": audit_id}), now))

            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise TransitionError("Transaction failed — rolled back", "TRANSACTION_FAILED")

        return {"result": "success", "new_state": target,
                "new_version": new_version, "audit_id": audit_id}

# --- Legacy Import ---
def dry_run_import(source_dir: str) -> dict:
    """Analyze legacy YAML decisions without writing."""
    import yaml, os
    stats = {"discovered": 0, "valid": 0, "invalid": 0, "duplicates": 0,
             "manual_review": 0, "rejected": 0}
    seen_ids = set()

    if not os.path.isdir(source_dir):
        return stats

    for fname in sorted(os.listdir(source_dir)):
        if not fname.endswith(".yaml"):
            continue
        stats["discovered"] += 1
        path = os.path.join(source_dir, fname)
        try:
            with open(path) as f:
                record = yaml.safe_load(f)
        except Exception:
            stats["invalid"] += 1
            continue

        if not isinstance(record, dict):
            stats["invalid"] += 1
            continue

        rec_id = record.get("decision_id") or record.get("id", "")
        if not rec_id:
            stats["invalid"] += 1
            continue
        if rec_id in seen_ids:
            stats["duplicates"] += 1
            continue
        seen_ids.add(rec_id)

        # State mapping
        legacy_state = record.get("status") or record.get("state", "")
        normalized = _map_state(legacy_state)
        if normalized == "MIGRATION_REVIEW_REQUIRED":
            stats["manual_review"] += 1
        else:
            stats["valid"] += 1

    return stats

def _map_state(legacy: str) -> str:
    STATE_MAP = {
        "locked": "LOCKED", "proposed": "AWAITING_AMJAD",
        "approved": "APPROVED", "rejected": "REJECTED",
        "deferred": "DEFERRED", "closed": "MIGRATION_REVIEW_REQUIRED",
        "hold": "HOLD", "blocked": "BLOCKED",
    }
    return STATE_MAP.get(legacy.lower(), "MIGRATION_REVIEW_REQUIRED")

# --- Git Projection (local test only) ---
def project_to_directory(output_dir: str, decisions: list = None) -> dict:
    """Export decisions as YAML files. Local test repository only."""
    import yaml, os
    if not decisions:
        decisions = list_decisions()
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    for d in decisions:
        out = {k: v for k, v in d.items()
               if k not in ("export_status", "export_version")}
        out["_generated"] = "DO NOT EDIT — generated by Hermes authoritative adapter"
        out["_version"] = d.get("version", 1)
        path = os.path.join(output_dir, f"{d['id']}.yaml")
        with open(path, "w") as f:
            yaml.dump(out, f, default_flow_style=False, sort_keys=True, allow_unicode=True)
        count += 1
    return {"exported": count, "to": output_dir}