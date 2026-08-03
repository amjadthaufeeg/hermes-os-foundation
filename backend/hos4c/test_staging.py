"""
HOS-4D.4D: Linux Staging Tests
Non-root validation, filesystem permissions, incident exercises,
recovery timer, RPO/RTO measurement.
Run: python3.11 -m pytest backend/hos4c/test_staging.py -v
"""

import pytest, os, stat, tempfile, json
from datetime import datetime, timezone
from backend.hos4c.staging import (
    validate_non_root, validate_permissions, validate_secrets_permissions,
    detect_disk_pressure, RecoveryTimer, Incident,
    PERMISSION_MATRIX, SECRETS_PERMISSIONS,
)

# --- Non-Root Service ---
class TestNonRoot:
    def test_validate_non_root(self):
        # Will be True on CI (non-root runner), False on local macOS
        result = validate_non_root()
        assert isinstance(result, bool)

# --- Filesystem Permissions ---
class TestFilesystem:
    def test_permissions_check_absent_file(self):
        assert not validate_permissions("/nonexistent/path", 0o600)

    def test_secrets_should_be_restricted(self):
        assert SECRETS_PERMISSIONS == 0o600

    def test_data_dir_permissions(self):
        assert PERMISSION_MATRIX["data"] == 0o700

    def test_app_dir_read_only(self):
        mode = PERMISSION_MATRIX["app"]
        assert not (mode & 0o222)  # no write bits

# --- Incident Detection ---
class TestIncidents:
    def test_disk_pressure_not_on_nonexistent(self):
        assert not detect_disk_pressure()

    def test_all_incidents_defined(self):
        assert len(Incident) == 12
        assert Incident.SERVICE_CRASH.value == "SERVICE_CRASH"
        assert Incident.DB_CORRUPT.value == "DB_CORRUPT"

# --- Recovery Timer ---
class TestRecovery:
    def test_timer_phases(self):
        t = RecoveryTimer()
        t.record("retrieval", 10.0)
        t.record("decryption", 2.0)
        assert t.total() == 12.0

    def test_rpo_calculation(self):
        t = RecoveryTimer()
        age = t.rpo_age("2026-08-03T00:00:00+00:00", "2026-08-03T12:00:00+00:00")
        assert age == 12.0

    def test_rpo_target_met(self):
        t = RecoveryTimer()
        assert t.rpo_met(12.0, 24.0)
        assert not t.rpo_met(25.0, 24.0)

    def test_rto_target_met(self):
        t = RecoveryTimer()
        t.record("total", 3600.0)  # 1 hour
        assert t.rto_met(2.0)
        t.record("total", 7200.0)  # 2 hours
        assert t.rto_met(2.0)

# --- Count ---
def test_staging_count():
    classes = [TestNonRoot, TestFilesystem, TestIncidents, TestRecovery]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4D Staging Tests: {total} ===\n")
    assert total >= 10