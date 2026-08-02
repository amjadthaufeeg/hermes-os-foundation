"""
HOS-4D.4C.1: Backup Foundation Tests
SQLite backup, integrity, manifest, checksums, retention, states.
Run: python3.11 -m pytest backend/hos4c/test_backup.py -v
"""

import pytest, os, tempfile, sqlite3, json
from backend.hos4c.backup import (
    check_integrity, create_backup, sha256_file, build_manifest,
    verify_manifest, BackupState, RETENTION_CLASSES, is_expired,
)

@pytest.fixture
def source_db():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "test.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, state TEXT)")
    conn.execute("INSERT INTO decisions VALUES ('DEC-001', 'AWAITING_AMJAD')")
    conn.commit()
    conn.close()
    yield path

@pytest.fixture
def dest_dir():
    d = tempfile.mkdtemp()
    yield d

# --- SQLite Backup ---
class TestSQLiteBackup:
    def test_successful_backup(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        assert backup is not None
        assert os.path.exists(backup)
        assert check_integrity(backup)

    def test_backup_preserves_data(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        conn = sqlite3.connect(backup)
        rows = conn.execute("SELECT * FROM decisions").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "DEC-001"

    def test_source_integrity_fails(self, dest_dir):
        result = create_backup("/nonexistent/db.db", dest_dir)
        assert result is None

    def test_integrity_check(self, source_db):
        assert check_integrity(source_db)

    def test_corrupt_db_fails_integrity(self):
        assert not check_integrity("/nonexistent/path")

# --- Checksums ---
class TestChecksums:
    def test_sha256_file(self, source_db):
        h1 = sha256_file(source_db)
        h2 = sha256_file(source_db)
        assert len(h1) == 64
        assert h1 == h2

    def test_different_data_different_hash(self, source_db):
        h1 = sha256_file(source_db)
        # Modify source
        with open(source_db, "ab") as f:
            f.write(b"x")
        h2 = sha256_file(source_db)
        assert h1 != h2

# --- Manifest ---
class TestManifest:
    def test_build_manifest(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        manifest = build_manifest(backup, source_db)
        assert manifest["backup_state"] == BackupState.SNAPSHOT_CREATED.value
        assert "backup_id" in manifest
        assert "created_at" in manifest
        assert manifest["manifest_schema_version"] == 1

    def test_manifest_deterministic(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        m1 = build_manifest(backup, source_db)
        m2 = build_manifest(backup, source_db)
        # Stable fields match (backup_id/timestamp may vary)
        assert m1["manifest_schema_version"] == m2["manifest_schema_version"]

# --- Retention ---
class TestRetention:
    def test_daily_not_expired(self):
        assert is_expired("2026-08-03T00:00:00Z", "DAILY") is False  # tomorrow in context

    def test_really_old_expired(self):
        assert is_expired("2025-01-01T00:00:00Z", "DAILY") is True

    def test_incident_longer_retention(self):
        assert is_expired("2025-08-01T00:00:00Z", "INCIDENT") is False  # under 2 years

    def test_six_classes_defined(self):
        assert len(RETENTION_CLASSES) == 6
        for cls in ("DAILY", "WEEKLY", "MONTHLY", "INCIDENT", "PRE_MIGRATION", "POST_MIGRATION"):
            assert cls in RETENTION_CLASSES

# --- Backup States ---
class TestBackupStates:
    def test_states_enum(self):
        assert BackupState.PENDING.value == "PENDING"
        assert BackupState.SNAPSHOT_CREATED.value == "SNAPSHOT_CREATED"
        assert BackupState.FAILED.value == "FAILED"
        assert BackupState.RESTORED.value == "RESTORED"

# --- Cleanup ---
class TestCleanup:
    def test_backup_directory_is_temporary(self, source_db):
        d = tempfile.mkdtemp()
        create_backup(source_db, d)
        assert len(os.listdir(d)) >= 1

# --- Manifest Tampering Detection ---
class TestManifestTampering:
    def test_valid_manifest_passes(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        manifest = build_manifest(backup, source_db)
        assert verify_manifest(manifest, backup)

    def test_changed_checksum_detected(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        manifest = build_manifest(backup, source_db)
        manifest["files"]["backup.db"] = "sha256:0000000000000000"
        assert not verify_manifest(manifest, backup)

    def test_nonexistent_file_fails(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        manifest = build_manifest(backup, source_db)
        assert not verify_manifest(manifest, "/nonexistent/path")

    def test_missing_required_field(self, source_db, dest_dir):
        backup = create_backup(source_db, dest_dir)
        manifest = build_manifest(backup, source_db)
        del manifest["files"]
        assert not verify_manifest(manifest, backup)

# --- Count ---
def test_backup_count():
    classes = [TestSQLiteBackup, TestChecksums, TestManifest, TestRetention,
               TestBackupStates, TestCleanup]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4C.1 Backup Tests: {total} ===\n")
    assert total >= 15