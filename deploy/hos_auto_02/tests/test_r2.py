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
    assert not record_failure(tid)
    assert not record_failure(tid)
    assert record_failure(tid)

def test_continuations_max():
    parent = "test-parent"
    assert not record_continuation(parent)
    assert not record_continuation(parent)
    assert not record_continuation(parent)
    assert record_continuation(parent)

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


# ─── Catch-up Tests (ChatGPT review findings) ─────────────────────

def test_watcher_no_ssh_in_bridge_invocation():
    from deploy.hos_auto_02.watcher import run_local_bridge
    import inspect
    source = inspect.getsource(run_local_bridge)
    assert 'subprocess.run(["ssh"' not in source.replace(" ", "")
    assert "root@141.136.44.66" not in source

def test_persistent_nonce_survives_call(monkeypatch, tmp_path):
    state_file = tmp_path / "r2-state.json"
    monkeypatch.setenv("R2_STATE_FILE", str(state_file))
    import importlib
    from deploy.hos_auto_02 import watcher
    importlib.reload(watcher)
    test_nonce = "test-persist-" + str(id(dict()))
    assert not watcher.persistent_is_duplicate_nonce(test_nonce)
    assert watcher.persistent_is_duplicate_nonce(test_nonce)

def test_persistent_task_dedup(monkeypatch, tmp_path):
    state_file = tmp_path / "r2-state.json"
    monkeypatch.setenv("R2_STATE_FILE", str(state_file))
    import importlib
    from deploy.hos_auto_02 import watcher
    importlib.reload(watcher)
    tid = "test-dedup-" + str(id(dict()))
    assert not watcher.persistent_is_duplicate_task(tid)
    watcher.persistent_mark_completed(tid)
    assert watcher.persistent_is_duplicate_task(tid)

def test_result_hash_binds_security_fields():
    from deploy.hos_auto_02.schema import R2Result
    r = R2Result(task_id="T", result_id="R", task_commit_sha="abc",
                  contract_sha256="def", status="COMPLETED", verdict="PASS",
                  authority_class="AUTO", evidence_receipts=["r1"],
                  completed_at="2026-01-01T00:00:00Z")
    h1 = r.compute_hash()
    r2 = R2Result(task_id="T", result_id="R", task_commit_sha="DIFFERENT",
                   contract_sha256="def", status="COMPLETED", verdict="PASS",
                   authority_class="AUTO", evidence_receipts=["r1"],
                   completed_at="2026-01-01T00:00:00Z")
    h2 = r2.compute_hash()
    assert h1 != h2


def test_replay_blocked_after_restart(monkeypatch, tmp_path):
    state_file = tmp_path / "r2-state.json"
    monkeypatch.setenv("R2_STATE_FILE", str(state_file))
    import importlib
    from deploy.hos_auto_02 import watcher
    importlib.reload(watcher)
    test_nonce = "replay-test-" + str(id(dict()))
    assert not watcher.persistent_is_duplicate_nonce(test_nonce)
    assert watcher.persistent_is_duplicate_nonce(test_nonce)
    importlib.reload(watcher)
    assert watcher.persistent_is_duplicate_nonce(test_nonce)


def test_transport_no_credential_in_source():
    from deploy.hos_auto_02.transport import DEPLOY_KEY, ISSUES_TOKEN_FILE
    assert "/opt/hermes-auto/creds/" in DEPLOY_KEY
    assert "BEGIN" not in DEPLOY_KEY
    assert ISSUES_TOKEN_FILE.startswith("/opt/hermes-auto/creds/")
    assert "token=" not in ISSUES_TOKEN_FILE.lower()


# ─── GitHub Issue Ingress Tests ────────────────────────────────────

def _issue_task_json(task_id="T-ISSUE-001", nonce="nonce-issue-001"):
    contract = {
        "objective": "Inspect timer",
        "working_directory": "/tmp/hos-auto-01-src",
        "source_git_sha": "source",
        "operations": [{
            "type": "inspect_timer",
            "params": {"timer_name": "hermes-production-snapshot-refresh.timer"},
            "timeout_seconds": 60,
        }],
        "expected_assertions": [],
        "timeout_seconds": 120,
    }
    task = R2Task(
        task_id=task_id,
        created_at="2026-08-14T00:00:00+00:00",
        expires_at="2099-01-01T00:00:00+00:00",
        nonce=nonce,
        contract=contract,
        objective="Inspect timer",
    )
    return json.dumps({
        "task_id": task.task_id,
        "schema_version": task.schema_version,
        "source": "chatgpt",
        "created_at": task.created_at,
        "expires_at": task.expires_at,
        "nonce": task.nonce,
        "depth": 0,
        "authority_suggestion": "AUTO",
        "objective": task.objective,
        "contract": contract,
        "contract_sha256": task.compute_contract_hash(),
    })


def test_list_issue_tasks_filters_prefix_and_author(monkeypatch):
    from deploy.hos_auto_02 import transport
    monkeypatch.setattr(transport, "_github_api_json", lambda path: [
        {"number": 2, "title": "R2-TASK T-2", "body": "{}", "user": {"login": "amjadthaufeeg"}, "updated_at": "u"},
        {"number": 3, "title": "Other", "body": "{}", "user": {"login": "amjadthaufeeg"}, "updated_at": "u"},
        {"number": 4, "title": "R2-TASK EVIL", "body": "{}", "user": {"login": "other"}, "updated_at": "u"},
        {"number": 5, "title": "R2-TASK PR", "body": "{}", "user": {"login": "amjadthaufeeg"}, "updated_at": "u", "pull_request": {}},
    ])
    items = transport.list_issue_tasks()
    assert [i["number"] for i in items] == [2]


def test_read_issue_task_binds_body_hash(monkeypatch):
    import hashlib
    from deploy.hos_auto_02 import transport
    body = _issue_task_json()
    monkeypatch.setattr(transport, "_github_api_json", lambda path: {
        "number": 8,
        "title": "R2-TASK T-ISSUE-001",
        "body": body,
        "user": {"login": "amjadthaufeeg"},
        "updated_at": "2026-08-14T00:00:00Z",
    })
    item = transport.read_issue_task(8)
    expected = hashlib.sha256(body.encode()).hexdigest()
    assert item["body_sha256"] == expected
    assert item["source_version"] == f"issue:8:{expected}"


def test_issue_processing_rechecks_source_version(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("R2_STATE_FILE", str(state_file))
    import importlib
    from deploy.hos_auto_02 import watcher
    importlib.reload(watcher)
    first = {"number": 7, "body": _issue_task_json(), "source_version": "issue:7:a", "body_sha256": "a", "author": "amjadthaufeeg", "updated_at": "1", "title": "R2-TASK T"}
    second = dict(first, source_version="issue:7:b", body_sha256="b")
    seq = iter([first, second])
    monkeypatch.setattr(watcher, "read_issue_task", lambda n: next(seq))
    result = watcher.process_issue_task(7)
    assert result.verdict == "SOURCE_CHANGED"
    assert result.status == "STOPPED"


def test_issue_task_auto_executes_through_local_bridge(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("R2_STATE_FILE", str(state_file))
    import importlib
    from deploy.hos_auto_02 import watcher
    importlib.reload(watcher)
    body = _issue_task_json(task_id="T-ISSUE-OK", nonce="nonce-issue-ok")
    envelope = {"number": 9, "body": body, "source_version": "issue:9:abc", "body_sha256": "abc", "author": "amjadthaufeeg", "updated_at": "1", "title": "R2-TASK T-ISSUE-OK"}
    monkeypatch.setattr(watcher, "read_issue_task", lambda n: envelope)
    monkeypatch.setattr(watcher, "attempt_claim", lambda task_id, source_version: (True, "claimed"))
    monkeypatch.setattr(watcher, "run_local_bridge", lambda task, source_version: {"status": "COMPLETED", "verdict": "PASS", "summary": "ok", "evidence_receipts": ["r"]})
    monkeypatch.setattr(watcher, "check_rate_limit", lambda: True)
    result = watcher.process_issue_task(9)
    assert result.status == "COMPLETED"
    assert result.verdict == "PASS"
    assert result.authority_class == "AUTO"
    assert result.task_commit_sha == "issue:9:abc"
