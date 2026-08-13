"""HOS-AUTO-02 R2 — GitHub Transport (SSH deploy key).

Git pull/push via SSH deploy key on private hermes-control repo.
REPO and BRANCH are hard-coded — tasks cannot alter transport config.
"""
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# HARD-CODED TRANSPORT — never configurable by task payload
REPO_URL = "git@github.com:amjadthaufeeg/hermes-control.git"
TRANSPORT_REPO = "amjadthaufeeg/hermes-control"
TRANSPORT_BRANCH = "main"
INBOX_PATH = "tasks/inbox"

# Credential: SSH deploy key at fixed path, root-owned, group-readable
DEPLOY_KEY = os.environ.get("R2_DEPLOY_KEY", "/opt/hermes-auto/creds/deploy-key")
LOCAL_CLONE = os.environ.get("R2_CONTROL_DIR", "/var/lib/hermes-auto/hermes-control")


def ensure_local_clone() -> Path:
    """Ensure the local clone exists and is up to date."""
    local = Path(LOCAL_CLONE)
    if not (local / ".git").exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes"
        subprocess.run(
            ["git", "clone", "-q", "--branch", TRANSPORT_BRANCH, REPO_URL, str(local)],
            check=True, capture_output=True, env=env,
        )
    return local


def git_pull() -> tuple[bool, str]:
    """Pull latest from main via SSH deploy key. Returns (success, message)."""
    local = ensure_local_clone()
    try:
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes"
        result = subprocess.run(
            ["git", "-C", str(local), "pull", "--ff-only", "origin", TRANSPORT_BRANCH],
            capture_output=True, text=True, timeout=30, env=env,
        )
        # Validate remote is correct
        remote_url = subprocess.run(
            ["git", "-C", str(local), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if remote_url != REPO_URL:
            return False, f"Remote mismatch: {remote_url} != {REPO_URL}"
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def git_commit_and_push(files: list[tuple[str, str]], message: str) -> tuple[bool, str, Optional[str]]:
    """Commit files and push to main via SSH deploy key. Returns (success, message, commit_sha)."""
    local = ensure_local_clone()
    try:
        for path, content in files:
            full_path = local / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes"
        subprocess.run(["git", "-C", str(local), "add", "-A"],
                      check=True, capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(local), "commit", "-m", message],
                      check=True, capture_output=True, timeout=10)
        sha = subprocess.run(["git", "-C", str(local), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
        subprocess.run(["git", "-C", str(local), "push", "origin", TRANSPORT_BRANCH],
                      check=True, capture_output=True, timeout=30, env=env)
        return True, "Committed", sha
    except Exception as e:
        return False, str(e), None


def list_inbox_tasks() -> list[str]:
    local = ensure_local_clone()
    inbox = local / INBOX_PATH
    if not inbox.exists():
        return []
    return sorted([f.name for f in inbox.iterdir() if f.suffix == ".json" and f.name != ".gitkeep"])


def read_task_file(task_filename: str) -> Optional[str]:
    local = ensure_local_clone()
    path = local / INBOX_PATH / task_filename
    if not path.exists():
        return None
    return path.read_text()


def get_task_commit_sha() -> Optional[str]:
    local = ensure_local_clone()
    try:
        return subprocess.run(
            ["git", "-C", str(local), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return None