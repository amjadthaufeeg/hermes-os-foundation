"""
HOS-4D.5: Final Security — TOCTOU, Concurrency, Idempotency, Authority
Optimistic concurrency control, idempotency keys, replay protection,
activation-level enforcement, authority matrix. Level 0 only.
"""

import hashlib, time, uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# --- Activation Levels ---
class ActivationLevel(int, Enum):
    LEVEL_0 = 0  # Local validation only
    LEVEL_1 = 1  # Private VPS staging
    LEVEL_2 = 2  # Production read-only
    LEVEL_3 = 3  # Controlled authoritative writes
    LEVEL_4 = 4  # Full approved operations

CURRENT_ACTIVATION_LEVEL = ActivationLevel.LEVEL_0
MUTATIONS_ENABLED = False  # Always false below Level 3

def get_activation_level() -> int:
    return CURRENT_ACTIVATION_LEVEL.value

def mutations_authorized() -> bool:
    return CURRENT_ACTIVATION_LEVEL >= ActivationLevel.LEVEL_3 and MUTATIONS_ENABLED

# --- Concurrency Control ---
class RevisionConflict(Exception):
    def __init__(self, current_revision: int, expected_revision: int):
        self.current = current_revision
        self.expected = expected_revision
        super().__init__(f"REVISION_CONFLICT: current={current_revision} expected={expected_revision}")

class DecisionRecord:
    def __init__(self, decision_id: str, state: str, revision: int = 1):
        self.decision_id = decision_id
        self.state = state
        self.revision = revision
        self.owner_id = "amjad"

    def mutate(self, new_state: str, expected_revision: int) -> int:
        if not mutations_authorized():
            raise RuntimeError("MUTATIONS_DISABLED")
        if self.revision != expected_revision:
            raise RevisionConflict(self.revision, expected_revision)
        self.state = new_state
        self.revision += 1
        return self.revision

# --- Idempotency ---
IDEMPOTENCY_STORE: dict[str, dict] = {}

def idempotency_key(owner_id: str, mutation_type: str, payload_hash: str) -> str:
    return hashlib.sha256(f"{owner_id}:{mutation_type}:{payload_hash}".encode()).hexdigest()[:16]

def execute_idempotent(key: str, payload_hash: str, fn, *args) -> dict:
    """Execute fn only if key not yet consumed. Returns prior result on duplicate."""
    if key in IDEMPOTENCY_STORE:
        prior = IDEMPOTENCY_STORE[key]
        if prior["payload_hash"] == payload_hash:
            return prior["result"]
        else:
            raise ValueError("IDEMPOTENCY_KEY_CONFLICT: same key, different payload")
    result = fn(*args)
    IDEMPOTENCY_STORE[key] = {"payload_hash": payload_hash, "result": result, "created_at": datetime.now(timezone.utc).isoformat()}
    return result

# --- Replay Protection ---
CONSUMED_TOKENS: set[str] = set()

def consume_token(token: str) -> bool:
    """Mark a token as consumed. Returns True if first use."""
    if token in CONSUMED_TOKENS:
        return False
    CONSUMED_TOKENS.add(token)
    return True

# --- Authority Matrix ---
class Role(str, Enum):
    AMJAD_OWNER = "AMJAD_OWNER"
    HERMES_ASSISTANT = "HERMES_ASSISTANT"
    SYSTEM_SERVICE = "SYSTEM_SERVICE"
    RECOVERY_OPERATOR = "RECOVERY_OPERATOR"
    BACKUP_WRITER = "BACKUP_WRITER"

AUTHORITY = {
    "approve_decision": {Role.AMJAD_OWNER},
    "reject_decision": {Role.AMJAD_OWNER},
    "mutate_decision": {Role.AMJAD_OWNER},
    "enable_mutations": {Role.AMJAD_OWNER},
    "set_activation_level": {Role.AMJAD_OWNER},
    "production_restore": {Role.AMJAD_OWNER},
    "delete_backup": {Role.AMJAD_OWNER},
    "rotate_keys": {Role.AMJAD_OWNER},
    "decrypt_backup": {Role.AMJAD_OWNER, Role.RECOVERY_OPERATOR},
    "upload_backup": {Role.AMJAD_OWNER, Role.BACKUP_WRITER},
    "read_status": {Role.AMJAD_OWNER, Role.HERMES_ASSISTANT, Role.SYSTEM_SERVICE, Role.RECOVERY_OPERATOR},
    "prepare_evidence": {Role.AMJAD_OWNER, Role.HERMES_ASSISTANT},
}

def check_authority(role: str, action: str) -> bool:
    try:
        r = Role(role)
    except ValueError:
        return False
    return r in AUTHORITY.get(action, set())

# --- State Machine ---
VALID_TRANSITIONS = {
    "draft": {"proposed"},
    "proposed": {"approved", "rejected"},
    "approved": {"superseded", "closed"},
    "rejected": {"draft"},
    "superseded": set(),
    "closed": set(),
}

def validate_transition(from_state: str, to_state: str) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, set())

# --- Activation Checklist ---
CHECKLIST: dict[str, dict] = {
    "code": {"tests_242": "PASS", "ci_green": "PASS", "governance": "PASS"},
    "security": {"oauth": "PASS", "csrf": "PASS", "toctou": "OPEN", "authority_matrix": "OPEN"},
    "runtime": {"private_vps": "NOT_PROVEN", "systemd": "PASS", "caddy": "PASS"},
    "recovery": {"off_host_backup": "NOT_PROVEN", "restore_exercise": "NOT_PROVEN", "rpo_rto": "NOT_PROVEN"},
    "authority": {"hermes_approval": "PASS", "hermes_recovery": "PASS", "hermes_mutation": "PASS", "amjad_activation": "OPEN"},
}

def activation_readiness() -> str:
    for domain, items in CHECKLIST.items():
        for k, v in items.items():
            if v in ("OPEN", "NOT_PROVEN", "FAIL"):
                return "NOT_READY"
    return "READY_FOR_PRIVATE_VPS_STAGING"