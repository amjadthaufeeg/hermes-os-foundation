"""GitHub-backed queue watcher for Hermes builder dispatch.

A builder job is executable only when it is bound to a prior PASS HOS result.
The HOS result contract hash must match the exact gate contract carried by the
builder job, and the gate metadata must match builder/repo/branch/baseline.
"""
from __future__ import annotations

import hashlib
import json
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deploy.builder_dispatch.adapter import BuilderJob, DispatchError, dispatch, load_config
from deploy.hos_auto_02.transport import ensure_local_clone, git_pull, git_commit_and_push

INBOX = "builders/inbox"
CLAIMS = "builders/claims"
COMPLETED = "builders/completed"
STOPPED = "builders/stopped"
PROCESSOR_ID = f"hermes-builder-{socket.gethostname()}"
ALLOWED_SOURCES = {"hermes", "chatgpt"}


@dataclass(frozen=True)
class QueueJob:
    task_id: str
    source: str
    builder: str
    repository: str
    branch: str
    baseline_commit: str
    contract_relpath: str
    hos_gate_task_id: str
    hos_gate_receipt: str
    hos_gate_contract: dict[str, Any]
    timeout_seconds: int = 1800

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueJob":
        return cls(
            task_id=str(data.get("task_id", "")),
            source=str(data.get("source", "")),
            builder=str(data.get("builder", "")),
            repository=str(data.get("repository", "")),
            branch=str(data.get("branch", "")),
            baseline_commit=str(data.get("baseline_commit", "")),
            contract_relpath=str(data.get("contract_relpath", "")),
            hos_gate_task_id=str(data.get("hos_gate_task_id", "")),
            hos_gate_receipt=str(data.get("hos_gate_receipt", "")),
            hos_gate_contract=data.get("hos_gate_contract", {}) if isinstance(data.get("hos_gate_contract", {}), dict) else {},
            timeout_seconds=int(data.get("timeout_seconds", 1800)),
        )


def _repo_entry(config_data: dict, repository: str) -> dict:
    entry = config_data.get("repositories", {}).get(repository)
    if not isinstance(entry, dict):
        raise DispatchError(f"repository not configured: {repository}")
    return entry


def _contract_hash(contract: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def verify_hos_gate(q: QueueJob, control_dir: Path) -> None:
    """Verify that HOS authorized this exact builder assignment."""
    if not q.hos_gate_task_id or not q.hos_gate_receipt or not q.hos_gate_contract:
        raise DispatchError("missing HOS builder gate evidence")
    result_path = control_dir / "tasks" / "completed" / f"{q.hos_gate_task_id}.json"
    if not result_path.is_file():
        raise DispatchError("HOS builder gate result not found")
    try:
        result = json.loads(result_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchError("invalid HOS builder gate result") from exc

    if result.get("task_id") != q.hos_gate_task_id:
        raise DispatchError("HOS gate task id mismatch")
    if result.get("status") != "COMPLETED" or result.get("verdict") != "PASS":
        raise DispatchError("HOS builder gate did not PASS")
    if result.get("authority_class") != "AUTO":
        raise DispatchError("builder start requires AUTO HOS gate")
    if q.hos_gate_receipt not in result.get("evidence_receipts", []):
        raise DispatchError("HOS gate receipt mismatch")
    if result.get("contract_sha256") != _contract_hash(q.hos_gate_contract):
        raise DispatchError("HOS gate contract hash mismatch")

    gate = q.hos_gate_contract.get("builder_gate")
    if not isinstance(gate, dict):
        raise DispatchError("builder_gate metadata missing from HOS contract")
    expected = {
        "task_id": q.task_id,
        "builder": q.builder,
        "repository": q.repository,
        "branch": q.branch,
        "baseline_commit": q.baseline_commit,
        "contract_relpath": q.contract_relpath,
    }
    for key, value in expected.items():
        if str(gate.get(key, "")) != value:
            raise DispatchError(f"HOS builder gate mismatch: {key}")
    if not isinstance(gate.get("allowed_files"), list) or not gate.get("allowed_files"):
        raise DispatchError("HOS builder gate requires allowed_files")
    if not isinstance(gate.get("protected_paths", []), list):
        raise DispatchError("invalid protected_paths in HOS builder gate")


def resolve_job(q: QueueJob, config_path: str, *, control_dir: Path | None = None) -> tuple[BuilderJob, object]:
    if q.source not in ALLOWED_SOURCES:
        raise DispatchError("untrusted source")
    control = control_dir or ensure_local_clone()
    verify_hos_gate(q, control)

    raw = json.loads(Path(config_path).read_text())
    specs = load_config(config_path)
    if q.builder not in specs:
        raise DispatchError(f"builder not configured: {q.builder}")

    repo = _repo_entry(raw, q.repository)
    workdir = Path(str(repo.get("working_directory", ""))).resolve()
    if not workdir.is_absolute():
        raise DispatchError("configured working_directory must be absolute")

    prefixes = tuple(str(x) for x in repo.get("allowed_branch_prefixes", ["feature/", "fix/", "chore/"]))
    if not q.branch.startswith(prefixes):
        raise DispatchError("branch prefix not allowed")

    contract_root = Path(str(repo.get("contract_root", workdir / "docs" / "tasks"))).resolve()
    contract = (contract_root / q.contract_relpath).resolve()
    if contract_root != contract and contract_root not in contract.parents:
        raise DispatchError("contract path escapes configured contract_root")

    job = BuilderJob(
        task_id=q.task_id,
        builder=q.builder,
        repository=q.repository,
        working_directory=str(workdir),
        branch=q.branch,
        baseline_commit=q.baseline_commit,
        contract_path=str(contract),
        timeout_seconds=q.timeout_seconds,
    )
    return job, specs[q.builder]


def _claim_path(task_id: str) -> str:
    return f"{CLAIMS}/{task_id}/claim.json"


def _queue_files() -> list[Path]:
    local = ensure_local_clone()
    inbox = local / INBOX
    if not inbox.exists():
        return []
    return sorted(p for p in inbox.glob("*.json") if p.name != ".gitkeep")


def _already_claimed(task_id: str) -> bool:
    return (ensure_local_clone() / _claim_path(task_id)).exists()


def _claim(task_id: str) -> bool:
    if _already_claimed(task_id):
        return False
    payload = {
        "task_id": task_id,
        "processor_id": PROCESSOR_ID,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "claim_nonce": uuid.uuid4().hex,
    }
    ok, _, _ = git_commit_and_push(
        [(_claim_path(task_id), json.dumps(payload, indent=2))],
        f"builder-claim: {task_id} by {PROCESSOR_ID}",
    )
    return ok


def _publish(path: str, payload: dict, message: str, inbox_file: Path) -> None:
    try:
        inbox_file.unlink()
    except FileNotFoundError:
        pass
    ok, msg, _ = git_commit_and_push([(path, json.dumps(payload, indent=2))], message)
    if not ok:
        raise DispatchError(f"failed to publish queue result: {msg}")


def process_once(config_path: str, *, state_dir: str = "/var/lib/hermes-builder") -> int:
    ok, _ = git_pull()
    if not ok:
        return 0
    processed = 0
    for inbox_file in _queue_files():
        q = None
        try:
            raw = json.loads(inbox_file.read_text())
            q = QueueJob.from_dict(raw)
            if not q.task_id or _already_claimed(q.task_id):
                continue
            # Validate trusted config + HOS gate before creating a durable claim.
            job, spec = resolve_job(q, config_path)
            if not _claim(q.task_id):
                continue
            result = dispatch(job, spec, state_dir=state_dir)
            result["source"] = q.source
            result["hos_gate_task_id"] = q.hos_gate_task_id
            result["hos_gate_receipt"] = q.hos_gate_receipt
            result["completed_at"] = datetime.now(timezone.utc).isoformat()
            target = f"{COMPLETED}/{q.task_id}.json" if result["status"] == "COMPLETED" else f"{STOPPED}/{q.task_id}.json"
            _publish(target, result, f"builder-completed: {q.task_id} status={result['status']}", inbox_file)
        except Exception as exc:
            task_id = q.task_id if q is not None and q.task_id else inbox_file.stem
            payload = {
                "task_id": task_id,
                "status": "STOPPED",
                "error": type(exc).__name__,
                "summary": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            _publish(f"{STOPPED}/{task_id}.json", payload, f"builder-stopped: {task_id}", inbox_file)
        processed += 1
    return processed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/hermes-auto/builder-dispatch.json")
    parser.add_argument("--state-dir", default="/var/lib/hermes-builder")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=30)
    args = parser.parse_args()
    if args.once:
        raise SystemExit(0 if process_once(args.config, state_dir=args.state_dir) >= 0 else 1)
    while True:
        process_once(args.config, state_dir=args.state_dir)
        time.sleep(max(5, args.poll))
