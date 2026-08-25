import json
import sys
from pathlib import Path

import pytest

from deploy.builder_dispatch.adapter import (
    BuilderJob,
    BuilderSpec,
    DispatchError,
    dispatch,
    load_config,
)


def make_job(tmp_path, builder="kimi-k3", branch="feature/TASK-123-demo"):
    work = tmp_path / "repo"
    work.mkdir()
    contract = tmp_path / "contract.md"
    contract.write_text("immutable")
    return BuilderJob(
        task_id="TASK-123",
        builder=builder,
        repository="owner/repo",
        working_directory=str(work),
        branch=branch,
        baseline_commit="abcdef1234567",
        contract_path=str(contract),
        timeout_seconds=60,
    )


def test_rejects_protected_branch(tmp_path):
    job = make_job(tmp_path, branch="main")
    assert "protected or empty branch" in job.validate()


def test_rejects_unknown_builder(tmp_path):
    job = make_job(tmp_path, builder="other")
    assert "builder must be kimi-k3 or codex" in job.validate()


def test_dispatch_executes_fixed_argv_without_shell(tmp_path):
    job = make_job(tmp_path)
    code = "import json,sys; d=json.load(open(sys.argv[1])); print(d['task_id'])"
    spec = BuilderSpec(executable=sys.executable, args=("-c", code, "{job_file}"))
    result = dispatch(job, spec, state_dir=str(tmp_path / "state"))
    assert result["status"] == "COMPLETED"
    assert result["exit_code"] == 0
    assert "TASK-123" in result["stdout"]


def test_config_requires_absolute_executable(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"builders": {"kimi-k3": {"executable": "python", "args": []}}}))
    with pytest.raises(DispatchError):
        load_config(str(cfg), enforce_permissions=False)
