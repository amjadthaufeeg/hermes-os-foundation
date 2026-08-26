"""macOS Git transport for the Hermes builder worker.

Uses only the dedicated hermes-control deploy key configured by the installer.
No SSH agent inheritance, no ambient Git credentials.
"""
from __future__ import annotations

import fcntl
import os
import shlex
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

REPO_URL = "git@github.com:amjadthaufeeg/hermes-control.git"
BRANCH = "main"
DEFAULT_ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"
KNOWN_HOSTS = Path.home() / ".ssh" / "hermes-builder-known_hosts"


def control_dir() -> Path:
    override = os.environ.get("HERMES_BUILDER_CONTROL_DIR")
    return Path(override).expanduser() if override else DEFAULT_ROOT / "hermes-control"


def control_key() -> Path:
    raw = os.environ.get("HERMES_CONTROL_SSH_KEY", "")
    if not raw:
        raise RuntimeError("HERMES_CONTROL_SSH_KEY is required")
    p = Path(raw).expanduser().resolve()
    if not p.is_file():
        raise RuntimeError("hermes-control deploy key is missing")
    st = p.stat()
    if st.st_mode & 0o077:
        raise RuntimeError("hermes-control deploy key must be mode 0600 or stricter")
    return p


def _git_env() -> dict[str, str]:
    key = control_key()
    KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
    KNOWN_HOSTS.touch(exist_ok=True)
    os.chmod(KNOWN_HOSTS, 0o600)
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(Path.home()),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "SSH_AUTH_SOCK": "",
        "GIT_SSH_COMMAND": (
            f"/usr/bin/ssh -i {shlex.quote(str(key))} -o IdentitiesOnly=yes "
            f"-o BatchMode=yes -o StrictHostKeyChecking=accept-new "
            f"-o UserKnownHostsFile={shlex.quote(str(KNOWN_HOSTS))}"
        ),
    }


def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout, shell=False, env=_git_env())


@contextmanager
def transport_lock():
    root = control_dir().parent
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "transport.lock"
    with lock_path.open("w") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        yield


def _verify_origin(local: Path) -> None:
    origin = _run(["git", "remote", "get-url", "origin"], cwd=local, timeout=10).stdout.strip()
    if origin != REPO_URL: raise RuntimeError(f"unexpected hermes-control origin: {origin}")


def ensure_clone() -> Path:
    local = control_dir()
    if (local / ".git").is_dir():
        _verify_origin(local); return local
    local.parent.mkdir(parents=True, exist_ok=True)
    result = _run(["git", "clone", "--branch", BRANCH, "--single-branch", REPO_URL, str(local)], timeout=120)
    if result.returncode != 0: raise RuntimeError(f"cannot clone hermes-control: {result.stderr.strip() or result.stdout.strip()}")
    _verify_origin(local); return local


def sync_rebase() -> tuple[bool, str]:
    local = ensure_clone()
    with transport_lock():
        _verify_origin(local)
        fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
        if fetch.returncode != 0: return False, fetch.stderr.strip() or fetch.stdout.strip()
        rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
        if rebase.returncode != 0:
            _run(["git", "rebase", "--abort"], cwd=local, timeout=10)
            return False, rebase.stderr.strip() or rebase.stdout.strip()
        return True, "synced"


def commit_and_push(files: list[tuple[str, str]], message: str, *, delete_paths: list[str] | None = None) -> tuple[bool, str, Optional[str]]:
    local = ensure_clone()
    with transport_lock():
        _verify_origin(local)
        fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
        if fetch.returncode != 0: return False, fetch.stderr.strip(), None
        rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
        if rebase.returncode != 0:
            _run(["git", "rebase", "--abort"], cwd=local, timeout=10)
            return False, rebase.stderr.strip(), None
        for path, content in files:
            full = local / path; full.parent.mkdir(parents=True, exist_ok=True); full.write_text(content)
        for path in delete_paths or []:
            full = local / path
            if full.exists(): full.unlink()
        _run(["git", "add", "-A"], cwd=local, timeout=15)
        diff = _run(["git", "diff", "--cached", "--quiet"], cwd=local, timeout=15)
        if diff.returncode == 0:
            sha = _run(["git", "rev-parse", "HEAD"], cwd=local, timeout=10).stdout.strip(); return True, "No changes", sha
        commit = _run(["git", "-c", "user.name=Hermes Builder Worker", "-c", "user.email=hermes-builder@localhost", "commit", "-m", message], cwd=local, timeout=30)
        if commit.returncode != 0: return False, commit.stderr.strip() or commit.stdout.strip(), None
        for _ in range(3):
            _verify_origin(local)
            push = _run(["git", "push", REPO_URL, f"HEAD:refs/heads/{BRANCH}"], cwd=local, timeout=60)
            if push.returncode == 0:
                sha = _run(["git", "rev-parse", "HEAD"], cwd=local, timeout=10).stdout.strip(); return True, "Committed", sha
            fetch = _run(["git", "fetch", "origin", BRANCH], cwd=local)
            if fetch.returncode != 0: return False, fetch.stderr.strip(), None
            rebase = _run(["git", "rebase", f"origin/{BRANCH}"], cwd=local)
            if rebase.returncode != 0:
                _run(["git", "rebase", "--abort"], cwd=local, timeout=10); return False, rebase.stderr.strip(), None
        return False, "push failed after 3 retries", None
