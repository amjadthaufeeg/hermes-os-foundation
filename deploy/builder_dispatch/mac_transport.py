"""macOS Git transport for the Hermes builder worker.

Uses the user's existing Git/SSH authentication. It never stores credentials
and serializes local writes to the private hermes-control queue.
"""
from __future__ import annotations

import fcntl
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

REPO_URL = "git@github.com:amjadthaufeeg/hermes-control.git"
BRANCH = "main"
DEFAULT_ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"


def control_dir() -> Path:
    override = os.environ.get("HERMES_BUILDER_CONTROL_DIR")
    return Path(override).expanduser() if override else DEFAULT_ROOT / "hermes-control"


def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout, shell=False)


@contextmanager
def transport_lock():
    root = control_dir().parent
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "transport.lock"
    with lock_path.open("w") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        yield


def ensure_clone() -> Path:
    local = control_dir()
    if (local / ".git").is_dir():
        return local
    local.parent.mkdir(parents=True, exist_ok=True)
    result = _run(["git", "clone", "--branch", BRANCH, "--single-branch", REPO_URL, str(local)], timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"cannot clone hermes-control: {result.stderr.strip() or result.stdout.strip()}")
    return local


def sync_rebase() -> tuple[bool, str]:
    local = ensure_clone()
    with transport_lock():
        fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
        if fetch.returncode != 0:
            return False, fetch.stderr.strip() or fetch.stdout.strip()
        rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
        if rebase.returncode != 0:
            _run(["git", "rebase", "--abort"], cwd=local, timeout=10)
            return False, rebase.stderr.strip() or rebase.stdout.strip()
        return True, "synced"


def commit_and_push(files: list[tuple[str, str]], message: str, *, delete_paths: list[str] | None = None) -> tuple[bool, str, Optional[str]]:
    local = ensure_clone()
    with transport_lock():
        fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
        if fetch.returncode != 0:
            return False, fetch.stderr.strip(), None
        rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
        if rebase.returncode != 0:
            _run(["git", "rebase", "--abort"], cwd=local, timeout=10)
            return False, rebase.stderr.strip(), None

        for path, content in files:
            full = local / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
        for path in delete_paths or []:
            full = local / path
            if full.exists():
                full.unlink()

        _run(["git", "add", "-A"], cwd=local, timeout=15)
        diff = _run(["git", "diff", "--cached", "--quiet"], cwd=local, timeout=15)
        if diff.returncode == 0:
            sha = _run(["git", "rev-parse", "HEAD"], cwd=local, timeout=10).stdout.strip()
            return True, "No changes", sha

        commit = _run([
            "git", "-c", "user.name=Hermes Builder Worker",
            "-c", "user.email=hermes-builder@localhost",
            "commit", "-m", message,
        ], cwd=local, timeout=30)
        if commit.returncode != 0:
            return False, commit.stderr.strip() or commit.stdout.strip(), None

        for _ in range(3):
            push = _run(["git", "push", "origin", BRANCH], cwd=local, timeout=60)
            if push.returncode == 0:
                sha = _run(["git", "rev-parse", "HEAD"], cwd=local, timeout=10).stdout.strip()
                return True, "Committed", sha
            fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
            if fetch.returncode != 0:
                return False, fetch.stderr.strip(), None
            rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
            if rebase.returncode != 0:
                _run(["git", "rebase", "--abort"], cwd=local, timeout=10)
                return False, rebase.stderr.strip(), None
        return False, "push failed after 3 retries", None
