"""Regression tests for R2 transport identity vs execution Git SHA separation."""

from deploy.hos_auto_02.schema import R2Task
from deploy.hos_auto_01.policy.authority import AuthorityClass


def test_run_local_bridge_uses_contract_git_sha_not_transport_identity(monkeypatch):
    from deploy.hos_auto_02 import watcher

    captured = {}

    class FakeContract:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.authority_class = kwargs["authority_class"]

    monkeypatch.setattr(watcher, "TaskContract", FakeContract)
    monkeypatch.setattr(watcher, "validate_authority", lambda contract: (False, "stop-after-capture"))

    task = R2Task(
        task_id="T-SHA-SEPARATION",
        created_at="2026-08-16T00:00:00+00:00",
        expires_at="2099-01-01T00:00:00+00:00",
        nonce="nonce-sha-separation",
        objective="Inspect timer",
        authority_suggestion="AUTO",
        contract={
            "objective": "Inspect timer",
            "working_directory": "/tmp/hos-auto-01-src",
            "source_git_sha": "git-sha-123",
            "operations": [
                {
                    "type": "inspect_timer",
                    "params": {"timer_name": "hermes-production-snapshot-refresh.timer"},
                    "timeout_seconds": 60,
                }
            ],
            "expected_assertions": [],
            "timeout_seconds": 120,
        },
    )

    result = watcher.run_local_bridge(task, "issue:99:bodyhash")

    assert captured["source_git_sha"] == "git-sha-123"
    assert captured["source_git_sha"] != "issue:99:bodyhash"
    assert captured["authority_class"] == AuthorityClass.AUTO
    assert result["status"] == "REJECTED"
    assert result["summary"] == "stop-after-capture"
