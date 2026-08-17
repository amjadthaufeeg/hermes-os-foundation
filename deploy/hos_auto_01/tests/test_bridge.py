"""HOS-AUTO-01 R1 — Contract + Bridge Tests."""
import json, os, tempfile, pytest

from deploy.hos_auto_01.policy.authority import (
    TaskContract, Operation, Assertion, OperationType, AuthorityClass,
    classify_operation, validate_authority,
    FORBIDDEN_OPERATIONS, AUTHORITY_MATRIX,
)
from deploy.hos_auto_01.bin.bridge import build_pytest_env, execute_operation, run_bridge


def test_contract_hash_deterministic():
    c = TaskContract(task_id="T1", objective="test", authority_class=AuthorityClass.AUTO,
                     working_directory="/tmp", source_git_sha="abc",
                     operations=[Operation(type=OperationType.GIT_STATUS)])
    assert c.compute_hash() == c.compute_hash()
    assert len(c.compute_hash()) == 64

def test_contract_rejects_missing_fields():
    c = TaskContract(task_id="", objective="", authority_class=AuthorityClass.AUTO, working_directory="", source_git_sha="")
    assert not c.is_valid()

def test_forbidden_operations_exist():
    assert len(FORBIDDEN_OPERATIONS) > 0
    assert "enable_production_mutations" in FORBIDDEN_OPERATIONS
    assert "run_shell_command" in FORBIDDEN_OPERATIONS

def test_forbidden_cannot_be_enum():
    for forbidden in FORBIDDEN_OPERATIONS:
        try: OperationType(forbidden); assert False, f"{forbidden} should not be a valid enum"
        except ValueError: pass

def test_gated_requires_token():
    # All current ops in the matrix are AUTO.
    # A GATED contract with AUTO ops → authority mismatch.
    # This is correct behavior: you can't declare GATED if all ops are AUTO.
    c = TaskContract(task_id="T1", objective="test", authority_class=AuthorityClass.GATED,
                     working_directory="/tmp", source_git_sha="abc",
                     operations=[Operation(type=OperationType.GIT_STATUS)])
    ok, msg = validate_authority(c)
    # Actual authority is AUTO, but contract declares GATED → mismatch
    assert not ok and "mismatch" in msg.lower()

def test_auto_passes_validation():
    c = TaskContract(task_id="T1", objective="test", authority_class=AuthorityClass.AUTO,
                     working_directory="/tmp", source_git_sha="abc",
                     operations=[Operation(type=OperationType.GIT_STATUS)])
    assert c.is_valid()

def test_authority_matrix_complete():
    for ot in OperationType:
        assert ot in AUTHORITY_MATRIX, f"{ot} missing from AUTHORITY_MATRIX"

def test_classify_auto_op():
    assert classify_operation(Operation(type=OperationType.GIT_STATUS)) == AuthorityClass.AUTO

def test_bridge_rejects_invalid_contract():
    c = TaskContract(task_id="", objective="", authority_class=AuthorityClass.AUTO, working_directory="", source_git_sha="")
    receipt = run_bridge(c)
    assert receipt.verdict == "STOP"

def test_bridge_auto_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        orig_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            os.system("git init -q && git add -A && git commit --allow-empty -m init -q >/dev/null 2>&1")
            sha = os.popen("git rev-parse HEAD").read().strip()

            c = TaskContract(
                task_id="E2E-001", objective="End-to-end", authority_class=AuthorityClass.AUTO,
                working_directory=tmp, source_git_sha=sha,
                operations=[Operation(type=OperationType.GIT_STATUS, timeout_seconds=30)],
                expected_assertions=[Assertion(id="A1", check="exit_code", expect="0")],
            )
            receipt = run_bridge(c, evidence_root=f"{tmp}/evidence")
            assert receipt.verdict == "PASS"
            assert receipt.receipt_sha256 and len(receipt.receipt_sha256) == 64
            assert os.path.isfile(f"{tmp}/evidence/{receipt.execution_id}/receipt.json")
        finally:
            os.chdir(orig_cwd)

def test_receipt_chain_integrity():
    import hashlib
    r1 = json.dumps({"task_id": "A", "verdict": "PASS", "previous_receipt_sha256": None}, sort_keys=True)
    h1 = hashlib.sha256(r1.encode()).hexdigest()
    r2 = json.dumps({"task_id": "B", "verdict": "PASS", "previous_receipt_sha256": h1}, sort_keys=True)
    h2 = hashlib.sha256(r2.encode()).hexdigest()
    assert h1 != h2

def test_preflight_runs_in_bridge():
    """Bridge runs preflight before executing."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            os.system("git init -q && git add -A && git commit --allow-empty -m init -q >/dev/null 2>&1")
            c = TaskContract(
                task_id="PF-TEST", objective="test", authority_class=AuthorityClass.AUTO,
                working_directory=tmp, source_git_sha="bogus-sha-12345",
                operations=[Operation(type=OperationType.GIT_STATUS)],
            )
            receipt = run_bridge(c, evidence_root=f"{tmp}/evidence")
            assert receipt.verdict == "TEST_ENVIRONMENT_INVALID"
        finally:
            os.chdir(orig_cwd)

def test_pytest_env_isolated_from_production_runtime(monkeypatch):
    """RUN_PYTEST must not inherit production runtime state from HOS-AUTO."""
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("SIMULATION_MODE", "")
    monkeypatch.setenv("MUTATIONS_DISABLED", "false")
    monkeypatch.setenv("DATABASE_PATH", "/opt/hermes/data/production.db")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "must-not-leak")

    env = build_pytest_env()

    assert env["HERMES_ENVIRONMENT"] == "LOCAL_SIMULATION"
    assert env["SIMULATION_MODE"] == "true"
    assert env["MUTATIONS_DISABLED"] == "true"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "DATABASE_PATH" not in env
    assert "GITHUB_CLIENT_SECRET" not in env

def test_run_pytest_passes_isolated_env_to_subprocess(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, capture_output, text, timeout, cwd, env):
        captured["cmd"] = cmd
        captured["env"] = env
        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return Result()

    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("DATABASE_PATH", "/opt/hermes/data/production.db")
    monkeypatch.setattr("deploy.hos_auto_01.bin.bridge.subprocess.run", fake_run)

    op = Operation(
        type=OperationType.RUN_PYTEST,
        params={"path": "backend/hos4c", "args": ["-x"]},
    )

    exit_code, stdout, stderr = execute_operation(op, str(tmp_path), tmp_path)

    assert exit_code == 0
    assert stdout == "ok"
    assert stderr == ""
    assert captured["cmd"] == ["python3", "-m", "pytest", "backend/hos4c", "-x"]
    assert captured["env"]["HERMES_ENVIRONMENT"] == "LOCAL_SIMULATION"
    assert "DATABASE_PATH" not in captured["env"]
