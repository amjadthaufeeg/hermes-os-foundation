"""
HOS-4D.4C.2: Backup Encryption + Off-Host Storage Adapter
GPG-like test encryption, S3-compatible storage adapter,
credential separation, catalog, key lifecycle. Isolated test mode.
"""

import os, json, hashlib, uuid, tempfile
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from cryptography.fernet import Fernet
from backend.hos4c.backup import BackupState, sha256_file

# --- Encryption States ---
class EncryptionState(str, Enum):
    ENCRYPTION_PENDING = "ENCRYPTION_PENDING"
    ENCRYPTED = "ENCRYPTED"
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    KEY_UNAVAILABLE = "KEY_UNAVAILABLE"
    KEY_REVOKED = "KEY_REVOKED"

class StorageState(str, Enum):
    UPLOAD_PENDING = "UPLOAD_PENDING"
    UPLOADED = "UPLOADED"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    OFFHOST_VERIFIED = "OFFHOST_VERIFIED"
    OFFHOST_VERIFICATION_FAILED = "OFFHOST_VERIFICATION_FAILED"
    RETENTION_LOCKED = "RETENTION_LOCKED"

# --- Key Management ---
def generate_encryption_key() -> bytes:
    """Generate Fernet symmetric key."""
    return Fernet.generate_key()

def encrypt_backup(backup_path: str, key: bytes) -> Optional[str]:
    """Encrypt backup file. Returns path to encrypted archive."""
    if not os.path.exists(backup_path):
        return None
    f = Fernet(key)
    with open(backup_path, "rb") as src:
        data = src.read()
    encrypted = f.encrypt(data)
    dest = backup_path + ".enc"
    with open(dest, "wb") as out:
        out.write(encrypted)
    return dest

def decrypt_backup(encrypted_path: str, key: bytes, output_dir: str) -> Optional[str]:
    """Decrypt backup archive. Returns path to decrypted file."""
    if not os.path.exists(encrypted_path):
        return None
    f = Fernet(key)
    with open(encrypted_path, "rb") as src:
        data = src.read()
    try:
        plaintext = f.decrypt(data)
    except Exception:
        return None
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "restored.db")
    with open(dest, "wb") as out:
        out.write(plaintext)
    return dest

# --- Storage Adapter ---
@dataclass
class StorageObject:
    backup_id: str
    object_key: str
    version_id: str
    size_bytes: int
    checksum: str
    retention_class: str
    object_lock_enabled: bool
    uploaded_at: str
    storage_provider: str

class StorageAdapter:
    """Isolated test storage adapter. No real S3/B2 calls."""

    def __init__(self):
        self._store: dict[str, StorageObject] = {}
        self._data: dict[str, bytes] = {}

    def upload(self, backup_id: str, filepath: str, retention_class: str = "DAILY") -> StorageObject:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(filepath, "rb") as f:
            self._data[backup_id] = f.read()
        obj = StorageObject(
            backup_id=backup_id,
            object_key=f"backups/{backup_id}.enc",
            version_id=str(uuid.uuid4()),
            size_bytes=len(self._data[backup_id]),
            checksum=sha256_file(filepath),
            retention_class=retention_class,
            object_lock_enabled=retention_class in ("INCIDENT",),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            storage_provider="test-local",
        )
        self._store[backup_id] = obj
        return obj

    def download(self, backup_id: str, output_path: str) -> bool:
        if backup_id not in self._data:
            return False
        with open(output_path, "wb") as f:
            f.write(self._data[backup_id])
        return True

    def get_metadata(self, backup_id: str) -> Optional[StorageObject]:
        return self._store.get(backup_id)

    def list_backups(self) -> list[StorageObject]:
        return list(self._store.values())

    def delete(self, backup_id: str) -> bool:
        if backup_id in self._store:
            del self._store[backup_id]
            self._data.pop(backup_id, None)
            return True
        return False

# --- Credential Separation ---
class CredentialRole(str, Enum):
    BACKUP_WRITER = "BACKUP_WRITER"
    BACKUP_READER = "BACKUP_READER"
    RESTORE_OPERATOR = "RESTORE_OPERATOR"
    RETENTION_ADMIN = "RETENTION_ADMIN"
    AMJAD_OWNER = "AMJAD_OWNER"

CREDENTIAL_PERMISSIONS = {
    CredentialRole.BACKUP_WRITER: {"upload", "verify"},
    CredentialRole.BACKUP_READER: {"download", "verify"},
    CredentialRole.RESTORE_OPERATOR: {"download", "verify", "restore"},
    CredentialRole.RETENTION_ADMIN: {"retention", "delete"},
    CredentialRole.AMJAD_OWNER: {"upload", "download", "verify", "restore", "retention", "delete"},
}

def check_permission(role: str, action: str) -> bool:
    """Check if role can perform action. Hermes=0 for all."""
    if role in ("HERMES_ASSISTANT", "SYSTEM_SERVICE"):
        return False
    try:
        r = CredentialRole(role)
    except ValueError:
        return False
    return action in CREDENTIAL_PERMISSIONS.get(r, set())

# --- Backup Catalog ---
CATALOG: dict[str, dict] = {}

def record_catalog_entry(backup_id: str, state: str, checksum: str, key_id: str,
                         storage_obj: StorageObject):
    CATALOG[backup_id] = {
        "backup_id": backup_id,
        "state": state,
        "created_at": storage_obj.uploaded_at,
        "retention_class": storage_obj.retention_class,
        "encryption_key_id": key_id,
        "object_key": storage_obj.object_key,
        "version_id": storage_obj.version_id,
        "checksum": checksum,
        "verified": True,
    }