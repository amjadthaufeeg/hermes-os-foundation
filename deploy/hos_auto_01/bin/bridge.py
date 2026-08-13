"""HOS-AUTO-01 — Execution Bridge + Evidence Receipts.

Contract validation → authority classification → preflight →
dispatch to typed executor → assertion evaluation → receipt generation.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from deploy.hos_auto_01.policy.authority import (
    TaskContract, Assertion, OperationType, Operation, AuthorityClass,
    validate_authority, classify_contract,
)
from deploy.hos_auto_01.bin.preflight import run as run_preflight

# ─── Evidence Receipt ────────────────────────────────────────────

@dataclass
class ExecutionReceipt:
    receipt_version: str = "1.0"
    task_id: str = ""
    execution_id: str = ""
    authority_class: str = ""
    contract_sha256: str = ""
    source_git_sha: str = ""
    executor_version: str = "r1a"
    policy_version: str = "r1a"
    environment_fingerprint: str = ""
    authorization_token_id: Optional[str] = None
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    operations_executed: list = field(default_factory=list)
    assertions: list = field(default_factory=list)
    state_change: dict = field(default_factory=lambda: {
        "production_changed": False,
        "production_db_changed": False,
    })
    verdict: str = "PENDING"
    artifact_paths: list = field(default_factory=list)
    previous_receipt_sha256: Optional[str] = None
    receipt_sha256: Optional[str] = None

    def compute_self_hash(self) -> str:
        raw = json.dumps({
            "task_id": self.task_id, "execution_id": self.execution_id,
            "contract_sha256": self.contract_sha256,
            "source_git_sha": self.source_git_sha,
            "verdict": self.verdict, "started_at": self.started_at,
            "finished_at": self.finished_at,
            "assertions": self.assertions,
            "previous_receipt_sha256": self.previous_receipt_sha256,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


# ─── Executor Dispatch (Typed Operations) ────────────────────────

def execute_operation(op, workdir: str, evidence_dir: Path) -> tuple[int, str, str]:
    """Dispatch a typed operation. Returns (exit_code, stdout, stderr)."""
    op_type = op.type
    params = op.params
    timeout = op.timeout_seconds

    if op_type == OperationType.RUN_PYTEST:
        path = params.get("path", ".")
        args = params.get("args", ["-q"])
        cmd = ["python3", "-m", "pytest", path] + args
    elif op_type == OperationType.GIT_STATUS:
        cmd = ["git", "-C", workdir, "status", "--short"]
    elif op_type == OperationType.GIT_DIFF:
        cmd = ["git", "-C", workdir, "diff", params.get("commit_a", "HEAD~1"), params.get("commit_b", "HEAD")]
    elif op_type == OperationType.GIT_LOG:
        n = str(params.get("n", 5))
        cmd = ["git", "-C", workdir, "log", "--oneline", f"-{n}"]
    elif op_type == OperationType.INSPECT_CONTAINER:
        name = params["container_name"]
        fmt = params.get("format", "{{.Names}} {{.Status}}")
        cmd = ["docker", "ps", "--filter", f"name={name}", "--format", fmt]
    elif op_type == OperationType.INSPECT_TIMER:
        name = params["timer_name"]
        cmd = ["systemctl", "list-timers", name, "--no-pager"]
    elif op_type == OperationType.COLLECT_LOGS:
        unit = params["unit"]
        since = params.get("since", "1h")
        cmd = ["journalctl", "-u", unit, "--since", since, "--no-pager"]
    elif op_type == OperationType.HASH_FILES:
        paths = params["paths"]
        cmd = ["sha256sum"] + paths
    elif op_type == OperationType.STAT_FILE:
        path = params["path"]
        fmt = params.get("format", "%a %U:%G")
        cmd = ["stat", "-c", fmt, path]
    elif op_type == OperationType.READ_FILE:
        path = params["path"]
        cmd = ["cat", path]
    elif op_type == OperationType.CREATE_SOURCE_DB:
        path = params["path"]
        decisions = params.get("decisions", 0)
        cmd = ["python3", "-c", f"""
import sqlite3
conn = sqlite3.connect('{path}')
conn.execute('CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, state TEXT, version INTEGER, owner TEXT, project TEXT, created_at TEXT, updated_at TEXT)')
for i in range({decisions}):
    conn.execute('INSERT INTO decisions VALUES (?,?,?,?,?,datetime(\\'now\\'),datetime(\\'now\\'))', (f'DEC-{{i:03d}}', 'AWAITING_AMJAD', 1, 'amjad', 'hermes-os'))
conn.commit()
conn.close()
print('OK')
"""]
    elif op_type == OperationType.ASSERT_HTTP_RESPONSE:
        url = params["url"]
        expected = params["expected_status"]
        cmd = ["python3", "-c", f"""
import urllib.request, urllib.error
try:
    r = urllib.request.urlopen('{url}')
    print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
"""]
    else:
        return (127, "", f"UNKNOWN_OPERATION: {op_type}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd=workdir or None,
        )
        return (result.returncode, result.stdout.strip(), result.stderr.strip())
    except subprocess.TimeoutExpired:
        return (124, "", f"TIMEOUT: {timeout}s")
    except Exception as e:
        return (1, "", str(e))


# ─── Bridge Main ─────────────────────────────────────────────────

def run_bridge(contract: TaskContract, evidence_root: str = "evidence") -> ExecutionReceipt:
    """Execute a validated task contract and produce a receipt."""
    now_utc = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    receipt = ExecutionReceipt(
        task_id=contract.task_id,
        execution_id=f"exec-{contract.task_id}-{int(time.time())}",
        authority_class=contract.authority_class.value,
        contract_sha256=contract.compute_hash(),
        source_git_sha=contract.source_git_sha,
        started_at=now_utc(),
    )

    # Validate contract
    errors = contract.validate()
    if errors:
        receipt.verdict = "STOP"
        receipt.assertions = [{"id": "CONTRACT_VALIDATION", "passed": False, "error": errors}]
        receipt.finished_at = now_utc()
        receipt.receipt_sha256 = receipt.compute_self_hash()
        return receipt

    # Validate authority
    auth_ok, auth_msg = validate_authority(contract)
    if not auth_ok:
        receipt.verdict = "STOP"
        receipt.assertions = [{"id": "AUTHORITY_CHECK", "passed": False, "error": auth_msg}]
        receipt.finished_at = now_utc()
        receipt.receipt_sha256 = receipt.compute_self_hash()
        return receipt

    # Preflight
    pf = run_preflight(contract.source_git_sha)
    receipt.environment_fingerprint = pf.fingerprint or "unknown"
    if not pf.passed:
        receipt.verdict = "TEST_ENVIRONMENT_INVALID"
        receipt.finished_at = now_utc()
        receipt.receipt_sha256 = receipt.compute_self_hash()
        return receipt

    # Evidence directory
    evidence_dir = Path(evidence_root) / receipt.execution_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Execute operations
    all_assertions = []
    all_passed = True
    start = time.time()

    for op in contract.operations:
        exit_code, stdout, stderr = execute_operation(op, contract.working_directory, evidence_dir)
        receipt.operations_executed.append({
            "type": op.type.value, "exit_code": exit_code,
            "stdout_preview": stdout[:500], "stderr_preview": stderr[:500],
        })

        # Write artifacts
        (evidence_dir / f"op-{op.type.value}-stdout.log").write_text(stdout)
        (evidence_dir / f"op-{op.type.value}-stderr.log").write_text(stderr)

        # Evaluate assertions after all operations complete
    for assertion in contract.expected_assertions:
        op_result = receipt.operations_executed[0] if receipt.operations_executed else {}
        exit_code = op_result.get("exit_code", -1)
        stdout = op_result.get("stdout_preview", "")

        if assertion.check == "exit_code":
            assertion.actual = str(exit_code)
            assertion.passed = str(exit_code) == assertion.expect
        elif assertion.check == "stdout_contains":
            assertion.actual = "FOUND" if assertion.expect in stdout else "NOT_FOUND"
            assertion.passed = assertion.expect in stdout
        elif assertion.check == "http_status":
            assertion.actual = str(stdout)
            assertion.passed = str(stdout) == str(assertion.expect)
        else:
            assertion.passed = None

        all_assertions.append({
            "id": assertion.id, "check": assertion.check,
            "expect": assertion.expect, "actual": assertion.actual,
            "passed": assertion.passed,
        })
        if assertion.passed is False:
            all_passed = False

    duration = time.time() - start
    receipt.duration_seconds = round(duration, 3)
    receipt.assertions = all_assertions

    if all_passed:
        receipt.verdict = "PASS"
    else:
        receipt.verdict = "FAIL"

    receipt.finished_at = now_utc()
    receipt.receipt_sha256 = receipt.compute_self_hash()

    # Write receipt
    receipt_path = evidence_dir / "receipt.json"
    receipt_path.write_text(json.dumps({
        k: v for k, v in receipt.__dict__.items()
    }, indent=2, default=str))

    return receipt


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: bridge.py <contract.json> [evidence_root]")
        sys.exit(2)

    contract_path = sys.argv[1]
    evidence_root = sys.argv[2] if len(sys.argv) > 2 else "evidence"

    with open(contract_path) as f:
        data = json.load(f)

    contract = TaskContract(
        task_id=data["task_id"],
        objective=data["objective"],
        authority_class=AuthorityClass(data["authority_class"]),
        working_directory=data["working_directory"],
        source_git_sha=data["source_git_sha"],
        authorization_token_id=data.get("authorization_token_id"),
        operations=[
            Operation(type=OperationType(o["type"]), params=o.get("params", {}), timeout_seconds=o.get("timeout_seconds", 300))
            for o in data["operations"]
        ],
        expected_assertions=[
            Assertion(id=a["id"], check=a["check"], expect=str(a["expect"]))
            for a in data.get("expected_assertions", [])
        ],
        timeout_seconds=data.get("timeout_seconds", 600),
    )

    receipt = run_bridge(contract, evidence_root)

    print(f"VERDICT: {receipt.verdict}")
    print(f"Receipt: {receipt.receipt_sha256}")

    sys.exit(0 if receipt.verdict == "PASS" else 1)


if __name__ == "__main__":
    main()