"""Closure regression tests for retry-safe R2 processing."""
from deploy.hos_auto_02.schema import R2Result
from deploy.hos_auto_02 import watcher_entry


def _result(verdict, warnings=None):
    return R2Result(
        task_id="RETRY-001",
        result_id="res-RETRY-001",
        status="COMPLETED",
        verdict=verdict,
        warnings=list(warnings or []),
    )


def test_first_failed_attempt_is_retryable():
    marked = []
    watcher_entry.finalize_issue_outcome(_result("FAIL"), marked.append)
    assert marked == []


def test_third_failed_attempt_becomes_terminal():
    marked = []
    result = _result("FAIL", ["STOP: 3 identical failures"])
    watcher_entry.finalize_issue_outcome(result, marked.append)
    assert marked == ["RETRY-001"]


def test_environment_failure_can_retry_then_stop(monkeypatch):
    marked = []
    monkeypatch.setattr(
        watcher_entry.watcher, "persistent_record_failure", lambda task_id: True
    )
    result = _result("TEST_ENVIRONMENT_INVALID")
    watcher_entry.finalize_issue_outcome(result, marked.append)
    assert marked == ["RETRY-001"]
    assert "STOP: 3 identical failures" in result.warnings


def test_pass_resets_failures_and_completes(monkeypatch):
    marked = []
    reset = []
    monkeypatch.setattr(
        watcher_entry.watcher, "persistent_reset_failures", reset.append
    )
    watcher_entry.finalize_issue_outcome(_result("PASS"), marked.append)
    assert reset == ["RETRY-001"]
    assert marked == ["RETRY-001"]


def test_transient_or_gated_result_does_not_poison_task():
    for verdict in ("GATED", "RATE_LIMITED", "CLAIM_FAILED", "SOURCE_CHANGED", "REPLAY"):
        marked = []
        watcher_entry.finalize_issue_outcome(_result(verdict), marked.append)
        assert marked == []


def test_duplicate_issue_version_is_retired(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        watcher_entry.watcher,
        "read_issue_task",
        lambda number: {"source_version": "issue:77:abc"},
    )
    monkeypatch.setattr(
        watcher_entry.watcher,
        "persistent_mark_issue_processed",
        lambda number, version: recorded.append((number, version)),
    )
    watcher_entry._mark_current_issue_version_processed(77)
    assert recorded == [(77, "issue:77:abc")]


def test_expired_legacy_file_becomes_terminal():
    marked = []
    watcher_entry.finalize_file_outcome(_result("EXPIRED"), marked.append)
    assert marked == ["RETRY-001"]


def test_invalid_legacy_file_becomes_terminal():
    for verdict in ("MALFORMED", "INVALID", "MAX_DEPTH", "TRANSPORT", "FORBIDDEN", "REPLAY"):
        marked = []
        watcher_entry.finalize_file_outcome(_result(verdict), marked.append)
        assert marked == ["RETRY-001"]


def test_transient_legacy_file_not_completed():
    for verdict in ("GATED", "RATE_LIMITED", "CLAIM_FAILED", "SOURCE_CHANGED"):
        marked = []
        watcher_entry.finalize_file_outcome(_result(verdict), marked.append)
        assert marked == []
