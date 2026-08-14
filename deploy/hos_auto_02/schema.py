"""HOS-AUTO-02 R2 — Task, Claim, and Result Schemas.

Strict machine-readable schemas for GitHub transport.
All task content is untrusted data; only validated structured fields
influence execution.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


SCHEMA_VERSION = "1.0"
TRANSPORT_REPO = "amjadthaufeeg/hermes-control"
TRANSPORT_BRANCH = "main"
INBOX_PATH = "tasks/inbox/"


class TaskStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    CLASSIFIED = "CLASSIFIED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class R2Task:
    task_id: str
    schema_version: str = SCHEMA_VERSION
    source: str = "chatgpt"
    created_at: str = ""
    expires_at: str = ""
    nonce: str = ""
    correlation_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    depth: int = 0
    authority_suggestion: str = "AUTO"
    contract: dict = field(default_factory=dict)
    contract_sha256: Optional[str] = None
    objective: str = ""

    def compute_contract_hash(self) -> str:
        raw = json.dumps(self.contract, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def from_json(cls, data: dict) -> "R2Task":
        task = cls(
            task_id=data.get("task_id", ""),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            source=data.get("source", "chatgpt"),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at", ""),
            nonce=data.get("nonce", ""),
            correlation_id=data.get("correlation_id"),
            parent_task_id=data.get("parent_task_id"),
            depth=data.get("depth", 0),
            authority_suggestion=data.get("authority_suggestion", "AUTO"),
            contract=data.get("contract", {}),
            objective=data.get("objective", ""),
        )
        task.contract_sha256 = task.compute_contract_hash()
        return task

    def validate(self) -> list[str]:
        errors = []
        if not self.task_id: errors.append("task_id required")
        if not self.created_at: errors.append("created_at required")
        if not self.nonce: errors.append("nonce required")
        if not self.contract: errors.append("contract required")
        if not self.contract_sha256: errors.append("contract_sha256 required")
        if self.schema_version != SCHEMA_VERSION:
            errors.append(f"schema_version {self.schema_version} != {SCHEMA_VERSION}")
        # NOTE: contract_sha256 is Hermes-authoritative (computed in from_json).
        # The ChatGPT-provided value is advisory and may use a different
        # canonicalization; the immutable binding is the git commit SHA.
        if self.depth > 3:
            errors.append(f"max depth exceeded: {self.depth}")
        if self.source not in ("chatgpt", "hermes", "amjad"):
            errors.append(f"unknown source: {self.source}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > expires
        except (ValueError, TypeError):
            return True


@dataclass
class R2Claim:
    task_id: str
    task_commit_sha: str
    processor_id: str
    claimed_at: str = ""
    claim_nonce: str = ""


@dataclass
class R2Result:
    task_id: str
    result_id: str
    task_commit_sha: str = ""
    contract_sha256: str = ""
    status: str = "COMPLETED"
    verdict: str = "PASS"
    authority_class: str = "AUTO"
    summary: str = ""
    evidence_receipts: list = field(default_factory=list)
    artifact_refs: list = field(default_factory=list)
    completed_at: str = ""
    result_sha256: Optional[str] = None
    requires_human_decision: bool = False
    next_action: str = "none"
    warnings: list = field(default_factory=list)

    def compute_hash(self) -> str:
        raw = json.dumps({
            "task_id": self.task_id, "result_id": self.result_id,
            "task_commit_sha": self.task_commit_sha,
            "contract_sha256": self.contract_sha256,
            "status": self.status, "verdict": self.verdict,
            "evidence_receipts": self.evidence_receipts,
            "completed_at": self.completed_at,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


def validate_transport(repo: str, branch: str, path: str) -> tuple[bool, str]:
    """Validate that the task originates from the approved transport."""
    if repo != TRANSPORT_REPO:
        return False, f"Rejected: wrong repo '{repo}', expected '{TRANSPORT_REPO}'"
    if branch != TRANSPORT_BRANCH:
        return False, f"Rejected: wrong branch '{branch}', expected '{TRANSPORT_BRANCH}'"
    if not path.startswith(INBOX_PATH):
        return False, f"Rejected: wrong path '{path}', expected '{INBOX_PATH}...'"
    return True, "Transport valid"