"""Concurrency-safe wrapper for HOS-AUTO-02 Git transport.

Preserves the certified transport endpoints/credentials while making writes
safe when ChatGPT and Hermes advance the private control repository at nearly
the same time. It also suppresses already-completed file tasks from the legacy
inbox so immutable files do not generate replay commits forever.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from deploy.hos_auto_02 import transport as legacy

REPO_URL = legacy.REPO_URL
TRANSPORT_BRANCH = legacy.TRANSPORT_BRANCH
INBOX_PATH = legacy.INBOX_PATH

ensure_local_clone = legacy.ensure_local_clone
read_task_file = legacy.read_task_file
get_task_commit_sha = legacy.get_task_commit_sha
list_issue_tasks = legacy.list_issue_tasks
read_issue_task = legacy.read_issue_task


def _sync_rebase(local: Path) -> tuple[bool, str]:
    """Fetch and rebase local unpublished transport commits onto origin/main."""
    try:
        fetch = subprocess.run(
            ["git", "-C", str(local), "fetch", "origin", TRANSPORT_BRANCH],
            capture_output=True, text=True, timeout=30, env=legacy._ssh_env(),
        )
        if fetch.returncode != 0:
            return False, fetch.stderr.strip() or fetch.stdout.strip()
        rebase = subprocess.run(
            ["git", "-C", str(local), "rebase", f"origin/{TRANSPORT_BRANCH}"],
            capture_output=True, text=True, timeout=30, env=legacy._ssh_env(),
        )
        if rebase.returncode != 0:
            subprocess.run(
                ["git", "-C", str(local), "rebase", "--abort"],
                capture_output=True, text=True, timeout=10,
            )
            return False, rebase.stderr.strip() or rebase.stdout.strip()
        return True, "synced"
    except Exception as exc:
        return False, str(exc)


def git_pull() -> tuple[bool, str]:
    local = ensure_local_clone()
    return _sync_rebase(local)


def git_commit_and_push(
    files: list[tuple[str, str]], message: str
) -> tuple[bool, str, Optional[str]]:
    """Commit and push with bounded fetch/rebase retry on non-fast-forward races."""
    local = ensure_local_clone()
    try:
        ok, msg = _sync_rebase(local)
        if not ok:
            return False, f"sync failed: {msg}", None

        for path, content in files:
            full_path = local / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        subprocess.run(
            ["git", "-C", str(local), "add", "-A"],
            check=True, capture_output=True, timeout=10,
        )
        staged = subprocess.run(
            ["git", "-C", str(local), "diff", "--cached", "--quiet"],
            timeout=10,
        )
        if staged.returncode == 0:
            sha = subprocess.run(
                ["git", "-C", str(local), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            return True, "No changes", sha

        subprocess.run(
            [
                "git", "-C", str(local),
                "-c", "user.name=Hermes R2 Watcher",
                "-c", "user.email=hermes-r2@localhost",
                "commit", "-m", message,
            ],
            check=True, capture_output=True, timeout=10,
        )

        for attempt in range(3):
            push = subprocess.run(
                ["git", "-C", str(local), "push", "origin", TRANSPORT_BRANCH],
                capture_output=True, text=True, timeout=30, env=legacy._ssh_env(),
            )
            if push.returncode == 0:
                sha = subprocess.run(
                    ["git", "-C", str(local), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
                return True, f"Committed (attempt {attempt + 1})", sha

            ok, sync_msg = _sync_rebase(local)
            if not ok:
                return False, f"push conflict; rebase failed: {sync_msg}", None

        return False, "push failed after 3 rebase retries", None
    except Exception as exc:
        return False, str(exc), None


def list_inbox_tasks() -> list[str]:
    """Return only inbox tasks that do not already have a completed result."""
    local = ensure_local_clone()
    inbox = local / INBOX_PATH
    completed = local / "tasks" / "completed"
    if not inbox.exists():
        return []
    names = []
    for path in sorted(inbox.iterdir()):
        if path.suffix != ".json" or path.name == ".gitkeep":
            continue
        task_id = path.stem
        if (completed / f"{task_id}.json").exists():
            continue
        names.append(path.name)
    return names
