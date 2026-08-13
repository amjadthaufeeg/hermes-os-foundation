"""HOS-AUTO-02 R2 — Hermes Task Watcher (VPS-deployed, hermes-auto).

Persistent systemd service. Polls hermes-control, validates tasks,
invokes local HOS-AUTO-01 bridge (no SSH), publishes results.

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
from pathlib import Path

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
    check_rate_limit, check_depth, check_ttl, record_failure, reset_failures,
)

from deploy.hos_auto_01.policy.authority import (
    TaskContract, Operation, Assertion, OperationType, AuthorityClass,
    validate_authority, AUTHORITY_MATRIX,
)


POLL_INTERVAL = 30
BRIDGE_PATH = "/opt/hermes-auto/bin/bridge.py"
BRIDGE_PYTHON = "/opt/hermes-auto/venv/bin/python3"
EVIDENCE_ROOT = "/opt/hermes-auto/evidence"
CONTRACT_DIR = "/opt/hermes-auto/contracts"
STATE_FILE = os.environ.get("R2_STATE_FILE", "/opt/hermes-auto/state/r2-state.json")

# ─── Persistent State ──────────────────────────────────────────────

def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"seen_nonces": [], "completed_tasks": [], "failure_counts": {}}

def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

_state = load_state()

def persistent_is_duplicate_nonce(nonce: str) -> bool:
    if nonce in _state["seen_nonces"]:
        return True
    _state["seen_nonces"].append(nonce)
    _state["seen_nonces"] = _state["seen_nonces"][-1000:]  # cap at 1000
    save_state(_state)
    return False

def persistent_is_duplicate_task(task_id: str) -> bool:
    return task_id in _state.get("completed_tasks", [])

def persistent_mark_completed(task_id: str):
    _state.setdefault("completed_tasks", []).append(task_id)
    _state["completed_tasks"] = _state["completed_tasks"][-5000:]
    save_state(_state)

def persistent_record_failure(task_id: str) -> bool:
    _state.setdefault("failure_counts", {})
    _state["failure_counts"][task_id] = _state["failure_counts"].get(task_id, 0) + 1
    save_state(_state)
    return _state["failure_counts"][task_id] >= 3

def persistent_reset_failures(task_id: str):
    _state.setdefault("failure_counts", {})
    _state["failure_counts"].pop(task_id, None)
    save_state(_state)


# ─── Authority Classification ──────────────────────────────────────

def classify_authority(task: R2Task) -> AuthorityClass:
    if task.depth > 3:
        return AuthorityClass.FORBIDDEN
    suggestion = task.authority_suggestion.upper()
    if suggestion == "FORBIDDEN": return AuthorityClass.FORBIDDEN
    if suggestion == "GATED": return AuthorityClass.GATED
    for op in task.contract.get("operations", []):
        op_type = OperationType(op["type"])
        if AUTHORITY_MATRIX.get(op_type) == AuthorityClass.GATED:
            return AuthorityClass.GATED
    return AuthorityClass.AUTO


# ─── Local Bridge Invocation (no SSH) ──────────────────────────────

def run_local_bridge(task: R2Task, contract_sha: str) -> dict:
    """Invoke the locally installed HOS-AUTO-01 bridge. No SSH, no root."""
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
        objective=task.objective,
        authority_class=classify_authority(task),
        working_directory=task.contract.get("working_directory", "/tmp/hos-auto-01-src"),
        source_git_sha=contract_sha,
        operations=ops,
        expected_assertions=assertions,
        timeout_seconds=task.contract.get("timeout_seconds", 600),
    )

    ok, msg = validate_authority(contract)
    if not ok:
        return {"status": "REJECTED", "verdict": "FAIL", "summary": msg,
                "requires_human_decision": contract.authority_class == AuthorityClass.GATED}

    # Write contract to temp file under approved directory
    os.makedirs(CONTRACT_DIR, exist_ok=True)
    contract_path = os.path.join(CONTRACT_DIR, f"contract-{uuid.uuid4().hex}.json")
    contract_dict = {
        "task_id": contract.task_id, "objective": contract.objective,
        "authority_class": contract.authority_class.value,
        "working_directory": contract.working_directory,
        "source_git_sha": contract.source_git_sha,
        "operations": [{"type": o.type.value, "params": o.params, "timeout_seconds": o.timeout_seconds} for o in ops],
        "expected_assertions": [{"id": a.id, "check": a.check, "expect": a.expect} for a in assertions],
        "timeout_seconds": contract.timeout_seconds,
    }
    with open(contract_path, "w") as f:
        json.dump(contract_dict, f)
    os.chmod(contract_path, 0o600)

    try:
        env = os.environ.copy()
        env["PATH"] = "/opt/hermes-auto/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        env["PYTHONPATH"] = "/opt/hermes-auto"
        result = subprocess.run(
            [BRIDGE_PYTHON, BRIDGE_PATH, contract_path, EVIDENCE_ROOT],
            capture_output=True, text=True, timeout=120, env=env,
        )

        receipt_sha = None
        verdict = "UNKNOWN"
        for line in result.stdout.split("\n"):
            if "Receipt:" in line: receipt_sha = line.split()[-1].strip()
            if "VERDICT:" in line: verdict = line.split()[-1].strip()

        return {
            "status": "COMPLETED", "verdict": verdict,
            "summary": result.stdout.strip()[-200:],
            "evidence_receipts": [receipt_sha] if receipt_sha else [],
        }
    except subprocess.TimeoutExpired:
        return {"status": "STOPPED", "verdict": "TIMEOUT", "summary": "Bridge timeout"}
    except Exception as e:
        return {"status": "STOPPED", "verdict": "ERROR", "summary": str(e)}
    finally:
        try: os.unlink(contract_path)
        except OSError: pass


# ─── Task Processing ───────────────────────────────────────────────

def process_task(filename: str) -> R2Result:
    task_id = filename.replace(".json", "")
    result = R2Result(task_id=task_id, result_id=f"res-{task_id}")

    if persistent_is_duplicate_task(task_id):
        result.status = "SKIPPED"; result.verdict = "DUPLICATE"
        result.summary = "Already processed"; return result

    content = read_task_file(filename)
    if not content:
        result.status = "STOPPED"; result.verdict = "ERROR"
        result.summary = "Cannot read task file"; return result

    try: task_data = json.loads(content)
    except json.JSONDecodeError:
        result.status = "REJECTED"; result.verdict = "MALFORMED"; return result

    task = R2Task.from_json(task_data)
    errors = task.validate()
    if errors:
        result.status = "REJECTED"; result.verdict = "INVALID"
        result.summary = "; ".join(errors); return result

    if not check_ttl(task.expires_at):
        result.status = "EXPIRED"; result.verdict = "EXPIRED"
        result.summary = "TTL expired"; return result
    if not check_depth(task.depth):
        result.status = "REJECTED"; result.verdict = "MAX_DEPTH"; return result
    if persistent_is_duplicate_nonce(task.nonce):
        result.status = "REJECTED"; result.verdict = "REPLAY"; return result
    if not check_rate_limit():
        result.status = "STOPPED"; result.verdict = "RATE_LIMITED"; return result

    task_sha = get_task_commit_sha() or "unknown"
    ok, msg = validate_transport("amjadthaufeeg/hermes-control", "main", f"tasks/inbox/{filename}")
    if not ok:
        result.status = "REJECTED"; result.verdict = "TRANSPORT"
        result.summary = msg; return result

    claimed, claim_msg = attempt_claim(task_id, task_sha)
    if not claimed:
        result.status = "SKIPPED"; result.verdict = "CLAIM_FAILED"
        result.summary = claim_msg; return result

    authority = classify_authority(task)
    result.authority_class = authority.value

    if authority == AuthorityClass.FORBIDDEN:
        result.status = "REJECTED"; result.verdict = "FORBIDDEN"; return result
    if authority == AuthorityClass.GATED:
        result.status = "STOPPED"; result.verdict = "GATED"
        result.requires_human_decision = True
        result.summary = "GATED — requires Amjad authorization"; return result

    exec_result = run_local_bridge(task, task_sha)
    result.status = exec_result.get("status", result.status)
    result.verdict = exec_result.get("verdict", result.verdict)
    result.summary = exec_result.get("summary", "")
    result.evidence_receipts = exec_result.get("evidence_receipts", [])
    result.task_commit_sha = task_sha
    result.contract_sha256 = task.contract_sha256 or ""

    if result.verdict == "FAIL":
        if persistent_record_failure(task_id):
            result.warnings.append("STOP: 3 identical failures")
    else:
        persistent_reset_failures(task_id)

    persistent_mark_completed(task_id)
    return result


def publish_result(result: R2Result):
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
        print(f"Published: {result.task_id} (sha:{sha[:12]})")


def watch_loop():
    print("HOS-AUTO-02 R2 watcher started (local bridge)")
    while True:
        try:
            ok, msg = git_pull()
            tasks = list_inbox_tasks()
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