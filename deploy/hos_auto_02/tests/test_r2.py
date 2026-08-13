"""HOS-AUTO-02 R2 — Tests.

Schema, transport, authority, loop guard, claim.
"""
import json, os, tempfile, time, pytest

from deploy.hos_auto_02.schema import (
    R2Task, R2Result, R2Claim, validate_transport,
    SCHEMA_VERSION, TRANSPORT_REPO, TRANSPORT_BRANCH, INBOX_PATH,
)
from deploy.hos_auto_02.loop_guard import (
    check_rate_limit, check_depth, check_ttl,
    record_failure, reset_failures, record_continuation,
)
from deploy.hos_auto_02.claim import (
    is_duplicate_nonce, is_duplicate_task, mark_completed,
)


# ─── Schema Tests ──────────────────────────────────────────────────

def test_task_schema_valid():
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc123", contract={"ops": []},
    )
    task.contract_sha256 = task.compute_contract_hash()
    assert task.is_valid()

def test_task_schema_missing_fields():
    task = R2Task(task_id="", created_at="", nonce="", contract={})
    assert not task.is_valid()

def test_contract_hash_mismatch():
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", contract={"ops": []}, contract_sha256="bogus",
    )
    assert "mismatch" in str(task.validate()).lower()

def test_depth_exceeded():
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", contract={"ops": []}, depth=5,
    )
    task.contract_sha256 = task.compute_contract_hash()
    assert not task.is_valid()

def test_task_expired():
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", contract={"ops": []}, expires_at="2020-01-01T00:00:00Z",
    )
    assert task.is_expired()

def test_task_not_expired():
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", contract={"ops": []}, expires_at="2099-01-01T00:00:00Z",
    )
    assert not task.is_expired()

def test_result_hash():
    result = R2Result(
        task_id="T-001", result_id="R-001",
        task_commit_sha="abc", contract_sha256="def",
        status="COMPLETED", verdict="PASS",
    )
    h = result.compute_hash()
    assert len(h) == 64
    assert result.compute_hash() == result.compute_hash()

def test_validate_transport_rejects_wrong_repo():
    ok, msg = validate_transport("wrong/repo", "main", "tasks/inbox/x.json")
    assert not ok and "repo" in msg.lower()

def test_validate_transport_rejects_wrong_branch():
    ok, msg = validate_transport(TRANSPORT_REPO, "dev", "tasks/inbox/x.json")
    assert not ok and "branch" in msg.lower()

def test_validate_transport_rejects_wrong_path():
    ok, msg = validate_transport(TRANSPORT_REPO, TRANSPORT_BRANCH, "other/x.json")
    assert not ok and "path" in msg.lower()

def test_validate_transport_accepts_valid():
    ok, msg = validate_transport(TRANSPORT_REPO, TRANSPORT_BRANCH, "tasks/inbox/T-001.json")
    assert ok


# ─── Loop Guard Tests ──────────────────────────────────────────────

def test_depth_valid():
    assert check_depth(0)
    assert check_depth(3)
    assert not check_depth(4)

def test_ttl_future():
    assert check_ttl("2099-01-01T00:00:00Z")

def test_ttl_past():
    assert not check_ttl("2020-01-01T00:00:00Z")

def test_ttl_none():
    assert check_ttl("")

def test_failure_stop_after_3():
    tid = "test-fail"
    reset_failures(tid)
    assert not record_failure(tid)  # 1
    assert not record_failure(tid)  # 2
    assert record_failure(tid)      # 3 → STOP

def test_continuations_max():
    parent = "test-parent"
    assert not record_continuation(parent)
    assert not record_continuation(parent)
    assert not record_continuation(parent)
    assert record_continuation(parent)  # 4th → STOP

def test_rate_limit():
    from deploy.hos_auto_02.loop_guard import _timestamps, RATE_LIMIT_MAX
    _timestamps.clear()
    for _ in range(RATE_LIMIT_MAX):
        assert check_rate_limit()
    assert not check_rate_limit()


# ─── Claim / Idempotency Tests ─────────────────────────────────────

def test_duplicate_nonce():
    nonce = "test-nonce-unique"
    assert not is_duplicate_nonce(nonce)
    assert is_duplicate_nonce(nonce)

def test_duplicate_task():
    tid = "test-task-id"
    assert not is_duplicate_task(tid)
    mark_completed(tid)
    assert is_duplicate_task(tid)


# ─── Authority Classification Tests ────────────────────────────────

def test_classify_auto():
    from deploy.hos_auto_02.watcher import classify_authority
    from deploy.hos_auto_01.policy.authority import AuthorityClass
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", authority_suggestion="AUTO",
        contract={"operations": [{"type": "git_status", "params": {}}]},
    )
    assert classify_authority(task) == AuthorityClass.AUTO

def test_classify_forbidden_suggestion():
    from deploy.hos_auto_02.watcher import classify_authority
    from deploy.hos_auto_01.policy.authority import AuthorityClass
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", authority_suggestion="FORBIDDEN",
        contract={"operations": []},
    )
    assert classify_authority(task) == AuthorityClass.FORBIDDEN

def test_classify_gated_suggestion():
    from deploy.hos_auto_02.watcher import classify_authority
    from deploy.hos_auto_01.policy.authority import AuthorityClass
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", authority_suggestion="GATED",
        contract={"operations": []},
    )
    assert classify_authority(task) == AuthorityClass.GATED

def test_classify_depth_exceeded():
    from deploy.hos_auto_02.watcher import classify_authority
    from deploy.hos_auto_01.policy.authority import AuthorityClass
    task = R2Task(
        task_id="T-001", created_at="2026-08-13T17:00:00Z",
        nonce="abc", authority_suggestion="AUTO", depth=5,
        contract={"operations": []},
    )
    assert classify_authority(task) == AuthorityClass.FORBIDDEN