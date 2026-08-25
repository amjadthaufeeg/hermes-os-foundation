import json
import sys

import pytest

from deploy.builder_dispatch.adapter import DispatchError
from deploy.builder_dispatch.queue_watcher import QueueJob, resolve_job


def test_resolve_job_derives_workdir_from_trusted_config(tmp_path):
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
    q = QueueJob(
        "TASK-123", "chatgpt", "kimi-k3", "owner/repo",
        "feature/TASK-123-x", "abcdef1234567", "TASK-1.md", 60,
    )
    job, _ = resolve_job(q, str(cfg))
    assert job.working_directory == str(work.resolve())
    assert job.contract_path == str((tasks / "TASK-1.md").resolve())


def test_rejects_contract_traversal(tmp_path):
    work = tmp_path / "repo"
    work.mkdir()
    tasks = work / "docs" / "tasks"
    tasks.mkdir(parents=True)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "builders": {"kimi-k3": {"executable": sys.executable, "args": []}},
        "repositories": {"owner/repo": {
            "working_directory": str(work),
            "contract_root": str(tasks)
        }}
    }))
    cfg.chmod(0o600)
    q = QueueJob(
        "TASK-123", "chatgpt", "kimi-k3", "owner/repo",
        "feature/TASK-123-x", "abcdef1234567", "../../escape.md", 60,
    )
    with pytest.raises(DispatchError):
        resolve_job(q, str(cfg))
