"""macOS Hermes Builder Worker v3.

Security model:
- dedicated non-admin macOS account;
- one full Git clone per task (no shared worktree metadata);
- repo-specific SSH deploy key with no SSH agent inheritance;
- exact HOS gate receipt/contract binding;
- allowed-files/protected-path enforcement;
- baseline ancestry and protected-branch snapshot checks;
- fixed remote URL for the final task-branch push.
"""
from __future__ import annotations

import fnmatch
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from deploy.builder_dispatch.adapter import BuilderJob, DispatchError, dispatch, load_config, redact
from deploy.builder_dispatch.gate import QueueJob, verify_hos_gate
from deploy.builder_dispatch.mac_transport import commit_and_push, control_dir, ensure_clone, sync_rebase

INBOX = "builders/inbox"
CLAIMS = "builders/claims"
COMPLETED = "builders/completed"
STOPPED = "builders/stopped"
PROCESSOR_ID = f"hermes-builder-mac-{socket.gethostname()}"
DEFAULT_ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"
PROTECTED_DEFAULT = ("main", "master", "production", "prod")


def _git_env(key: Path) -> dict[str, str]:
    known_hosts = DEFAULT_ROOT / "known_hosts"
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(Path.home()),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "SSH_AUTH_SOCK": "",
        "GIT_SSH_COMMAND": (
            f"/usr/bin/ssh -i {key} -o IdentitiesOnly=yes -o BatchMode=yes "
            f"-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={known_hosts}"
        ),
    }


def _run_git(args: list[str], *, cwd: Path, key: Path, timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null"] + args,
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        shell=False, env=_git_env(key),
    )


def _secure_key(raw: str, name: str) -> Path:
    p = Path(raw).expanduser().resolve()
    if not p.is_file(): raise DispatchError(f"{name} deploy key missing")
    if p.stat().st_mode & 0o077: raise DispatchError(f"{name} deploy key must be mode 0600 or stricter")
    return p


def _repo_config(raw: dict, repository: str) -> dict:
    cfg = raw.get("repositories", {}).get(repository)
    if not isinstance(cfg, dict): raise DispatchError(f"repository not configured: {repository}")
    for field in ("remote_url", "ssh_key", "clone_root"):
        if not cfg.get(field): raise DispatchError(f"repository config missing {field}: {repository}")
    return cfg


def _allowed_branch(branch: str, cfg: dict) -> bool:
    prefixes = tuple(str(x) for x in cfg.get("allowed_branch_prefixes", ["feature/", "fix/", "chore/"]))
    return bool(branch) and branch not in PROTECTED_DEFAULT and branch.startswith(prefixes)


def _remote_snapshot(remote: str, protected: list[str], *, cwd: Path, key: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for branch in protected:
        r = _run_git(["ls-remote", remote, f"refs/heads/{branch}"], cwd=cwd, key=key, timeout=60)
        if r.returncode != 0: raise DispatchError(f"cannot snapshot protected branch {branch}")
        line = r.stdout.strip().splitlines()
        snap[branch] = line[0].split()[0] if line else ""
    return snap


def _prepare_clone(q: QueueJob, cfg: dict) -> tuple[Path, Path, Path, str, dict[str, str]]:
    if not _allowed_branch(q.branch, cfg): raise DispatchError("branch prefix not allowed")
    remote = str(cfg["remote_url"])
    key = _secure_key(str(cfg["ssh_key"]), q.repository)
    root = Path(str(cfg["clone_root"])).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    clone = (root / q.builder / q.task_id).resolve()
    if root not in clone.parents: raise DispatchError("clone path escaped configured root")
    if clone.exists(): shutil.rmtree(clone)
    clone.parent.mkdir(parents=True, exist_ok=True)

    parent = clone.parent
    before = _remote_snapshot(remote, list(cfg.get("protected_branches", PROTECTED_DEFAULT)), cwd=parent, key=key)
    r = _run_git(["clone", "--no-checkout", remote, str(clone)], cwd=parent, key=key, timeout=300)
    if r.returncode != 0: raise DispatchError(f"clone failed: {redact(r.stderr or r.stdout)[-500:]}")
    origin = _run_git(["remote", "get-url", "origin"], cwd=clone, key=key).stdout.strip()
    if origin != remote: raise DispatchError("clone origin mismatch")
    exists = _run_git(["cat-file", "-e", f"{q.baseline_commit}^{{commit}}"], cwd=clone, key=key)
    if exists.returncode != 0: raise DispatchError("baseline commit unavailable in isolated clone")
    checkout = _run_git(["switch", "-c", q.branch, q.baseline_commit], cwd=clone, key=key)
    if checkout.returncode != 0: raise DispatchError(f"cannot create assigned branch: {redact(checkout.stderr)[-500:]}")

    contract_root = (clone / str(cfg.get("contract_root_relpath", "docs/tasks"))).resolve()
    contract = (contract_root / q.contract_relpath).resolve()
    if contract_root != contract and contract_root not in contract.parents: raise DispatchError("contract path escapes root")
    if not contract.is_file(): raise DispatchError(f"task contract missing at baseline: {contract}")
    return clone, contract, key, remote, before


def _path_allowed(path: str, patterns: list[str]) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        pat = str(pattern).replace("\\", "/").lstrip("./")
        if fnmatch.fnmatch(p, pat): return True
        if pat.endswith("/**") and (p == pat[:-3].rstrip("/") or p.startswith(pat[:-3].rstrip("/") + "/")): return True
        if pat.endswith("/") and p.startswith(pat): return True
    return False


def _path_protected(path: str, patterns: list[str]) -> bool:
    p = path.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        pat = str(pattern).replace("\\", "/").lstrip("./")
        if fnmatch.fnmatch(p, pat) or p == pat.rstrip("/") or p.startswith(pat.rstrip("/") + "/"): return True
    return False


def _finalize_git(q: QueueJob, clone: Path, key: Path, remote: str, before: dict[str, str], result: dict) -> dict:
    gate = q.hos_gate_contract.get("builder_gate", {})
    allowed_files = [str(x) for x in gate.get("allowed_files", [])]
    protected_paths = [str(x) for x in gate.get("protected_paths", [])]
    if not allowed_files: raise DispatchError("gate has no allowed_files")

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=clone, key=key).stdout.strip()
    if branch != q.branch: raise DispatchError("builder changed away from assigned branch")
    if _run_git(["status", "--porcelain"], cwd=clone, key=key).stdout.strip():
        raise DispatchError("builder left uncommitted changes")
    candidate = _run_git(["rev-parse", "HEAD"], cwd=clone, key=key).stdout.strip()
    if not candidate or candidate == q.baseline_commit: raise DispatchError("builder produced no committed candidate")
    ancestor = _run_git(["merge-base", "--is-ancestor", q.baseline_commit, candidate], cwd=clone, key=key)
    if ancestor.returncode != 0: raise DispatchError("candidate does not descend from baseline")

    diff = _run_git(["diff", "--name-only", f"{q.baseline_commit}..{candidate}"], cwd=clone, key=key)
    if diff.returncode != 0: raise DispatchError("cannot compute candidate diff")
    changed = [x.strip() for x in diff.stdout.splitlines() if x.strip()]
    if not changed: raise DispatchError("candidate diff is empty")
    bad_allowed = [p for p in changed if not _path_allowed(p, allowed_files)]
    bad_protected = [p for p in changed if _path_protected(p, protected_paths)]
    if bad_allowed: raise DispatchError("changed files outside allowed_files: " + ", ".join(bad_allowed[:20]))
    if bad_protected: raise DispatchError("changed protected_paths: " + ", ".join(bad_protected[:20]))

    origin = _run_git(["remote", "get-url", "origin"], cwd=clone, key=key).stdout.strip()
    if origin != remote: raise DispatchError("builder altered repository origin")
    after = _remote_snapshot(remote, list(before.keys()), cwd=clone, key=key)
    if after != before: raise DispatchError("protected remote branch moved during build")

    push = _run_git(["push", remote, f"{candidate}:refs/heads/{q.branch}"], cwd=clone, key=key, timeout=180)
    if push.returncode != 0: raise DispatchError(f"candidate push failed: {redact(push.stderr or push.stdout)[-500:]}")
    result.update({"candidate_sha": candidate, "branch": q.branch, "pushed": True, "changed_files": changed,
                   "protected_branch_snapshot": before})
    return result


def _claim_path(task_id: str) -> str: return f"{CLAIMS}/{task_id}/claim.json"


def _claim_state(task_id: str) -> str:
    path = control_dir() / _claim_path(task_id)
    if not path.is_file(): return "unclaimed"
    try: data = json.loads(path.read_text())
    except Exception: return "other"
    return "mine" if data.get("processor_id") == PROCESSOR_ID else "other"


def _claim(task_id: str) -> bool:
    state = _claim_state(task_id)
    if state == "mine": return True
    if state != "unclaimed": return False
    payload = {"task_id": task_id, "processor_id": PROCESSOR_ID,
               "claimed_at": datetime.now(timezone.utc).isoformat(), "claim_nonce": uuid.uuid4().hex}
    ok, _, _ = commit_and_push([(_claim_path(task_id), json.dumps(payload, indent=2))],
                               f"builder-claim: {task_id} by {PROCESSOR_ID}")
    return ok


def _publish(task_id: str, payload: dict, *, completed: bool) -> None:
    target = f"{COMPLETED}/{task_id}.json" if completed else f"{STOPPED}/{task_id}.json"
    ok, msg, _ = commit_and_push([(target, json.dumps(payload, indent=2))],
                                 f"builder-completed: {task_id} status={payload.get('status')}",
                                 delete_paths=[f"{INBOX}/{task_id}.json"])
    if not ok: raise DispatchError(f"cannot publish builder result: {msg}")


def process_once(config_path: str, *, state_dir: str) -> int:
    ok, _ = sync_rebase()
    if not ok: return 0
    local = ensure_clone(); inbox = local / INBOX
    if not inbox.exists(): return 0
    config = Path(config_path).expanduser(); load_config(str(config)); raw_cfg = json.loads(config.read_text()); specs = load_config(str(config))
    processed = 0
    for inbox_file in sorted(inbox.glob("*.json")):
        if inbox_file.name == ".gitkeep": continue
        q = None
        try:
            q = QueueJob.from_dict(json.loads(inbox_file.read_text()))
            if not q.task_id or _claim_state(q.task_id) == "other": continue
            verify_hos_gate(q, local)
            if q.builder not in specs: raise DispatchError(f"builder not configured: {q.builder}")
            cfg = _repo_config(raw_cfg, q.repository)
            clone, contract, key, remote, before = _prepare_clone(q, cfg)
            if not _claim(q.task_id): continue
            job = BuilderJob(q.task_id, q.builder, q.repository, str(clone), q.branch,
                             q.baseline_commit, str(contract), q.timeout_seconds)
            result = dispatch(job, specs[q.builder], state_dir=state_dir)
            result.update({"hos_gate_task_id": q.hos_gate_task_id, "hos_gate_receipt": q.hos_gate_receipt})
            if result["status"] != "COMPLETED": raise DispatchError(f"builder {result['status']}: {result.get('stderr','')[-500:]}")
            result = _finalize_git(q, clone, key, remote, before, result)
            result["completed_at"] = datetime.now(timezone.utc).isoformat(); _publish(q.task_id, result, completed=True)
        except Exception as exc:
            task_id = q.task_id if q is not None and q.task_id else inbox_file.stem
            payload = {"task_id": task_id, "status": "STOPPED", "error": type(exc).__name__,
                       "summary": redact(str(exc)), "completed_at": datetime.now(timezone.utc).isoformat()}
            try: _publish(task_id, payload, completed=False)
            except Exception: pass
        processed += 1
    return processed


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default=str(DEFAULT_ROOT / "config.json"))
    parser.add_argument("--state-dir", default=str(DEFAULT_ROOT / "state")); parser.add_argument("--poll", type=int, default=30); parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once: process_once(args.config, state_dir=args.state_dir); return 0
    while True: process_once(args.config, state_dir=args.state_dir); time.sleep(max(5, args.poll))


if __name__ == "__main__": raise SystemExit(main())
