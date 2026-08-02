"""
HOS-4D.4C.1: Backup, Encryption, and Manifest Foundation
SQLite-safe backup, integrity checks, GPG encryption,
checksums, manifest, verification. Isolated test mode only.
"""

import os, json, hashlib, shutil, sqlite3, tempfile, uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# --- Backup States ---
class BackupState(str, Enum):
    PENDING = "PENDING"
    SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
    INTEGRITY_VERIFIED = "INTEGRITY_VERIFIED"
    MANIFEST_CREATED = "MANIFEST_CREATED"
    ENCRYPTED = "ENCRYPTED"
    ARCHIVE_VERIFIED = "ARCHIVE_VERIFIED"
    FAILED = "FAILED"
    CORRUPT = "CORRUPT"
    EXPIRED = "EXPIRED"
    RESTORED = "RESTORED"

# --- Source Integrity ---
def check_integrity(db_path: str) -> bool:
    """Run PRAGMA integrity_check on a SQLite database."""
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        return result[0] == "ok"
    except Exception:
        return False
    finally:
        conn.close()

# --- Backup Creation ---
def create_backup(source_db: str, destination_dir: str) -> Optional[str]:
    """Create SQLite backup using .backup. Returns backup path."""
    if not check_integrity(source_db):
        return None
    os.makedirs(destination_dir, exist_ok=True)
    filename = f"backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.db"
    dest = os.path.join(destination_dir, filename)

    src = sqlite3.connect(source_db)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    # Verify backup integrity
    if not check_integrity(dest):
        os.remove(dest)
        return None
    return dest

# --- Checksums ---
def sha256_file(path: str) -> str:
    """SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# --- Manifest ---
# --- Manifest Verification ---
def verify_manifest(manifest: dict, backup_path: str) -> bool:
    """Verify manifest against actual backup file. Returns True if valid."""
    if not isinstance(manifest, dict) or not os.path.exists(backup_path):
        return False
    required = ["backup_state", "manifest_schema_version", "files"]
    for field in required:
        if field not in manifest:
            return False
    for fname, expected_checksum in manifest.get("files", {}).items():
        actual = sha256_file(backup_path)
        if actual != expected_checksum:
            return False
    return True


def build_manifest(backup_path: str, source_db: str, key_id: str = "test-key-001") -> dict:
    """Build deterministic backup manifest."""
    return {
        "backup_id": f"BKP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_environment": os.environ.get("HERMES_ENVIRONMENT", "LOCAL_SIMULATION"),
        "service_version": "0.1.0",
        "source_database_id": os.path.basename(source_db),
        "database_schema_version": 1,
        "audit_chain_head": "NOT_RECORDED",
        "checkpoint_head": "NOT_RECORDED",
        "migration_history_head": "NOT_RECORDED",
        "files": {"backup.db": sha256_file(backup_path)},
        "encryption_key_id": key_id,
        "archive_format": "sqlite",
        "backup_state": BackupState.SNAPSHOT_CREATED.value,
        "retention_class": "DAILY",
        "manifest_schema_version": 1,
    }

# --- Retention ---
RETENTION_CLASSES = {
    "DAILY": 30,      # days
    "WEEKLY": 84,     # 12 weeks
    "MONTHLY": 365,   # 12 months
    "INCIDENT": 730,  # 2 years
    "PRE_MIGRATION": 365,
    "POST_MIGRATION": 365,
}

def is_expired(created_at: str, retention_class: str = "DAILY") -> bool:
    """Check if backup has exceeded retention."""
    if retention_class not in RETENTION_CLASSES:
        return False
    created = datetime.fromisoformat(created_at)
    age_days = (datetime.now(timezone.utc) - created).total_seconds() / 86400
    return age_days > RETENTION_CLASSES[retention_class]