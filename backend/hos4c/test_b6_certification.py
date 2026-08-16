"""B6 closure certification: measured isolated RPO/RTO + deployed cadence policy.

This test never mutates production. It creates an isolated recovery point,
executes the existing recovery pipeline, records measured freshness/recovery
time, and verifies the checked-in snapshot timer cadence against explicit
closure thresholds.
"""
import os
import re
import sqlite3
import time
from pathlib import Path

from backend.hos4c.backup import create_backup
from backend.hos4c.encryption import (
    CATALOG,
    StorageAdapter,
    encrypt_with_age,
    generate_age_keypair,
    record_catalog_entry,
)
from backend.hos4c.restore import RecoveryRequest, RecoveryState, run_recovery


RPO_TARGET_SECONDS = 24 * 60 * 60
RTO_TARGET_SECONDS = 2 * 60 * 60
TIMER_FILE = Path("deploy/hermes-snapshot-refresh.timer")


def _timer_seconds(name: str) -> int:
    text = TIMER_FILE.read_text()
    match = re.search(rf"^{re.escape(name)}=(\d+)$", text, re.MULTILINE)
    assert match, f"missing {name} in {TIMER_FILE}"
    return int(match.group(1))


def _source_db(tmp_path: Path) -> str:
    path = tmp_path / "source.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, event_type TEXT, "
        "decision_id TEXT, action TEXT, actor_id TEXT, actor_role TEXT, session_id TEXT, "
        "previous_state TEXT, resulting_state TEXT, rationale TEXT, reason_code TEXT, "
        "created_at TEXT, hash TEXT, previous_hash TEXT)"
    )
    conn.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT)")
    conn.execute("CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id TEXT)")
    conn.execute("INSERT INTO decisions VALUES ('DEC-B6', 'AWAITING')")
    conn.execute("INSERT INTO sessions VALUES ('sess-b6', 'amjad')")
    conn.commit()
    conn.close()
    return str(path)


def test_b6_measured_rpo_rto_and_cadence(tmp_path):
    CATALOG.clear()
    source_db = _source_db(tmp_path)

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    recovery_point = create_backup(source_db, str(backup_dir))

    measured_rpo_seconds = max(0.0, time.time() - os.path.getmtime(recovery_point))
    assert measured_rpo_seconds <= RPO_TARGET_SECONDS

    private_key, public_key = generate_age_keypair()
    encrypted = encrypt_with_age(recovery_point, public_key)
    storage = StorageAdapter()
    obj = storage.upload("BKP-B6-CERT", encrypted)
    record_catalog_entry(
        "BKP-B6-CERT", "OFFHOST_VERIFIED", obj.checksum, "key-b6", obj
    )

    request = RecoveryRequest("REC-B6-CERT", "BKP-B6-CERT", "operator")
    assert request.approve("AMJAD_OWNER")

    restore_dir = tmp_path / "restore"
    restore_dir.mkdir()
    started = time.monotonic()
    evidence = run_recovery(request, storage, private_key, str(restore_dir))
    measured_rto_seconds = time.monotonic() - started

    assert evidence["state"] == RecoveryState.VERIFIED_TEST_ONLY.value
    assert measured_rto_seconds <= RTO_TARGET_SECONDS

    interval_seconds = _timer_seconds("OnUnitActiveSec")
    randomized_delay_seconds = _timer_seconds("RandomizedDelaySec")
    cadence_max_seconds = interval_seconds + randomized_delay_seconds
    assert cadence_max_seconds <= RPO_TARGET_SECONDS

    print(
        "B6_CERT|"
        f"rpo_age_seconds={measured_rpo_seconds:.3f}|"
        f"rpo_target_seconds={RPO_TARGET_SECONDS}|"
        f"rto_seconds={measured_rto_seconds:.3f}|"
        f"rto_target_seconds={RTO_TARGET_SECONDS}|"
        f"cadence_max_seconds={cadence_max_seconds}"
    )
