"""HOS-AUTO-02 R2 — GitHub Transport.

Git pull/push operations on the private hermes-control repo.
No secrets in this module — uses git credential helper.
"""
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_URL = "https://github.com/amjadthaufeeg/hermes-control.git"
LOCAL_CLONE = os.path.expanduser("~/.hermes/hermes-control")


def ensure_local_clone() -> Path:
    """Ensure the local clone exists and is up to date."""
    local = Path(LOCAL_CLONE)
    if not (local / ".git").exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", REPO_URL, str(local)],
                      check=True, capture_output=True)
    return local


def git_pull() -> tuple[bool, str]:
    """Pull latest from main. Returns (success, message)."""
    local = ensure_local_clone()
    try:
        result = subprocess.run(
            ["git", "-C", str(local), "pull", "--ff-only", "origin", "main"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def git_commit_and_push(files: list[tuple[str, str]], message: str) -> tuple[bool, str, Optional[str]]:
    """Commit files and push to main. Returns (success, message, commit_sha)."""
    local = ensure_local_clone()
    try:
        for path, content in files:
            full_path = local / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        subprocess.run(["git", "-C", str(local), "add", "-A"],
                      check=True, capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(local), "commit", "-m", message],
                      check=True, capture_output=True, timeout=10)
        sha = subprocess.run(["git", "-C", str(local), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
        subprocess.run(["git", "-C", str(local), "push", "origin", "main"],
                      check=True, capture_output=True, timeout=30)
        return True, "Committed", sha
    except Exception as e:
        return False, str(e), None


def list_inbox_tasks() -> list[str]:
    """List task files currently in tasks/inbox/."""
    local = ensure_local_clone()
    inbox = local / "tasks" / "inbox"
    if not inbox.exists():
        return []
    return sorted([f.name for f in inbox.iterdir() if f.suffix == ".json" and f.name != ".gitkeep"])


def read_task_file(task_filename: str) -> Optional[str]:
    """Read a task file from inbox. Returns content or None."""
    local = ensure_local_clone()
    path = local / "tasks" / "inbox" / task_filename
    if not path.exists():
        return None
    return path.read_text()


def get_task_commit_sha() -> Optional[str]:
    """Get the HEAD commit SHA of the local clone."""
    local = ensure_local_clone()
    try:
        return subprocess.run(
            ["git", "-C", str(local), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return None