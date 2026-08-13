"""HOS-AUTO-02 R2 — Hermes Task Watcher.

Polls hermes-control/tasks/inbox/, validates, claims, executes via
HOS-AUTO-01 bridge, publishes results.

ChatGPT task → detect → validate → classify → claim → execute → result → GitHub.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

from deploy.hos_auto_02.schema import (
    R2Task, R2Result, validate_transport,
)
from deploy.hos_auto_02.transport import (
    git_pull, git_commit_and_push, list_inbox_tasks,
    read_task_file, get_task_commit_sha,
)
from deploy.hos_auto_02.claim import (
    attempt_claim, is_duplicate_nonce, is_duplicate_task, mark_completed,
)
from deploy.hos_auto_02.loop_guard import (
    check_rate_limit, check_depth, check_ttl, record_failure,
)

from deploy.hos_auto_01.policy.authority import (
    TaskContract, Operation, Assertion, OperationType, AuthorityClass,
    validate_authority,
)


POLL_INTERVAL = 30
BRIDGE_PATH = "/opt/hermes-auto/bin/bridge.py"
BRIDGE_PYTHON = "/opt/hermes-auto/venv/bin/python3"
EVIDENCE_ROOT = "/opt/hermes-auto/evidence"


def classify_authority(task: R2Task) -> AuthorityClass:
    """Independent authority classification."""
    if task.depth > 3:
        return AuthorityClass.FORBIDDEN
    suggestion = task.authority_suggestion.upper()
    if suggestion == "FORBIDDEN":
        return AuthorityClass.FORBIDDEN
    if suggestion == "GATED":
        return AuthorityClass.GATED
    # For AUTO: verify against authority matrix
    ops = task.contract.get("operations", [])
    for op in ops:
        op_type = OperationType(op["type"])
        from deploy.hos_auto_01.policy.authority import AUTHORITY_MATRIX
        if AUTHORITY_MATRIX.get(op_type) == AuthorityClass.GATED:
            return AuthorityClass.GATED
    return AuthorityClass.AUTO


def run_hos_auto_01(task: R2Task) -> dict:
    """Execute task contract via HOS-AUTO-01 bridge. Returns result dict."""
    # Build contract
    ops = [
        Operation(
            type=OperationType(o["type"]),
            params=o.get("params", {}),
            timeout_seconds=o.get("timeout_seconds", 300),
        )
        for o in task.contract.get("operations", [])
    ]
    assertions = [
        Assertion(id=a["id"], check=a["check"], expect=str(a["expect"]))
        for a in task.contract.get("expected_assertions", [])
    ]

    contract = TaskContract(
        task_id=task.task_id,
        objective=task.objective or task.contract.get("objective", ""),
        authority_class=classify_authority(task),
        working_directory=task.contract.get("working_directory", "/tmp/hos-auto-01-src"),
        source_git_sha=task.contract.get("source_git_sha", get_task_commit_sha() or "unknown"),
        operations=ops,
        expected_assertions=assertions,
        timeout_seconds=task.contract.get("timeout_seconds", 600),
    )

    # Validate authority
    ok, msg = validate_authority(contract)
    if not ok:
        return {"status": "REJECTED", "verdict": "FAIL", "summary": msg,
                "requires_human_decision": contract.authority_class == AuthorityClass.GATED}

    # Write contract to temp file
    contract_dict = {
        "task_id": contract.task_id,
        "objective": contract.objective,
        "authority_class": contract.authority_class.value,
        "working_directory": contract.working_directory,
        "source_git_sha": contract.source_git_sha,
        "operations": [{"type": o.type.value, "params": o.params, "timeout_seconds": o.timeout_seconds} for o in ops],
        "expected_assertions": [{"id": a.id, "check": a.check, "expect": a.expect} for a in assertions],
        "timeout_seconds": contract.timeout_seconds,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(contract_dict, f)
        contract_path = f.name

    # Run bridge on VPS via SSH
    try:
        cmd = (
            f"cd /tmp/hos-auto-01-src && "
            f"sudo -u hermes-auto env "
            f"PATH=/opt/hermes-auto/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "
            f"PYTHONPATH=/opt/hermes-auto "
            f"/opt/hermes-auto/venv/bin/python3 {BRIDGE_PATH} {contract_path} {EVIDENCE_ROOT}"
        )
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=15", "root@141.136.44.66", cmd],
            capture_output=True, text=True, timeout=120,
        )

        # Read receipt
        receipt_sha = None
        for line in result.stdout.split("\n"):
            if "Receipt:" in line:
                receipt_sha = line.split()[-1].strip()
            if "VERDICT:" in line:
                verdict = line.split()[-1].strip()

        summary = result.stdout.strip().split("\n")[-3:] if result.stdout else [result.stderr[:200]]

        if result.returncode == 0:
            return {
                "status": "COMPLETED", "verdict": "PASS",
                "summary": "\n".join(summary),
                "evidence_receipts": [receipt_sha] if receipt_sha else [],
            }
        else:
            return {
                "status": "COMPLETED", "verdict": "FAIL",
                "summary": "\n".join(summary),
                "evidence_receipts": [receipt_sha] if receipt_sha else [],
            }
    except subprocess.TimeoutExpired:
        return {"status": "STOPPED", "verdict": "TIMEOUT", "summary": "Bridge execution timed out"}
    except Exception as e:
        return {"status": "STOPPED", "verdict": "ERROR", "summary": str(e)}
    finally:
        os.unlink(contract_path)


def process_task(filename: str) -> R2Result:
    """Process a single task from inbox. Returns result."""
    task_id = filename.replace(".json", "")
    result = R2Result(task_id=task_id, result_id=f"res-{task_id}")

    # Check duplicate
    if is_duplicate_task(task_id):
        result.status = "SKIPPED"; result.verdict = "DUPLICATE"
        result.summary = "Task already processed"
        return result

    # Read task
    content = read_task_file(filename)
    if not content:
        result.status = "STOPPED"; result.verdict = "ERROR"
        result.summary = "Cannot read task file"
        return result

    try:
        task_data = json.loads(content)
    except json.JSONDecodeError:
        result.status = "REJECTED"; result.verdict = "MALFORMED"
        result.summary = "Invalid JSON"
        return result

    task = R2Task.from_json(task_data)

    # Validate
    errors = task.validate()
    if errors:
        result.status = "REJECTED"; result.verdict = "INVALID"
        result.summary = "; ".join(errors)
        return result

    # TTL
    if not check_ttl(task.expires_at):
        result.status = "EXPIRED"; result.verdict = "EXPIRED"
        result.summary = f"TTL expired: {task.expires_at}"
        return result

    # Depth
    if not check_depth(task.depth):
        result.status = "REJECTED"; result.verdict = "MAX_DEPTH"
        result.summary = f"Depth {task.depth} exceeds max {check_depth.__code__.co_consts}"
        return result

    # Nonce
    if is_duplicate_nonce(task.nonce):
        result.status = "REJECTED"; result.verdict = "REPLAY"
        result.summary = "Duplicate nonce"
        return result

    # Rate limit
    if not check_rate_limit():
        result.status = "STOPPED"; result.verdict = "RATE_LIMITED"
        result.summary = "Rate limit exceeded"
        return result

    # Transport validation
    task_commit_sha = get_task_commit_sha() or "unknown"
    ok, msg = validate_transport(
        "amjadthaufeeg/hermes-control", "main",
        f"tasks/inbox/{filename}",
    )
    if not ok:
        result.status = "REJECTED"; result.verdict = "TRANSPORT"
        result.summary = msg
        return result

    # Claim
    claimed, claim_msg = attempt_claim(task_id, task_commit_sha)
    if not claimed:
        result.status = "SKIPPED"; result.verdict = "CLAIM_FAILED"
        result.summary = claim_msg
        return result

    # Classify authority
    authority = classify_authority(task)
    result.authority_class = authority.value

    if authority == AuthorityClass.FORBIDDEN:
        result.status = "REJECTED"; result.verdict = "FORBIDDEN"
        result.summary = "FORBIDDEN authority"
        return result

    if authority == AuthorityClass.GATED:
        result.status = "STOPPED"; result.verdict = "GATED"
        result.requires_human_decision = True
        result.summary = "GATED — requires Amjad authorization"
        return result

    # Execute
    exec_result = run_hos_auto_01(task)
    result.status = exec_result.get("status", result.status)
    result.verdict = exec_result.get("verdict", result.verdict)
    result.summary = exec_result.get("summary", result.summary)
    result.evidence_receipts = exec_result.get("evidence_receipts", [])
    result.task_commit_sha = task_commit_sha
    result.contract_sha256 = task.contract_sha256 or ""

    if result.verdict == "FAIL":
        stop = record_failure(task_id)
        if stop:
            result.warnings.append("STOP: 3 identical failures")
    else:
        from deploy.hos_auto_02.loop_guard import reset_failures
        reset_failures(task_id)

    mark_completed(task_id)
    return result


def publish_result(result: R2Result):
    """Publish structured result to hermes-control."""
    result.completed_at = datetime.now(timezone.utc).isoformat()
    result.result_sha256 = result.compute_hash()
    result_json = json.dumps({
        "task_id": result.task_id, "result_id": result.result_id,
        "task_commit_sha": result.task_commit_sha,
        "contract_sha256": result.contract_sha256,
        "status": result.status, "verdict": result.verdict,
        "authority_class": result.authority_class,
        "summary": result.summary,
        "evidence_receipts": result.evidence_receipts,
        "artifact_refs": result.artifact_refs,
        "completed_at": result.completed_at,
        "result_sha256": result.result_sha256,
        "requires_human_decision": result.requires_human_decision,
        "next_action": result.next_action,
        "warnings": result.warnings,
    }, indent=2)

    ok, msg, sha = git_commit_and_push(
        [(f"tasks/completed/{result.task_id}.json", result_json)],
        f"completed: {result.task_id} verdict={result.verdict}",
    )
    if ok:
        print(f"Published: {result.task_id} → completed/ (sha:{sha[:12]})")
    else:
        print(f"Publish failed: {msg}")


def watch_loop():
    """Main watcher loop. Polls inbox, processes tasks, publishes results."""
    print("HOS-AUTO-02 R2 watcher started")
    while True:
        try:
            ok, msg = git_pull()
            if not ok:
                print(f"git pull: {msg}")

            tasks = list_inbox_tasks()
            if tasks:
                print(f"Inbox: {len(tasks)} tasks")

            for filename in tasks:
                print(f"Processing: {filename}")
                result = process_task(filename)
                publish_result(result)
                print(f"  → {result.status} {result.verdict}: {result.summary[:80]}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Watcher error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch_loop()