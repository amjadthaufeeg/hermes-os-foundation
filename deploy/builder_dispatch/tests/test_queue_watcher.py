import hashlib
import json
import sys

import pytest

from deploy.builder_dispatch.adapter import DispatchError
from deploy.builder_dispatch.queue_watcher import QueueJob, resolve_job, verify_hos_gate


def gate_contract(contract_relpath="TASK-1.md"):
    return {
        "objective": "Authorize exact builder assignment",
        "working_directory": "/tmp/hos-auto-01-src",
        "source_git_sha": "abcdef1234567",
        "builder_gate": {
            "task_id": "TASK-123",
            "builder": "kimi-k3",
            "repository": "owner/repo",
            "branch": "feature/TASK-123-x",
            "baseline_commit": "abcdef1234567",
            "contract_relpath": contract_relpath,
            "allowed_files": ["src/example.py"],
            "protected_paths": ["main"],
        },
        "operations": [{"type": "git_status", "params": {}, "timeout_seconds": 30}],
        "expected_assertions": [],
        "timeout_seconds": 60,
    }


def contract_hash(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def make_control(tmp_path, contract, *, receipt="receipt-123", verdict="PASS"):
    control = tmp_path / "control"
    completed = control / "tasks" / "completed"
    completed.mkdir(parents=True)
    (completed / "GATE-123.json").write_text(json.dumps({
        "task_id": "GATE-123",
        "status": "COMPLETED",
        "verdict": verdict,
        "authority_class": "AUTO",
        "contract_sha256": contract_hash(contract),
        "evidence_receipts": [receipt],
    }))
    return control


def make_q(contract, *, contract_relpath="TASK-1.md", receipt="receipt-123"):
    return QueueJob(
        "TASK-123", "chatgpt", "kimi-k3", "owner/repo",
        "feature/TASK-123-x", "abcdef1234567", contract_relpath,
        "GATE-123", receipt, contract, 60,
    )


def make_config(tmp_path):
    work = tmp_path / "repo"
    work.mkdir()
    tasks = work / "docs" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "TASK-1.md").write_text("x")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "builders": {"kimi-k3": {"executable": sys.executable, "args": []}},
        "repositories": {"owner/repo": {
            "working_directory": str(work),
            "contract_root": str(tasks),
            "allowed_branch_prefixes": ["feature/"]
        }}
    }))
    cfg.chmod(0o600)
    return work, tasks, cfg


def test_resolve_job_derives_workdir_from_trusted_config(tmp_path):
    work, tasks, cfg = make_config(tmp_path)
    gate = gate_contract()
    control = make_control(tmp_path, gate)
    q = make_q(gate)
    job, _ = resolve_job(q, str(cfg), control_dir=control)
    assert job.working_directory == str(work.resolve())
    assert job.contract_path == str((tasks / "TASK-1.md").resolve())


def test_rejects_contract_traversal(tmp_path):
    _, _, cfg = make_config(tmp_path)
    gate = gate_contract("../../escape.md")
    control = make_control(tmp_path, gate)
    q = make_q(gate, contract_relpath="../../escape.md")
    with pytest.raises(DispatchError, match="escapes"):
        resolve_job(q, str(cfg), control_dir=control)


def test_rejects_missing_hos_gate(tmp_path):
    gate = gate_contract()
    q = make_q(gate)
    empty = tmp_path / "empty-control"
    empty.mkdir()
    with pytest.raises(DispatchError, match="result not found"):
        verify_hos_gate(q, empty)


def test_rejects_wrong_receipt(tmp_path):
    gate = gate_contract()
    control = make_control(tmp_path, gate)
    q = make_q(gate, receipt="wrong")
    with pytest.raises(DispatchError, match="receipt mismatch"):
        verify_hos_gate(q, control)


def test_rejects_tampered_gate_contract(tmp_path):
    gate = gate_contract()
    control = make_control(tmp_path, gate)
    tampered = gate_contract()
    tampered["builder_gate"]["builder"] = "codex"
    q = QueueJob(
        "TASK-123", "chatgpt", "codex", "owner/repo",
        "feature/TASK-123-x", "abcdef1234567", "TASK-1.md",
        "GATE-123", "receipt-123", tampered, 60,
    )
    with pytest.raises(DispatchError, match="contract hash mismatch"):
        verify_hos_gate(q, control)


def test_rejects_failed_hos_gate(tmp_path):
    gate = gate_contract()
    control = make_control(tmp_path, gate, verdict="FAIL")
    q = make_q(gate)
    with pytest.raises(DispatchError, match="did not PASS"):
        verify_hos_gate(q, control)
