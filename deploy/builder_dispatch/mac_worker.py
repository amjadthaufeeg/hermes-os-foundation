"""macOS Hermes builder worker.

Runs beside the local Hermes gateway. GitHub is the durable queue, HOS is the
builder gate, and Kimi/Codex run only inside dedicated per-task worktrees.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from deploy.builder_dispatch.adapter import BuilderJob, DispatchError, dispatch, load_config
from deploy.builder_dispatch.mac_transport import commit_and_push, control_dir, ensure_clone, sync_rebase
from deploy.builder_dispatch.queue_watcher import QueueJob, verify_hos_gate

INBOX = "builders/inbox"
CLAIMS = "builders/claims"
COMPLETED = "builders/completed"
STOPPED = "builders/stopped"
PROCESSOR_ID = f"hermes-builder-mac-{socket.gethostname()}"
DEFAULT_ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"


def _run(args: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, shell=False)


def _load_raw_config(path: Path) -> dict:
    # load_config enforces owner/mode and validates builder executables.
    load_config(str(path))
    return json.loads(path.read_text())


def _repo_config(raw: dict, repository: str) -> dict:
    cfg = raw.get("repositories", {}).get(repository)
    if not isinstance(cfg, dict):
        raise DispatchError(f"repository not configured: {repository}")
    return cfg


def _validate_branch(branch: str, repo_cfg: dict) -> None:
    prefixes = tuple(str(x) for x in repo_cfg.get("allowed_branch_prefixes", ["feature/", "fix/", "chore/"]))
    if not branch.startswith(prefixes):
        raise DispatchError("branch prefix not allowed")


def _ensure_worktree(q: QueueJob, repo_cfg: dict) -> tuple[Path, Path]:
    source = Path(str(repo_cfg.get("source_repository", ""))).expanduser().resolve()
    if not (source / ".git").exists():
        raise DispatchError(f"source repository unavailable: {source}")
    _validate_branch(q.branch, repo_cfg)

    fetch = _run(["git", "fetch", "origin"], cwd=source, timeout=180)
    if fetch.returncode != 0:
        raise DispatchError(f"git fetch failed: {fetch.stderr.strip() or fetch.stdout.strip()}")
    exists = _run(["git", "cat-file", "-e", f"{q.baseline_commit}^{{commit}}"], cwd=source)
    if exists.returncode != 0:
        raise DispatchError("baseline commit is not present in source repository")

    root = Path(str(repo_cfg.get("worktree_root", ""))).expanduser().resolve()
    if not root.is_absolute():
        raise DispatchError("worktree_root must be absolute")
    worktree = root / q.builder / q.task_id
    worktree.parent.mkdir(parents=True, exist_ok=True)

    if worktree.exists():
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree).stdout.strip()
        if branch != q.branch:
            raise DispatchError(f"existing worktree branch mismatch: {branch}")
    else:
        local_branch = _run(["git", "show-ref", "--verify", f"refs/heads/{q.branch}"], cwd=source)
        if local_branch.returncode == 0:
            add = _run(["git", "worktree", "add", str(worktree), q.branch], cwd=source, timeout=180)
        else:
            add = _run(["git", "worktree", "add", "-b", q.branch, str(worktree), q.baseline_commit], cwd=source, timeout=180)
        if add.returncode != 0:
            raise DispatchError(f"cannot create task worktree: {add.stderr.strip() or add.stdout.strip()}")

    contract_root_rel = str(repo_cfg.get("contract_root_relpath", "docs/tasks"))
    contract_root = (worktree / contract_root_rel).resolve()
    contract = (contract_root / q.contract_relpath).resolve()
    if contract_root != contract and contract_root not in contract.parents:
        raise DispatchError("contract path escapes configured contract root")
    if not contract.is_file():
        raise DispatchError(f"task contract not present in worktree: {contract}")
    return worktree, contract


def _claim_path(task_id: str) -> str:
    return f"{CLAIMS}/{task_id}/claim.json"


def _claim_state(task_id: str) -> str:
    path = control_dir() / _claim_path(task_id)
    if not path.is_file():
        return "unclaimed"
    try:
        data = json.loads(path.read_text())
    except Exception:
        return "other"
    return "mine" if data.get("processor_id") == PROCESSOR_ID else "other"


def _claim(task_id: str) -> bool:
    state = _claim_state(task_id)
    if state == "mine":
        return True
    if state != "unclaimed":
        return False
    payload = {
        "task_id": task_id,
        "processor_id": PROCESSOR_ID,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "claim_nonce": uuid.uuid4().hex,
    }
    ok, _, _ = commit_and_push(
        [(_claim_path(task_id), json.dumps(payload, indent=2))],
        f"builder-claim: {task_id} by {PROCESSOR_ID}",
    )
    return ok


def _publish(task_id: str, payload: dict, *, completed: bool) -> None:
    target = f"{COMPLETED}/{task_id}.json" if completed else f"{STOPPED}/{task_id}.json"
    ok, msg, _ = commit_and_push(
        [(target, json.dumps(payload, indent=2))],
        f"builder-completed: {task_id} status={payload.get('status')}",
        delete_paths=[f"{INBOX}/{task_id}.json"],
    )
    if not ok:
        raise DispatchError(f"cannot publish builder result: {msg}")


def _finalize_git(q: QueueJob, worktree: Path, result: dict) -> dict:
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree).stdout.strip()
    if branch != q.branch:
        raise DispatchError("builder changed away from assigned branch")
    status = _run(["git", "status", "--porcelain"], cwd=worktree).stdout.strip()
    if status:
        raise DispatchError("builder left uncommitted changes; candidate is not durable")
    candidate = _run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()
    if not candidate:
        raise DispatchError("candidate SHA unavailable")
    if candidate == q.baseline_commit:
        raise DispatchError("builder produced no committed change")
    push = _run(["git", "push", "-u", "origin", q.branch], cwd=worktree, timeout=180)
    if push.returncode != 0:
        raise DispatchError(f"candidate push failed: {push.stderr.strip() or push.stdout.strip()}")
    result["candidate_sha"] = candidate
    result["branch"] = q.branch
    result["pushed"] = True
    return result


def process_once(config_path: str, *, state_dir: str) -> int:
    ok, _ = sync_rebase()
    if not ok:
        return 0
    local = ensure_clone()
    inbox = local / INBOX
    if not inbox.exists():
        return 0
    config = Path(config_path).expanduser()
    raw_cfg = _load_raw_config(config)
    specs = load_config(str(config))
    processed = 0

    for inbox_file in sorted(inbox.glob("*.json")):
        if inbox_file.name == ".gitkeep":
            continue
        q = None
        try:
            q = QueueJob.from_dict(json.loads(inbox_file.read_text()))
            if not q.task_id or _claim_state(q.task_id) == "other":
                continue
            verify_hos_gate(q, local)
            if q.builder not in specs:
                raise DispatchError(f"builder not configured: {q.builder}")
            repo_cfg = _repo_config(raw_cfg, q.repository)
            worktree, contract = _ensure_worktree(q, repo_cfg)
            if not _claim(q.task_id):
                continue
            job = BuilderJob(
                task_id=q.task_id,
                builder=q.builder,
                repository=q.repository,
                working_directory=str(worktree),
                branch=q.branch,
                baseline_commit=q.baseline_commit,
                contract_path=str(contract),
                timeout_seconds=q.timeout_seconds,
            )
            result = dispatch(job, specs[q.builder], state_dir=state_dir)
            result["hos_gate_task_id"] = q.hos_gate_task_id
            result["hos_gate_receipt"] = q.hos_gate_receipt
            if result["status"] != "COMPLETED":
                raise DispatchError(f"builder exited {result.get('exit_code')}: {result.get('stderr', '')[-500:]}")
            result = _finalize_git(q, worktree, result)
            result["completed_at"] = datetime.now(timezone.utc).isoformat()
            _publish(q.task_id, result, completed=True)
        except Exception as exc:
            task_id = q.task_id if q is not None and q.task_id else inbox_file.stem
            payload = {
                "task_id": task_id,
                "status": "STOPPED",
                "error": type(exc).__name__,
                "summary": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                _publish(task_id, payload, completed=False)
            except Exception:
                pass
        processed += 1
    return processed


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_ROOT / "config.json"))
    parser.add_argument("--state-dir", default=str(DEFAULT_ROOT / "state"))
    parser.add_argument("--poll", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        process_once(args.config, state_dir=args.state_dir)
        return 0
    while True:
        process_once(args.config, state_dir=args.state_dir)
        time.sleep(max(5, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
