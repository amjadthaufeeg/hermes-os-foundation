"""HOS-AUTO-02 R2 — Hermes Task Watcher (VPS-deployed, hermes-auto).

Persistent systemd service. Polls two authenticated ingress channels:
1) private hermes-control git inbox (legacy/direct file path), and
2) private hermes-control GitHub Issues with title prefix ``R2-TASK ``.

Every task is validated, independently authority-classified, atomically
claimed, executed through the local HOS-AUTO-01 bridge, and published back to
private hermes-control as a structured result. No SSH/root execution path.
"""
import hashlib
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone

from deploy.hos_auto_02.schema import R2Task, R2Result, validate_transport
from deploy.hos_auto_02.transport import (
    git_pull,
    git_commit_and_push,
    list_inbox_tasks,
    read_task_file,
    get_task_commit_sha,
    list_issue_tasks,
    read_issue_task,
)
from deploy.hos_auto_02.claim import attempt_claim
from deploy.hos_auto_02.loop_guard import check_rate_limit, check_depth, check_ttl

from deploy.hos_auto_01.policy.authority import (
    TaskContract,
    Operation,
    Assertion,
    OperationType,
    AuthorityClass,
    validate_authority,
    AUTHORITY_MATRIX,
)


POLL_INTERVAL = 30
BRIDGE_PATH = "/opt/hermes-auto/bin/bridge.py"
BRIDGE_PYTHON = "/opt/hermes-auto/venv/bin/python3"
EVIDENCE_ROOT = "/opt/hermes-auto/evidence"
CONTRACT_DIR = "/var/lib/hermes-auto/contracts"
STATE_FILE = os.environ.get("R2_STATE_FILE", "/var/lib/hermes-auto/state/r2-state.json")


# ─── Persistent State ──────────────────────────────────────────────

def _default_state() -> dict:
    return {
        "seen_nonces": [],
        "completed_tasks": [],
        "failure_counts": {},
        "processed_issues": [],
    }


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = _default_state()
    for key, value in _default_state().items():
        state.setdefault(key, value.copy() if isinstance(value, (list, dict)) else value)
    return state


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    temp = f"{STATE_FILE}.tmp-{uuid.uuid4().hex}"
    with open(temp, "w") as f:
        json.dump(state, f)
    os.chmod(temp, 0o600)
    os.replace(temp, STATE_FILE)


_state = load_state()


def persistent_is_duplicate_nonce(nonce: str) -> bool:
    if nonce in _state["seen_nonces"]:
        return True
    _state["seen_nonces"].append(nonce)
    _state["seen_nonces"] = _state["seen_nonces"][-1000:]
    save_state(_state)
    return False


def persistent_is_duplicate_task(task_id: str) -> bool:
    return task_id in _state.get("completed_tasks", [])


def persistent_mark_completed(task_id: str):
    if task_id not in _state.setdefault("completed_tasks", []):
        _state["completed_tasks"].append(task_id)
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


def persistent_issue_processed(issue_number: int, source_version: str) -> bool:
    marker = f"{int(issue_number)}:{source_version}"
    return marker in _state.get("processed_issues", [])


def persistent_mark_issue_processed(issue_number: int, source_version: str):
    marker = f"{int(issue_number)}:{source_version}"
    items = _state.setdefault("processed_issues", [])
    if marker not in items:
        items.append(marker)
    _state["processed_issues"] = items[-5000:]
    save_state(_state)


# ─── Authority Classification ──────────────────────────────────────

def classify_authority(task: R2Task) -> AuthorityClass:
    if task.depth > 3:
        return AuthorityClass.FORBIDDEN
    suggestion = task.authority_suggestion.upper()
    if suggestion == "FORBIDDEN":
        return AuthorityClass.FORBIDDEN
    if suggestion == "GATED":
        return AuthorityClass.GATED
    for op in task.contract.get("operations", []):
        try:
            op_type = OperationType(op["type"])
        except (KeyError, ValueError, TypeError):
            return AuthorityClass.FORBIDDEN
        classification = AUTHORITY_MATRIX.get(op_type, AuthorityClass.FORBIDDEN)
        if classification == AuthorityClass.FORBIDDEN:
            return AuthorityClass.FORBIDDEN
        if classification == AuthorityClass.GATED:
            return AuthorityClass.GATED
    return AuthorityClass.AUTO


# ─── Local Bridge Invocation (no SSH) ──────────────────────────────

def run_local_bridge(task: R2Task, source_version: str) -> dict:
    """Invoke the locally installed HOS-AUTO-01 bridge. No SSH, no root."""
    try:
        ops = [
            Operation(
                type=OperationType(o["type"]),
                params=o.get("params", {}),
                timeout_seconds=o.get("timeout_seconds", 300),
            )
            for o in task.contract.get("operations", [])
        ]
    except (KeyError, ValueError, TypeError) as e:
        return {"status": "REJECTED", "verdict": "INVALID_OPERATION", "summary": str(e)}

    assertions = [
        Assertion(id=a["id"], check=a["check"], expect=str(a["expect"]))
        for a in task.contract.get("expected_assertions", [])
    ]

    contract = TaskContract(
        task_id=task.task_id,
        objective=task.objective,
        authority_class=classify_authority(task),
        working_directory=task.contract.get("working_directory", "/tmp/hos-auto-01-src"),
        source_git_sha=source_version,
        operations=ops,
        expected_assertions=assertions,
        timeout_seconds=task.contract.get("timeout_seconds", 600),
    )

    ok, msg = validate_authority(contract)
    if not ok:
        return {
            "status": "REJECTED",
            "verdict": "FAIL",
            "summary": msg,
            "requires_human_decision": contract.authority_class == AuthorityClass.GATED,
        }

    os.makedirs(CONTRACT_DIR, exist_ok=True)
    contract_path = os.path.join(CONTRACT_DIR, f"contract-{uuid.uuid4().hex}.json")
    contract_dict = {
        "task_id": contract.task_id,
        "objective": contract.objective,
        "authority_class": contract.authority_class.value,
        "working_directory": contract.working_directory,
        "source_git_sha": contract.source_git_sha,
        "operations": [
            {"type": o.type.value, "params": o.params, "timeout_seconds": o.timeout_seconds}
            for o in ops
        ],
        "expected_assertions": [
            {"id": a.id, "check": a.check, "expect": a.expect} for a in assertions
        ],
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
            capture_output=True,
            text=True,
            timeout=min(int(contract.timeout_seconds), 600),
            env=env,
        )

        receipt_sha = None
        verdict = "UNKNOWN"
        for line in result.stdout.split("\n"):
            if "Receipt:" in line:
                receipt_sha = line.split()[-1].strip()
            if "VERDICT:" in line:
                verdict = line.split()[-1].strip()

        if result.returncode != 0 and verdict == "UNKNOWN":
            verdict = "FAIL"

        return {
            "status": "COMPLETED",
            "verdict": verdict,
            "summary": result.stdout.strip()[-200:] if result.stdout else result.stderr.strip()[-200:],
            "evidence_receipts": [receipt_sha] if receipt_sha else [],
        }
    except subprocess.TimeoutExpired:
        return {"status": "STOPPED", "verdict": "TIMEOUT", "summary": "Bridge timeout"}
    except Exception as e:
        return {"status": "STOPPED", "verdict": "ERROR", "summary": str(e)}
    finally:
        try:
            os.unlink(contract_path)
        except OSError:
            pass


# ─── Generic Task Processing ───────────────────────────────────────

def process_task_content(content: str, source_version: str, transport_path: str) -> R2Result:
    """Validate/classify/claim/execute a task from any approved ingress."""
    try:
        task_data = json.loads(content)
    except json.JSONDecodeError:
        return R2Result(task_id="unknown", result_id="res-unknown", status="REJECTED", verdict="MALFORMED")

    task = R2Task.from_json(task_data)
    task_id = task.task_id or "unknown"
    result = R2Result(task_id=task_id, result_id=f"res-{task_id}")

    if persistent_is_duplicate_task(task_id):
        result.status = "SKIPPED"
        result.verdict = "DUPLICATE"
        result.summary = "Already processed"
        return result

    errors = task.validate()
    if errors:
        result.status = "REJECTED"
        result.verdict = "INVALID"
        result.summary = "; ".join(errors)
        return result

    if not check_ttl(task.expires_at):
        result.status = "EXPIRED"
        result.verdict = "EXPIRED"
        result.summary = "TTL expired"
        return result
    if not check_depth(task.depth):
        result.status = "REJECTED"
        result.verdict = "MAX_DEPTH"
        return result
    if persistent_is_duplicate_nonce(task.nonce):
        result.status = "REJECTED"
        result.verdict = "REPLAY"
        return result
    if not check_rate_limit():
        result.status = "STOPPED"
        result.verdict = "RATE_LIMITED"
        return result

    # File tasks retain strict repo/branch/path transport validation.
    if transport_path.startswith("tasks/inbox/"):
        ok, msg = validate_transport("amjadthaufeeg/hermes-control", "main", transport_path)
        if not ok:
            result.status = "REJECTED"
            result.verdict = "TRANSPORT"
            result.summary = msg
            return result
    elif not transport_path.startswith("issues/"):
        result.status = "REJECTED"
        result.verdict = "TRANSPORT"
        result.summary = "Unsupported ingress transport"
        return result

    claimed, claim_msg = attempt_claim(task_id, source_version)
    if not claimed:
        result.status = "SKIPPED"
        result.verdict = "CLAIM_FAILED"
        result.summary = claim_msg
        return result

    authority = classify_authority(task)
    result.authority_class = authority.value
    result.task_commit_sha = source_version
    result.contract_sha256 = task.contract_sha256 or ""

    if authority == AuthorityClass.FORBIDDEN:
        result.status = "REJECTED"
        result.verdict = "FORBIDDEN"
        result.summary = "FORBIDDEN authority"
        persistent_mark_completed(task_id)
        return result
    if authority == AuthorityClass.GATED:
        result.status = "STOPPED"
        result.verdict = "GATED"
        result.requires_human_decision = True
        result.summary = "GATED — requires Amjad authorization"
        return result

    exec_result = run_local_bridge(task, source_version)
    result.status = exec_result.get("status", result.status)
    result.verdict = exec_result.get("verdict", result.verdict)
    result.summary = exec_result.get("summary", "")
    result.evidence_receipts = exec_result.get("evidence_receipts", [])

    if result.verdict == "FAIL":
        if persistent_record_failure(task_id):
            result.warnings.append("STOP: 3 identical failures")
    else:
        persistent_reset_failures(task_id)

    persistent_mark_completed(task_id)
    return result


def process_file_task(filename: str) -> R2Result:
    content = read_task_file(filename)
    if not content:
        task_id = filename.replace(".json", "")
        return R2Result(
            task_id=task_id,
            result_id=f"res-{task_id}",
            status="STOPPED",
            verdict="ERROR",
            summary="Cannot read task file",
        )
    source_version = get_task_commit_sha() or "unknown"
    return process_task_content(content, source_version, f"tasks/inbox/{filename}")


def process_issue_task(issue_number: int) -> R2Result:
    """Process one private GitHub Issue task with edit-race protection."""
    first = read_issue_task(issue_number)
    if not first:
        return R2Result(
            task_id=f"issue-{issue_number}",
            result_id=f"res-issue-{issue_number}",
            status="REJECTED",
            verdict="TRANSPORT",
            summary="Issue does not satisfy R2 ingress policy",
        )

    if persistent_issue_processed(issue_number, first["source_version"]):
        return R2Result(
            task_id=f"issue-{issue_number}",
            result_id=f"res-issue-{issue_number}",
            status="SKIPPED",
            verdict="DUPLICATE",
            summary="Issue version already processed",
        )

    # Fetch twice before claim to ensure task body is stable across validation boundary.
    second = read_issue_task(issue_number)
    if not second or second["source_version"] != first["source_version"]:
        return R2Result(
            task_id=f"issue-{issue_number}",
            result_id=f"res-issue-{issue_number}",
            status="STOPPED",
            verdict="SOURCE_CHANGED",
            summary="Issue changed during validation; retry on next poll",
        )

    result = process_task_content(
        first["body"],
        first["source_version"],
        f"issues/{issue_number}",
    )
    # Record terminal states only; GATED/SOURCE_CHANGED may need future action.
    if result.status in {"COMPLETED", "REJECTED", "EXPIRED", "SKIPPED"}:
        persistent_mark_issue_processed(issue_number, first["source_version"])
    return result


# ─── Result Publication ────────────────────────────────────────────

def publish_result(result: R2Result):
    result.completed_at = datetime.now(timezone.utc).isoformat()
    result.result_sha256 = result.compute_hash()
    result_json = json.dumps({
        "task_id": result.task_id,
        "result_id": result.result_id,
        "task_commit_sha": result.task_commit_sha,
        "contract_sha256": result.contract_sha256,
        "status": result.status,
        "verdict": result.verdict,
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
    else:
        print(f"Publish failed: {msg}")


# ─── Watch Loop ────────────────────────────────────────────────────

def watch_loop():
    print("HOS-AUTO-02 R2 watcher started (file + issue ingress, local bridge)")
    while True:
        try:
            git_pull()

            for filename in list_inbox_tasks():
                print(f"Processing file task: {filename}")
                result = process_file_task(filename)
                publish_result(result)
                print(f"  → {result.status} {result.verdict}: {result.summary[:80]}")

            try:
                issues = list_issue_tasks()
            except Exception as e:
                issues = []
                print(f"Issue ingress unavailable: {e}")

            for issue in issues:
                number = int(issue["number"])
                print(f"Processing issue task: #{number}")
                result = process_issue_task(number)
                if result.verdict != "DUPLICATE":
                    publish_result(result)
                print(f"  → {result.status} {result.verdict}: {result.summary[:80]}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Watcher error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch_loop()
