"""HOS-4 — Snapshot Freshness Enforcement (FC-05 corrected design).

Authoritative freshness uses metadata + hash binding:
  snapshot.meta.json.created_at_utc + snapshot.meta.json.sha256
  vs actual SHA256(snapshot.db)

Maximum snapshot age: 900 seconds (15 minutes).
mtime is secondary sanity evidence only.
"""
import hashlib
import json
import os
import time


MAX_AGE_SECONDS = 900
FUTURE_TOLERANCE = 5  # seconds — small clock-skew tolerance


def freshness_enforced() -> bool:
    """Return True if snapshot freshness enforcement is active."""
    return os.environ.get("SNAPSHOT_FRESHNESS_ENFORCED", "").strip().lower() == "true"


def snapshot_freshness(snapshot_dir: str) -> dict:
    """Check snapshot freshness. Returns structured evidence dict.

    status values: FRESH, STALE, UNAVAILABLE, INVALID, MISMATCH
    """
    db_path = os.path.join(snapshot_dir, "snapshot.db")
    meta_path = os.path.join(snapshot_dir, "snapshot.meta.json")

    # --- snapshot.db must exist ---
    if not os.path.isfile(db_path):
        return {
            "status": "UNAVAILABLE",
            "age_seconds": None,
            "reason": "snapshot.db missing",
            "snapshot_dir": snapshot_dir,
        }

    # --- snapshot.meta.json must exist ---
    if not os.path.isfile(meta_path):
        return {
            "status": "UNAVAILABLE",
            "age_seconds": None,
            "reason": "snapshot.meta.json missing",
            "snapshot_dir": snapshot_dir,
        }

    # --- Parse metadata ---
    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {
            "status": "INVALID",
            "age_seconds": None,
            "reason": f"snapshot.meta.json malformed: {e}",
            "snapshot_dir": snapshot_dir,
        }

    created_str = meta.get("created_at_utc")
    if not created_str:
        return {
            "status": "INVALID",
            "age_seconds": None,
            "reason": "snapshot.meta.json missing created_at_utc",
            "snapshot_dir": snapshot_dir,
        }

    # --- Compute age ---
    try:
        from datetime import datetime, timezone
        created = datetime.fromisoformat(created_str)
        now = datetime.now(timezone.utc)
        age = (now - created).total_seconds()
    except (ValueError, TypeError) as e:
        return {
            "status": "INVALID",
            "age_seconds": None,
            "reason": f"invalid created_at_utc format: {e}",
            "snapshot_dir": snapshot_dir,
        }

    # --- Future timestamp (beyond tolerance) ---
    if age < -FUTURE_TOLERANCE:
        return {
            "status": "INVALID",
            "age_seconds": round(age, 1),
            "reason": f"snapshot timestamp is {abs(age):.0f}s in the future (tolerance {FUTURE_TOLERANCE}s)",
            "snapshot_dir": snapshot_dir,
        }

    # Clamp small negative ages to 0 (within tolerance)
    age = max(age, 0.0)

    # --- Stale check ---
    if age > MAX_AGE_SECONDS:
        return {
            "status": "STALE",
            "age_seconds": round(age, 1),
            "threshold_seconds": MAX_AGE_SECONDS,
            "reason": f"snapshot is {age:.0f}s old, max {MAX_AGE_SECONDS}s",
            "snapshot_dir": snapshot_dir,
        }

    # --- Hash binding: metadata.sha256 must match actual snapshot.db ---
    expected_sha = meta.get("sha256")
    if expected_sha:
        try:
            actual_sha = hashlib.sha256()
            with open(db_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    actual_sha.update(chunk)
            actual_sha_hex = actual_sha.hexdigest()
        except OSError as e:
            return {
                "status": "INVALID",
                "age_seconds": round(age, 1),
                "reason": f"cannot read snapshot.db for hash: {e}",
                "snapshot_dir": snapshot_dir,
            }

        if actual_sha_hex != expected_sha:
            return {
                "status": "MISMATCH",
                "age_seconds": round(age, 1),
                "reason": "metadata.sha256 does not match actual snapshot.db SHA256",
                "expected_sha": expected_sha[:12],
                "actual_sha": actual_sha_hex[:12],
                "snapshot_dir": snapshot_dir,
            }
    else:
        # metadata has no sha256 — mtime as fallback evidence only
        pass

    # --- FRESH ---
    return {
        "status": "FRESH",
        "age_seconds": round(age, 1),
        "threshold_seconds": MAX_AGE_SECONDS,
        "snapshot_dir": snapshot_dir,
    }


def snapshot_read_allowed(snapshot_dir: str) -> tuple[bool, dict]:
    """Return (allowed, evidence). Only FRESH snapshots are allowed for reads."""
    evidence = snapshot_freshness(snapshot_dir)
    allowed = evidence["status"] == "FRESH"
    return allowed, evidence