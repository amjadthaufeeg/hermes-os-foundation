"""Sanitized status/reconciliation reporter for Hermes Builder.

Runs as the dedicated hermesbuilder account. It may inspect the builder's local
control clone and Git metadata, but publishes only non-secret operational data
to /Users/Shared/HermesBuilderReports for review from the main account.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONTROL = Path.home() / "Library" / "Application Support" / "HermesBuilder" / "hermes-control"
ROOT = Path.home() / "Library" / "Application Support" / "HermesBuilder"
REPORT_ROOT = Path(os.environ.get("HERMES_REPORT_ROOT", "/Users/Shared/HermesBuilderReports"))
REPO_URL = "git@github.com:amjadthaufeeg/hermes-control.git"
EXPECTED_PREFIXES = (
    "builders/worker-status/",
    "builders/claims/",
    "builders/completed/",
    "builders/stopped/",
    "builders/inbox/",
    "tasks/inbox/",
    "tasks/claims/",
    "tasks/completed/",
    "tasks/stopped/",
)


def _env() -> dict[str, str]:
    key = Path(os.environ.get("HERMES_CONTROL_SSH_KEY", str(Path.home() / ".ssh" / "hermes-control-deploy")))
    known = Path.home() / ".ssh" / "hermes-builder-known_hosts"
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(Path.home()),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "SSH_AUTH_SOCK": "",
        "GIT_SSH_COMMAND": (
            f"/usr/bin/ssh -i {key} -o IdentitiesOnly=yes -o BatchMode=yes "
            f"-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile={known}"
        ),
    }


def _run(args: list[str], *, cwd: Path = CONTROL, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), env=_env(), capture_output=True, text=True, timeout=timeout, shell=False)


def _git(*args: str, timeout: int = 60) -> str:
    p = _run(["git", "-c", "core.hooksPath=/dev/null", *args], timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-500:])
    return p.stdout.strip()


def _safe_status() -> dict:
    status_path = ROOT / "worker-status.json"
    if not status_path.is_file():
        return {"status": "UNKNOWN"}
    try:
        raw = json.loads(status_path.read_text())
    except Exception:
        return {"status": "INVALID"}
    allowed = {"status", "host", "source_sha", "user", "admin", "isolation", "kimi_model", "verified_at"}
    return {k: raw[k] for k in allowed if k in raw}


def _commit_details(ref_range: str) -> list[dict]:
    shas = [x for x in _git("rev-list", "--reverse", ref_range).splitlines() if x]
    out = []
    for sha in shas[:50]:
        msg = _git("show", "-s", "--format=%s", sha)
        files = [x for x in _git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines() if x]
        transport_only = all(any(f.startswith(prefix) for prefix in EXPECTED_PREFIXES) for f in files)
        out.append({"sha": sha, "message": msg, "files": files, "transport_only": transport_only})
    return out


def build_report() -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "worker": _safe_status(),
        "control_repo": {"path": str(CONTROL), "exists": (CONTROL / ".git").is_dir()},
    }
    if not (CONTROL / ".git").is_dir():
        return report

    origin = _git("remote", "get-url", "origin")
    report["control_repo"]["origin"] = origin
    if origin != REPO_URL:
        report["control_repo"]["error"] = "unexpected origin"
        return report

    fetch = _run(["git", "-c", "core.hooksPath=/dev/null", "fetch", "origin", "main"], timeout=90)
    report["control_repo"]["fetch_ok"] = fetch.returncode == 0
    if fetch.returncode != 0:
        report["control_repo"]["fetch_error"] = (fetch.stderr or fetch.stdout).strip()[-500:]

    report["control_repo"]["branch"] = _git("rev-parse", "--abbrev-ref", "HEAD")
    report["control_repo"]["local_head"] = _git("rev-parse", "HEAD")
    report["control_repo"]["remote_main"] = _git("rev-parse", "origin/main")
    report["control_repo"]["working_tree_clean"] = not bool(_git("status", "--porcelain"))
    counts = _git("rev-list", "--left-right", "--count", "origin/main...HEAD").split()
    behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (-1, -1)
    report["control_repo"]["ahead_by"] = ahead
    report["control_repo"]["behind_by"] = behind
    ahead_commits = _commit_details("origin/main..HEAD") if ahead > 0 else []
    report["control_repo"]["ahead_commits"] = ahead_commits
    report["control_repo"]["all_ahead_transport_only"] = bool(ahead_commits) and all(c["transport_only"] for c in ahead_commits)
    if not ahead_commits:
        report["control_repo"]["all_ahead_transport_only"] = True
    return report


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    os.chmod(REPORT_ROOT, 0o755)
    report = build_report()
    target = REPORT_ROOT / "status-and-reconciliation.json"
    tmp = REPORT_ROOT / ".status-and-reconciliation.tmp"
    tmp.write_text(json.dumps(report, indent=2) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
