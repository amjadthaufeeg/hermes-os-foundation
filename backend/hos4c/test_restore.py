"""
HOS-4D.4C.3: Restore + Recovery Tests
Recovery authority, pipeline, states, decryption, restore,
validation, session invalidation, mutation safety, timing.
Run: python3.11 -m pytest backend/hos4c/test_restore.py -v
"""

import pytest, os, tempfile, sqlite3
from backend.hos4c.restore import (
    RecoveryRequest, RecoveryState, run_recovery,
    invalidate_sessions, confirm_mutations_disabled,
)
from backend.hos4c.encryption import (
    generate_age_keypair, encrypt_with_age, StorageAdapter,
    record_catalog_entry, CATALOG,
)
from backend.hos4c.backup import create_backup, check_integrity

@pytest.fixture(autouse=True)
def cleanup():
    CATALOG.clear()
    yield

@pytest.fixture
def keypair():
    return generate_age_keypair()

@pytest.fixture
def source_db():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "test.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT)")
    conn.execute("CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id TEXT)")
    conn.execute("INSERT INTO decisions VALUES ('DEC-001', 'AWAITING')")
    conn.execute("INSERT INTO sessions VALUES ('sess-abc', 'amjad')")
    conn.commit(); conn.close()
    return path

@pytest.fixture
def encrypted_backup(source_db, keypair):
    priv, pub = keypair
    backup = create_backup(source_db, tempfile.mkdtemp())
    enc = encrypt_with_age(backup, pub)
    storage = StorageAdapter()
    obj = storage.upload("BKP-001", enc)
    record_catalog_entry("BKP-001", "OFFHOST_VERIFIED", obj.checksum, "key-001", obj)
    return priv, storage

# --- Recovery Request + Authority ---
class TestRecoveryAuthority:
    def test_amjad_approves(self):
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        assert req.approve("AMJAD_OWNER")
        assert req.state == RecoveryState.APPROVED
        assert req.approved_by == "AMJAD_OWNER"

    def test_hermes_cannot_approve(self):
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        assert not req.approve("HERMES_ASSISTANT")
        assert req.state == RecoveryState.REQUESTED

    def test_operator_cannot_self_approve(self):
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        assert not req.approve("operator")
        assert req.state == RecoveryState.REQUESTED

    def test_unapproved_cannot_execute(self, encrypted_backup):
        priv, storage = encrypted_backup
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        evidence = run_recovery(req, storage, priv, tempfile.mkdtemp())
        assert evidence["state"] == "APPROVAL_REQUIRED"

# --- Recovery Pipeline ---
class TestRecoveryPipeline:
    def test_full_pipeline(self, encrypted_backup):
        priv, storage = encrypted_backup
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        req.approve("AMJAD_OWNER")
        evidence = run_recovery(req, storage, priv, tempfile.mkdtemp())
        assert evidence["state"] == RecoveryState.VERIFIED_TEST_ONLY.value
        assert evidence["duration_seconds"] > 0

    def test_wrong_key_fails(self, encrypted_backup):
        _, storage = encrypted_backup
        wrong_priv, _ = generate_age_keypair()
        req = RecoveryRequest("REC-001", "BKP-001", "operator")
        req.approve("AMJAD_OWNER")
        evidence = run_recovery(req, storage, wrong_priv, tempfile.mkdtemp())
        assert evidence["state"] == RecoveryState.DECRYPTION_FAILED.value

    def test_missing_backup_fails(self, encrypted_backup):
        priv, storage = encrypted_backup
        req = RecoveryRequest("REC-001", "BKP-999", "operator")
        req.approve("AMJAD_OWNER")
        evidence = run_recovery(req, storage, priv, tempfile.mkdtemp())
        assert evidence["state"] == "RECOVERY_POINT_NOT_FOUND"

# --- Session Invalidation ---
class TestSessionInvalidation:
    def test_invalidate_sessions(self, source_db):
        conn = sqlite3.connect(source_db)
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        conn.close()
        invalidate_sessions(source_db)
        conn = sqlite3.connect(source_db)
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0

# --- Mutation Safety ---
class TestMutationSafety:
    def test_mutations_disabled(self):
        assert confirm_mutations_disabled()

# --- Count ---
def test_restore_count():
    classes = [TestRecoveryAuthority, TestRecoveryPipeline,
               TestSessionInvalidation, TestMutationSafety]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4C.3 Recovery Tests: {total} ===\n")
    assert total >= 9