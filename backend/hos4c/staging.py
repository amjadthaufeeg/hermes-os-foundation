"""
HOS-4D.4D: Linux Staging and Incident Validation
Non-root service model, filesystem permissions, service lifecycle,
incident exercises, recovery validation. Local simulation mode.
"""

import os, stat, tempfile
from enum import Enum
from typing import Optional

# --- Service Model ---
SERVICE_USER = "hermes"
SERVICE_GROUP = "hermes"

REQUIRED_DIRS = {
    "app": "/opt/hermes/app",
    "config": "/opt/hermes/config",
    "data": "/opt/hermes/data",
    "backup": "/opt/hermes/backup",
    "runtime": "/opt/hermes/runtime",
    "logs": "/var/log/hermes",
}

PERMISSION_MATRIX = {
    "app": 0o755,      # read+execute, no write
    "config": 0o750,   # read+execute, group read
    "data": 0o700,     # hermes only
    "backup": 0o700,   # hermes only
    "runtime": 0o700,  # hermes only
    "logs": 0o750,     # group read for monitoring
}

SECRETS_FILES = ["/opt/hermes/config/env"]
SECRETS_PERMISSIONS = 0o600  # owner read only

# --- Incident Types ---
class Incident(str, Enum):
    SERVICE_CRASH = "SERVICE_CRASH"
    RESTART_LOOP = "RESTART_LOOP"
    DB_CORRUPT = "DB_CORRUPT"
    DB_LOCKED = "DB_LOCKED"
    DISK_NEAR_FULL = "DISK_NEAR_FULL"
    BACKUP_OVERDUE = "BACKUP_OVERDUE"
    KEY_UNAVAILABLE = "KEY_UNAVAILABLE"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    AUDIT_MISMATCH = "AUDIT_MISMATCH"
    CHECKPOINT_MISMATCH = "CHECKPOINT_MISMATCH"
    SESSION_INVAL_FAILURE = "SESSION_INVAL_FAILURE"
    MUTATION_DISABLE_FAILURE = "MUTATION_DISABLE_FAILURE"

# --- Validation Functions ---
def validate_non_root() -> bool:
    """Service must not run as root."""
    return os.geteuid() != 0

def validate_permissions(path: str, expected_mode: int) -> bool:
    """Check file/dir permissions match expected."""
    if not os.path.exists(path):
        return False
    actual = stat.S_IMODE(os.stat(path).st_mode)
    return actual == expected_mode

def validate_secrets_permissions() -> bool:
    """Secrets files must be 0600."""
    for f in SECRETS_FILES:
        if os.path.exists(f) and not validate_permissions(f, SECRETS_PERMISSIONS):
            return False
    return True

def detect_disk_pressure(threshold_pct: float = 90.0) -> bool:
    """Detect if disk is nearly full."""
    try:
        statvfs = os.statvfs("/opt/hermes/data")
        used_pct = (1.0 - statvfs.f_bavail / statvfs.f_blocks) * 100
        return used_pct > threshold_pct
    except Exception:
        return False

# --- Recovery Exercise ---
def recovery_exercise_summary():
    """Return expected recovery exercise steps for documentation."""
    return [
        "1. Create test data",
        "2. Create SQLite backup",
        "3. Generate manifest",
        "4. Encrypt with age public key",
        "5. Store in isolated storage",
        "6. Verify stored archive",
        "7. Stop service",
        "8. Retrieve encrypted archive",
        "9. Decrypt in recovery boundary",
        "10. Restore into clean database",
        "11. SQLite integrity validation",
        "12. Schema and migration validation",
        "13. Audit chain reconciliation",
        "14. Checkpoint chain reconciliation",
        "15. Invalidate restored sessions",
        "16. Confirm mutations disabled",
        "17. Verify readiness (test config only)",
        "18. Produce recovery evidence",
        "19. Clean temporary artifacts",
    ]

# --- RPO/RTO Tracker ---
class RecoveryTimer:
    def __init__(self):
        self.phases: dict[str, float] = {}

    def record(self, phase: str, seconds: float):
        self.phases[phase] = seconds

    def total(self) -> float:
        return sum(self.phases.values())

    def rpo_age(self, backup_created: str, recovery_started: str) -> float:
        """Calculate recovery-point age in hours."""
        from datetime import datetime, timezone
        created = datetime.fromisoformat(backup_created)
        started = datetime.fromisoformat(recovery_started)
        return (started - created).total_seconds() / 3600.0

    def rto_total(self) -> float:
        """Total recovery time in hours."""
        return self.total() / 3600.0

    def rpo_met(self, age_hours: float, target_hours: float = 24.0) -> bool:
        return age_hours <= target_hours

    def rto_met(self, target_hours: float = 2.0) -> bool:
        return self.rto_total() <= target_hours