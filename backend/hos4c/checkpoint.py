"""
HOS-4D.4A: External Audit Checkpoint Foundation
Ed25519 signing, canonical payload, checkpoint chaining,
storage adapter, verification. Isolated test mode only.
"""

import os, json, hashlib, uuid
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# --- Key Management ---
def generate_keypair() -> tuple:
    """Generate Ed25519 keypair. Returns (private_key_pem, public_key_pem)."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    priv_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    pub_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return priv_pem, pub_pem

def sign_payload(payload: dict, private_key_pem: str) -> str:
    """Sign canonical JSON payload. Returns hex signature."""
    private = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    signature = private.sign(canonical.encode())
    return signature.hex()

def verify_signature(payload: dict, signature_hex: str, public_key_pem: str) -> bool:
    """Verify Ed25519 signature over canonical payload."""
    try:
        public = serialization.load_pem_public_key(public_key_pem.encode())
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        public.verify(bytes.fromhex(signature_hex), canonical.encode())
        return True
    except (InvalidSignature, Exception):
        return False

# --- Checkpoint Payload ---
def build_checkpoint_payload(
    audit_chain_head: str,
    last_audit_event_id: str,
    schema_version: int,
    environment: str,
    signing_key_id: str,
    previous_checkpoint_hash: Optional[str] = None,
) -> dict:
    """Build canonical checkpoint payload."""
    return {
        "checkpoint_id": f"CKP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "checkpoint_timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_schema_version": 1,
        "audit_chain_head_hash": audit_chain_head,
        "last_audit_event_id": last_audit_event_id,
        "authoritative_schema_version": schema_version,
        "migration_history_head": "NOT_RECORDED",
        "projection_queue_summary": "NOT_RECORDED",
        "authoritative_decision_version_summary": {},
        "environment": environment,
        "service_instance_id": os.environ.get("SERVICE_INSTANCE_ID", "unknown"),
        "signing_key_id": signing_key_id,
        "previous_checkpoint_hash": previous_checkpoint_hash or "",
    }

def canonical_hash(payload: dict) -> str:
    """SHA-256 of canonical checkpoint payload (excluding signature)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

# --- Checkpoint States ---
VALID_STATES = {
    "PENDING", "SIGNED", "STORED", "VERIFIED",
    "VERIFICATION_FAILED", "STORE_FAILED", "MISSED", "STALE", "REVOKED_KEY"
}

# --- Storage Adapter ---
def store_checkpoint_local(directory: str, payload: dict, signature: str) -> str:
    """Store checkpoint as JSON file. Returns file path."""
    os.makedirs(directory, exist_ok=True)
    filename = f"{payload['checkpoint_id']}.json"
    path = os.path.join(directory, filename)

    record = {**payload, "signature": signature}
    with open(path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=2)
    return path

def load_checkpoint(path: str) -> dict:
    """Load checkpoint from file."""
    with open(path) as f:
        return json.load(f)

def list_checkpoints(directory: str) -> list:
    """List checkpoint files ordered by name."""
    if not os.path.isdir(directory):
        return []
    files = sorted([f for f in os.listdir(directory) if f.endswith(".json")])
    return [os.path.join(directory, f) for f in files]

def get_latest_checkpoint(directory: str) -> Optional[dict]:
    """Get most recent checkpoint."""
    files = list_checkpoints(directory)
    if not files:
        return None
    return load_checkpoint(files[-1])

# --- Verification ---
class CheckpointVerificationError(Exception):
    pass

def verify_checkpoint(payload: dict, signature: str, public_key_pem: str,
                     expected_prev_hash: str = None) -> bool:
    """Verify checkpoint signature and chain integrity. Raises on failure."""
    # Signature verification
    if not verify_signature(payload, signature, public_key_pem):
        raise CheckpointVerificationError("Invalid signature")

    # Chain verification
    if expected_prev_hash is not None:
        actual = payload.get("previous_checkpoint_hash", "")
        if actual != expected_prev_hash:
            raise CheckpointVerificationError(
                f"Chain break: expected prev_hash={expected_prev_hash[:12]}... got={actual[:12]}...")

    return True

def verify_chain(checkpoints: list, public_key_pem: str) -> bool:
    """Verify entire checkpoint chain. Raises on first failure."""
    prev_hash = ""
    for record in checkpoints:
        payload = {k: v for k, v in record.items() if k != "signature"}
        signature = record.get("signature", "")
        verify_checkpoint(payload, signature, public_key_pem, prev_hash)
        prev_hash = canonical_hash(payload)
    return True

def check_missed_checkpoint(directory: str, max_age_hours: int = 25) -> bool:
    """Return True if latest checkpoint is within max_age_hours."""
    latest = get_latest_checkpoint(directory)
    if not latest:
        return True  # Missed
    ts = datetime.fromisoformat(latest["checkpoint_timestamp"])
    age = datetime.now(timezone.utc) - ts
    return age.total_seconds() > max_age_hours * 3600