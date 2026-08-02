"""HOS-4C Audit Ledger — Append-Only, Tamper-Evident"""

import uuid, hashlib, json, sqlite3
from datetime import datetime, timezone
from typing import Optional
from backend.hos4c.database import get_db

def _hash_event(prev_hash: str, data: dict) -> str:
    payload = prev_hash + json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()

def _get_last_hash(db: sqlite3.Connection) -> str:
    row = db.execute(
        "SELECT event_hash FROM audit_events ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return row["event_hash"] if row else "0" * 64  # Genesis hash

def record_audit_event(
    event_type: str,
    decision_id: str,
    action: str,
    actor_id: str,
    actor_role: str,
    session_id: Optional[str],
    previous_state: str,
    resulting_state: str,
    rationale: str,
    reason_code: Optional[str],
    decision_version: int,
    expected_version: int,
    idempotency_key: str,
    result: str,
    failure_reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
    client_context: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(uuid.uuid4())

    with get_db(db_path) if db_path else get_db() as db:
        prev_hash = _get_last_hash(db)

        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "decision_id": decision_id,
            "action": action,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "session_id": session_id,
            "previous_state": previous_state,
            "resulting_state": resulting_state,
            "rationale": rationale,
            "reason_code": reason_code,
            "decision_version": decision_version,
            "expected_version": expected_version,
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
            "client_context": client_context,
        }
        event_hash = _hash_event(prev_hash, event_data)

        db.execute("""
            INSERT INTO audit_events (
                event_id, event_type, decision_id, action, actor_id, actor_role,
                session_id, previous_state, resulting_state, rationale, reason_code,
                decision_version, expected_version, idempotency_key,
                request_timestamp, execution_timestamp, result, failure_reason,
                correlation_id, client_context, previous_event_hash, event_hash, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            event_id, event_type, decision_id, action, actor_id, actor_role,
            session_id, previous_state, resulting_state, rationale, reason_code,
            decision_version, expected_version, idempotency_key,
            now, now, result, failure_reason,
            correlation_id, client_context, prev_hash, event_hash, now
        ))

    return {"event_id": event_id, "event_hash": event_hash, "recorded_at": now}

def verify_hash_chain(db_path: Optional[str] = None) -> dict:
    """Verify integrity of the audit hash chain. Returns status and details."""
    with get_db(db_path) if db_path else get_db() as db:
        rows = db.execute(
            "SELECT * FROM audit_events ORDER BY created_at ASC"
        ).fetchall()

    expected_prev = "0" * 64
    verified = 0
    broken = []

    for row in rows:
        data = {
            "event_id": row["event_id"], "event_type": row["event_type"],
            "decision_id": row["decision_id"], "action": row["action"],
            "actor_id": row["actor_id"], "actor_role": row["actor_role"],
            "session_id": row["session_id"],
            "previous_state": row["previous_state"],
            "resulting_state": row["resulting_state"],
            "rationale": row["rationale"], "reason_code": row["reason_code"],
            "decision_version": row["decision_version"],
            "expected_version": row["expected_version"],
            "idempotency_key": row["idempotency_key"],
            "correlation_id": row["correlation_id"],
            "client_context": row["client_context"],
        }
        computed = _hash_event(expected_prev, data)
        if computed == row["event_hash"]:
            verified += 1
            expected_prev = computed
        else:
            broken.append(row["event_id"])

    return {
        "total_events": len(rows),
        "verified": verified,
        "broken": len(broken),
        "broken_event_ids": broken,
        "integrity": "INTACT" if not broken else "COMPROMISED",
    }