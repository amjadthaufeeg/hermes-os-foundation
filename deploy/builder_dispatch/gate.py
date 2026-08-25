"""Portable HOS builder-gate contract and verification.

No HOS runtime imports: both the VPS and macOS workers can verify the exact
PASS result and receipt from the durable hermes-control repository.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deploy.builder_dispatch.adapter import DispatchError


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
        gate_contract = data.get("hos_gate_contract", {})
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
            hos_gate_contract=gate_contract if isinstance(gate_contract, dict) else {},
            timeout_seconds=int(data.get("timeout_seconds", 1800)),
        )


def contract_hash(contract: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def verify_hos_gate(q: QueueJob, control_dir: Path) -> None:
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
    if result.get("contract_sha256") != contract_hash(q.hos_gate_contract):
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
