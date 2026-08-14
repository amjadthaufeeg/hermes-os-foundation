"""HOS-AUTO-02 R2 — GitHub Transport.

Primary result/claim transport uses the repo-scoped SSH deploy key against the
private hermes-control repository. ChatGPT ingress may also arrive through a
structured GitHub Issue because the ChatGPT connector can create Issues even
when direct repository file writes are blocked by the platform safety layer.

Repo, branch, issue repository, credential paths, and task title prefix are
hard-coded — task payloads cannot alter transport configuration.
"""
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


# HARD-CODED TRANSPORT — never configurable by task payload
REPO_URL = "git@github.com:amjadthaufeeg/hermes-control.git"
TRANSPORT_REPO = "amjadthaufeeg/hermes-control"
TRANSPORT_BRANCH = "main"
INBOX_PATH = "tasks/inbox"
ISSUE_REPO = TRANSPORT_REPO
ISSUE_TITLE_PREFIX = "R2-TASK "
EXPECTED_ISSUE_AUTHOR = "amjadthaufeeg"

# Credentials are fixed file paths, never task-controlled.
DEPLOY_KEY = os.environ.get("R2_DEPLOY_KEY", "/opt/hermes-auto/creds/deploy-key")
ISSUES_TOKEN_FILE = os.environ.get("R2_ISSUES_TOKEN_FILE", "/opt/hermes-auto/creds/issues-token")
LOCAL_CLONE = os.environ.get("R2_CONTROL_DIR", "/var/lib/hermes-auto/hermes-control")
GITHUB_API = "https://api.github.com"


def _ssh_env() -> dict:
    env = os.environ.copy()
    # Use a known_hosts file under writable runtime state (ProtectHome=yes
    # blocks ~/.ssh for the systemd service).
    known_hosts = "/var/lib/hermes-auto/known_hosts"
    env["GIT_SSH_COMMAND"] = (
        f"ssh -i {DEPLOY_KEY} -o StrictHostKeyChecking=accept-new "
        f"-o IdentitiesOnly=yes -o UserKnownHostsFile={known_hosts}"
    )
    return env


def ensure_local_clone() -> Path:
    """Ensure the local clone exists and is up to date."""
    local = Path(LOCAL_CLONE)
    if not (local / ".git").exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "-q", "--branch", TRANSPORT_BRANCH, REPO_URL, str(local)],
            check=True, capture_output=True, env=_ssh_env(),
        )
    return local


def git_pull() -> tuple[bool, str]:
    """Pull latest from main via SSH deploy key. Returns (success, message)."""
    local = ensure_local_clone()
    try:
        result = subprocess.run(
            ["git", "-C", str(local), "pull", "--ff-only", "origin", TRANSPORT_BRANCH],
            capture_output=True, text=True, timeout=30, env=_ssh_env(),
        )
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
    """Commit files and push to main via SSH deploy key."""
    local = ensure_local_clone()
    try:
        for path, content in files:
            full_path = local / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        subprocess.run(["git", "-C", str(local), "add", "-A"],
                      check=True, capture_output=True, timeout=10)
        # Explicit author — hermes-auto has no global git identity.
        subprocess.run([
            "git", "-C", str(local),
            "-c", "user.name=Hermes R2 Watcher",
            "-c", "user.email=hermes-r2@localhost",
            "commit", "-m", message,
        ], check=True, capture_output=True, timeout=10)
        sha = subprocess.run(["git", "-C", str(local), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
        subprocess.run(["git", "-C", str(local), "push", "origin", TRANSPORT_BRANCH],
                      check=True, capture_output=True, timeout=30, env=_ssh_env())
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


# ─── GitHub Issue ingress (read-only token) ───────────────────────

def _read_issues_token() -> str:
    """Read the repo-scoped Issues:read token from the fixed credential path."""
    with open(ISSUES_TOKEN_FILE) as f:
        token = f.read().strip()
    if not token:
        raise RuntimeError("GitHub issues token is empty")
    return token


def _github_api_json(path: str) -> object:
    """GET JSON from GitHub API using the fixed read-only issue credential."""
    req = urllib.request.Request(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {_read_issues_token()}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "hermes-r2-watcher",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub issue API HTTP {e.code}") from e


def list_issue_tasks() -> list[dict]:
    """Return open structured R2 task issues from the private control repo.

    Only issues authored by the expected GitHub account and with the exact
    R2-TASK title prefix are returned. Pull requests are excluded.
    """
    owner, repo = ISSUE_REPO.split("/", 1)
    data = _github_api_json(f"/repos/{owner}/{repo}/issues?state=open&per_page=100")
    if not isinstance(data, list):
        return []
    tasks = []
    for item in data:
        if not isinstance(item, dict) or "pull_request" in item:
            continue
        title = item.get("title") or ""
        author = ((item.get("user") or {}).get("login") or "")
        if not title.startswith(ISSUE_TITLE_PREFIX):
            continue
        if author != EXPECTED_ISSUE_AUTHOR:
            continue
        tasks.append({
            "number": int(item["number"]),
            "title": title,
            "body": item.get("body") or "",
            "author": author,
            "updated_at": item.get("updated_at") or "",
        })
    return sorted(tasks, key=lambda x: x["number"])


def read_issue_task(issue_number: int) -> Optional[dict]:
    """Fetch one issue and return its immutable processing envelope."""
    owner, repo = ISSUE_REPO.split("/", 1)
    item = _github_api_json(f"/repos/{owner}/{repo}/issues/{int(issue_number)}")
    if not isinstance(item, dict) or "pull_request" in item:
        return None
    title = item.get("title") or ""
    author = ((item.get("user") or {}).get("login") or "")
    if not title.startswith(ISSUE_TITLE_PREFIX) or author != EXPECTED_ISSUE_AUTHOR:
        return None
    body = item.get("body") or ""
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {
        "number": int(item["number"]),
        "title": title,
        "body": body,
        "body_sha256": body_sha256,
        "author": author,
        "updated_at": item.get("updated_at") or "",
        "source_version": f"issue:{int(item['number'])}:{body_sha256}",
    }
