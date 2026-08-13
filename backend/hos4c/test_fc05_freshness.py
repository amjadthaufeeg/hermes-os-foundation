"""FC-05 Snapshot Freshness — Focused Tests.

Tests: fresh/stale/missing/corrupt/mismatch/future/hash-binding.
"""
import json, os, shutil, tempfile, time
import hashlib
import pytest

from backend.hos4c.snapshot_freshness import (
    freshness_enforced, snapshot_freshness, snapshot_read_allowed,
    MAX_AGE_SECONDS,
)


@pytest.fixture
def fresh_snapshot_dir():
    """Create a fresh snapshot directory with snapshot.db + snapshot.meta.json."""
    d = tempfile.mkdtemp()
    # Create snapshot.db (1 byte OK)
    db_content = b"test snapshot data"
    db_path = os.path.join(d, "snapshot.db")
    with open(db_path, "wb") as f:
        f.write(db_content)
    # Compute real SHA
    db_sha = hashlib.sha256(db_content).hexdigest()
    # Create metadata with current time
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    meta = {"created_at_utc": now, "sha256": db_sha, "result": "published"}
    with open(os.path.join(d, "snapshot.meta.json"), "w") as f:
        json.dump(meta, f)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# --- Freshness Enforcement Toggle ---

def test_freshness_enforced_false_by_default(monkeypatch):
    monkeypatch.delenv("SNAPSHOT_FRESHNESS_ENFORCED", raising=False)
    assert not freshness_enforced()

def test_freshness_enforced_true(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_FRESHNESS_ENFORCED", "true")
    assert freshness_enforced()

def test_freshness_enforced_respects_exact(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_FRESHNESS_ENFORCED", "TRUE")
    assert freshness_enforced()


# --- Fresh Snapshot ---

def test_fresh_snapshot_pass(fresh_snapshot_dir):
    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "FRESH"
    assert evidence["age_seconds"] <= 5  # just created

def test_fresh_snapshot_read_allowed(fresh_snapshot_dir):
    allowed, evidence = snapshot_read_allowed(fresh_snapshot_dir)
    assert allowed
    assert evidence["status"] == "FRESH"


# --- Missing Snapshot ---

def test_missing_db(tmp_path):
    evidence = snapshot_freshness(str(tmp_path))
    assert evidence["status"] == "UNAVAILABLE"

def test_missing_metadata(fresh_snapshot_dir):
    os.remove(os.path.join(fresh_snapshot_dir, "snapshot.meta.json"))
    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "UNAVAILABLE"


# --- Corrupt Metadata ---

def test_corrupt_metadata(fresh_snapshot_dir):
    with open(os.path.join(fresh_snapshot_dir, "snapshot.meta.json"), "w") as f:
        f.write("not json")
    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "INVALID"


# --- Stale Snapshot (> 900s) ---

def test_stale_snapshot(fresh_snapshot_dir, monkeypatch):
    # Set created_at_utc to 1000 seconds ago
    from datetime import datetime, timedelta, timezone
    old = datetime.now(timezone.utc) - timedelta(seconds=1000)
    meta_path = os.path.join(fresh_snapshot_dir, "snapshot.meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    meta["created_at_utc"] = old.isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "STALE"
    assert evidence["age_seconds"] >= 999

def test_stale_not_allowed(fresh_snapshot_dir):
    from datetime import datetime, timedelta, timezone
    old = datetime.now(timezone.utc) - timedelta(seconds=1000)
    meta_path = os.path.join(fresh_snapshot_dir, "snapshot.meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    meta["created_at_utc"] = old.isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    allowed, evidence = snapshot_read_allowed(fresh_snapshot_dir)
    assert not allowed
    assert evidence["status"] == "STALE"


# --- Hash Mismatch ---

def test_hash_mismatch(fresh_snapshot_dir):
    # Tamper with snapshot.db but keep metadata.sha256 the same
    with open(os.path.join(fresh_snapshot_dir, "snapshot.db"), "wb") as f:
        f.write(b"tampered data")
    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "MISMATCH"
    assert "sha" in evidence.get("expected_sha", "").lower() or "actual_sha" in evidence


# --- Future Timestamp ---

def test_future_timestamp_rejected(fresh_snapshot_dir):
    from datetime import datetime, timedelta, timezone
    future = datetime.now(timezone.utc) + timedelta(seconds=600)
    meta_path = os.path.join(fresh_snapshot_dir, "snapshot.meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    meta["created_at_utc"] = future.isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "INVALID"
    assert "future" in evidence["reason"].lower()


# --- Within tolerance future (5s) ---

def test_future_within_tolerance_pass(fresh_snapshot_dir):
    from datetime import datetime, timedelta, timezone
    near_future = datetime.now(timezone.utc) + timedelta(seconds=3)
    meta_path = os.path.join(fresh_snapshot_dir, "snapshot.meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    meta["created_at_utc"] = near_future.isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "FRESH"


# --- Missing created_at_utc ---

def test_metadata_missing_timestamp(fresh_snapshot_dir):
    meta_path = os.path.join(fresh_snapshot_dir, "snapshot.meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    del meta["created_at_utc"]
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    evidence = snapshot_freshness(fresh_snapshot_dir)
    assert evidence["status"] == "INVALID"


# --- Startup Policy Enforcement ---

def test_snapshot_consumer_requires_freshness_enforced(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_CONSUMER", "true")
    monkeypatch.delenv("SNAPSHOT_FRESHNESS_ENFORCED", raising=False)
    from backend.hos4c.environment import validate_startup
    errors = validate_startup()
    fatals = [e for e in errors if "SNAPSHOT_FRESHNESS_ENFORCED" in e]
    assert len(fatals) >= 1

def test_snapshot_consumer_freshness_false_fails(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_CONSUMER", "true")
    monkeypatch.setenv("SNAPSHOT_FRESHNESS_ENFORCED", "false")
    from backend.hos4c.environment import validate_startup
    errors = validate_startup()
    fatals = [e for e in errors if "SNAPSHOT_FRESHNESS_ENFORCED" in e]
    assert len(fatals) >= 1

def test_snapshot_consumer_freshness_true_pass(monkeypatch):
    monkeypatch.setenv("SNAPSHOT_CONSUMER", "true")
    monkeypatch.setenv("SNAPSHOT_FRESHNESS_ENFORCED", "true")
    from backend.hos4c.environment import validate_startup
    errors = validate_startup()
    fatals = [e for e in errors if "SNAPSHOT_FRESHNESS_ENFORCED" in e]
    assert len(fatals) == 0

def test_non_snapshot_consumer_no_freshness_required(monkeypatch):
    monkeypatch.delenv("SNAPSHOT_CONSUMER", raising=False)
    monkeypatch.delenv("SNAPSHOT_FRESHNESS_ENFORCED", raising=False)
    from backend.hos4c.environment import validate_startup
    errors = validate_startup()
    fatals = [e for e in errors if "SNAPSHOT_FRESHNESS_ENFORCED" in e]
    assert len(fatals) == 0