"""
HOS-4D.4C.2: Asymmetric Backup Encryption + Off-Host Storage
age encryption: writer gets public key, recovery gets private key.
Credential separation, catalog, key lifecycle. Isolated test mode.
"""

import os, json, uuid, subprocess
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from backend.hos4c.backup import sha256_file

# --- Asymmetric age Encryption ---
# Cryptographic separation: writer has public key (encrypt only)
# Recovery boundary has private key (decrypt only)

AGE_PUBLIC_KEY_HEADER = "age1"

def generate_age_keypair() -> tuple:
    """Generate age keypair. Returns (private_key_str, public_key_str)."""
    priv = subprocess.run(["age-keygen"], capture_output=True, text=True, timeout=5)
    if priv.returncode != 0:
        raise RuntimeError("age-keygen failed — install age: brew install age")
    lines = priv.stdout.strip().split("\n")
    pub = None
    for line in lines:
        if line.startswith("# public key: "):
            pub = line.replace("# public key: ", "").strip()
    return priv.stdout.strip(), pub

def encrypt_with_age(backup_path: str, public_key: str) -> Optional[str]:
    """Encrypt backup with age public key. Writer has NO private key."""
    if not os.path.exists(backup_path) or not public_key.startswith("age1"):
        return None
    dest = backup_path + ".age"
    result = subprocess.run(
        ["age", "-r", public_key, "-o", dest, backup_path],
        capture_output=True, text=True, timeout=30
    )
    return dest if result.returncode == 0 else None

def decrypt_with_age(encrypted_path: str, private_key: str, output_dir: str) -> Optional[str]:
    """Decrypt age archive. Private key required — NEVER on writer VPS."""
    if not os.path.exists(encrypted_path) or "AGE-SECRET-KEY" not in private_key:
        return None
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "restored.db")
    result = subprocess.run(
        ["age", "-d", "-i", "-", "-o", dest, encrypted_path],
        input=private_key, capture_output=True, text=True, timeout=30
    )
    return dest if result.returncode == 0 else None

# --- Encryption States ---
class EncryptionState(str, Enum):
    ENCRYPTION_PENDING = "ENCRYPTION_PENDING"
    ENCRYPTED = "ENCRYPTED"
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    KEY_UNAVAILABLE = "KEY_UNAVAILABLE"
    KEY_REVOKED = "KEY_REVOKED"

# --- Storage Adapter (isolated test mode, no real S3) ---
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
    def __init__(self):
        self._store: dict[str, StorageObject] = {}
        self._data: dict[str, bytes] = {}

    def upload(self, backup_id: str, filepath: str, retention_class: str = "DAILY") -> StorageObject:
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        with open(filepath, "rb") as f:
            self._data[backup_id] = f.read()
        obj = StorageObject(
            backup_id=backup_id,
            object_key=f"backups/{backup_id}.age",
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

# --- Credential Separation ---
class CredentialRole(str, Enum):
    BACKUP_WRITER = "BACKUP_WRITER"
    RESTORE_OPERATOR = "RESTORE_OPERATOR"
    AMJAD_OWNER = "AMJAD_OWNER"

CREDENTIAL_PERMISSIONS = {
    CredentialRole.BACKUP_WRITER: {"upload", "verify"},
    CredentialRole.RESTORE_OPERATOR: {"download", "verify", "restore"},
    CredentialRole.AMJAD_OWNER: {"upload", "download", "verify", "restore", "delete"},
}

def check_permission(role: str, action: str) -> bool:
    if role in ("HERMES_ASSISTANT", "SYSTEM_SERVICE"):
        return False
    try:
        r = CredentialRole(role)
    except ValueError:
        return False
    return action in CREDENTIAL_PERMISSIONS.get(r, set())

# --- Backup Catalog ---
CATALOG: dict[str, dict] = {}

def record_catalog_entry(backup_id: str, state: str, checksum: str, key_id: str, storage_obj: StorageObject):
    CATALOG[backup_id] = {
        "backup_id": backup_id, "state": state, "created_at": storage_obj.uploaded_at,
        "retention_class": storage_obj.retention_class, "encryption_key_id": key_id,
        "object_key": storage_obj.object_key, "version_id": storage_obj.version_id,
        "checksum": checksum, "verified": True,
    }