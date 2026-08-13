"""HOS-AUTO-02 R2 — Atomic Claim + Idempotency.

Only one Hermes processor may execute a task.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from deploy.hos_auto_02.schema import R2Claim
from deploy.hos_auto_02.transport import git_commit_and_push


PROCESSOR_ID = "hermes-r2-01"
SEEN_NONCES = set()
COMPLETED_TASKS = set()


def create_claim(task_id: str, task_commit_sha: str) -> R2Claim:
    return R2Claim(
        task_id=task_id,
        task_commit_sha=task_commit_sha,
        processor_id=PROCESSOR_ID,
        claimed_at=datetime.now(timezone.utc).isoformat(),
        claim_nonce=str(uuid.uuid4()),
    )


def attempt_claim(task_id: str, task_commit_sha: str) -> tuple[bool, str]:
    """Attempt atomic claim via GitHub commit. Returns (claimed, reason)."""
    claim = create_claim(task_id, task_commit_sha)
    claim_json = json.dumps({
        "task_id": claim.task_id,
        "task_commit_sha": claim.task_commit_sha,
        "processor_id": claim.processor_id,
        "claimed_at": claim.claimed_at,
        "claim_nonce": claim.claim_nonce,
    }, indent=2)

    success, msg, sha = git_commit_and_push(
        [(
            f"claims/{task_id}/claim.json",
            claim_json,
        )],
        f"claim: {task_id} by {PROCESSOR_ID}",
    )

    if success:
        return True, f"Claimed: {sha[:12]}"
    else:
        return False, f"Claim failed (already claimed or push conflict): {msg}"


def is_duplicate_nonce(nonce: str) -> bool:
    """True if nonce has been seen before."""
    if nonce in SEEN_NONCES:
        return True
    SEEN_NONCES.add(nonce)
    return False


def is_duplicate_task(task_id: str) -> bool:
    """True if task_id has already been processed."""
    return task_id in COMPLETED_TASKS


def mark_completed(task_id: str):
    COMPLETED_TASKS.add(task_id)