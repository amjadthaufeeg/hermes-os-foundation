"""Promote validated ChatGPT ingress files into protected hermes-control main.

Security model:
- ChatGPT writes only to the unprotected `chatgpt-ingress` branch.
- This relay runs as the isolated `hermesbuilder` machine identity.
- Only `ingress/tasks/*.json` and `ingress/builders/*.json` are accepted.
- Files are mapped to `tasks/inbox/*.json` and `builders/inbox/*.json`.
- No arbitrary repository path can be promoted.
- The relay never merges code branches and never changes GitHub settings.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

from deploy.builder_dispatch.mac_transport import commit_and_push, ensure_clone, git_run, sync_rebase

INGRESS_BRANCH = "chatgpt-ingress"
TASK_PREFIX = "ingress/tasks/"
BUILDER_PREFIX = "ingress/builders/"
MAX_BYTES = 128 * 1024
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$")
DEFAULT_ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"
STATE_PATH = DEFAULT_ROOT / "ingress-relay-state.json"


def _log(message: str) -> None:
    print(f"[ingress-relay] {message}", file=sys.stderr, flush=True)


def _load_state() -> dict[str, str]:
    try:
        data = json.loads(STATE_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_PATH)


def _target_for(path: str) -> tuple[str, str] | None:
    if path.startswith(TASK_PREFIX):
        name = path[len(TASK_PREFIX):]
        if "/" in name or not NAME_RE.fullmatch(name):
            return None
        return "task", f"tasks/inbox/{name}"
    if path.startswith(BUILDER_PREFIX):
        name = path[len(BUILDER_PREFIX):]
        if "/" in name or not NAME_RE.fullmatch(name):
            return None
        return "builder", f"builders/inbox/{name}"
    return None


def _validate(kind: str, filename: str, content: str) -> dict:
    raw = content.encode()
    if len(raw) > MAX_BYTES:
        raise ValueError("ingress payload too large")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("ingress payload must be object")
    task_id = str(data.get("task_id", ""))
    if not task_id or f"{task_id}.json" != filename:
        raise ValueError("task_id must match filename")
    if str(data.get("source", "")) != "chatgpt":
        raise ValueError("ingress source must be chatgpt")
    if kind == "task":
        if str(data.get("schema_version", "")) != "1.0":
            raise ValueError("task schema_version must be 1.0")
        if not isinstance(data.get("contract"), dict) or not data["contract"]:
            raise ValueError("task contract required")
    else:
        for field in ("builder", "repository", "branch", "baseline_commit", "contract_relpath", "hos_gate_task_id", "hos_gate_receipt", "hos_gate_contract"):
            if not data.get(field):
                raise ValueError(f"builder job missing {field}")
    return data


def process_once() -> int:
    ok, sync_msg = sync_rebase()
    if not ok:
        _log(f"main sync failed: {sync_msg}")
        return 0
    repo = ensure_clone()

    fetch = git_run(["git", "fetch", "origin", f"{INGRESS_BRANCH}:refs/remotes/origin/{INGRESS_BRANCH}"], cwd=repo)
    if fetch.returncode != 0:
        _log(f"ingress fetch failed: {fetch.stderr.strip() or fetch.stdout.strip()}")
        return 0
    tree = git_run(["git", "ls-tree", "-r", "--name-only", f"origin/{INGRESS_BRANCH}", "--", "ingress"], cwd=repo)
    if tree.returncode != 0:
        _log(f"ingress tree read failed: {tree.stderr.strip() or tree.stdout.strip()}")
        return 0

    state = _load_state()
    processed = 0
    for path in sorted(x.strip() for x in tree.stdout.splitlines() if x.strip()):
        mapped = _target_for(path)
        if not mapped:
            _log(f"ignored unsupported ingress path: {path}")
            continue
        kind, target = mapped
        show = git_run(["git", "show", f"origin/{INGRESS_BRANCH}:{path}"], cwd=repo)
        if show.returncode != 0:
            _log(f"cannot read ingress payload {path}: {show.stderr.strip() or show.stdout.strip()}")
            continue
        digest = hashlib.sha256(show.stdout.encode()).hexdigest()
        if state.get(path) == digest:
            continue
        try:
            _validate(kind, Path(path).name, show.stdout)
        except Exception as exc:
            _log(f"validation rejected {path}: {exc}")
            continue

        target_path = repo / target
        if target_path.exists():
            if hashlib.sha256(target_path.read_bytes()).hexdigest() == digest:
                state[path] = digest
                processed += 1
                _log(f"already promoted: {path} -> {target}")
                continue
            _log(f"target collision; refusing overwrite: {target}")
            continue

        task_id = Path(path).stem
        terminal_paths = [
            repo / "tasks" / "completed" / f"{task_id}.json",
            repo / "builders" / "completed" / f"{task_id}.json",
            repo / "builders" / "stopped" / f"{task_id}.json",
        ]
        if any(p.exists() for p in terminal_paths):
            state[path] = digest
            _log(f"terminal task already exists; not replaying: {task_id}")
            continue

        success, message, sha = commit_and_push([(target, show.stdout)], f"ingress-promote: {task_id}")
        if success:
            state[path] = digest
            processed += 1
            _log(f"promoted {path} -> {target} at {sha}")
        else:
            _log(f"promotion failed for {path}: {message}")
    _save_state(state)
    return processed


def main() -> int:
    import argparse
    import time

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=20)
    args = parser.parse_args()
    if args.once:
        count = process_once()
        _log(f"single pass complete; processed={count}")
        return 0
    while True:
        count = process_once()
        if count:
            _log(f"poll pass processed={count}")
        time.sleep(max(10, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
