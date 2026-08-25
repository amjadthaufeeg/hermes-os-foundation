"""Hermes Builder Dispatch Adapter.

This component is orchestration-only. It launches exactly one approved builder
for an immutable task packet. It never invokes a shell and never changes HOS
authority semantics.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_BUILDERS = {"kimi-k3", "codex"}
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")
FORBIDDEN_BRANCHES = {"main", "master", "production", "prod", "hos-auto-02-r2"}
DEFAULT_PATH = ("/usr/local/bin", "/usr/bin", "/bin")


class DispatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuilderJob:
    task_id: str
    builder: str
    repository: str
    working_directory: str
    branch: str
    baseline_commit: str
    contract_path: str
    timeout_seconds: int = 1800

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuilderJob":
        return cls(
            task_id=str(data.get("task_id", "")),
            builder=str(data.get("builder", "")),
            repository=str(data.get("repository", "")),
            working_directory=str(data.get("working_directory", "")),
            branch=str(data.get("branch", "")),
            baseline_commit=str(data.get("baseline_commit", "")),
            contract_path=str(data.get("contract_path", "")),
            timeout_seconds=int(data.get("timeout_seconds", 1800)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not TASK_ID_RE.fullmatch(self.task_id):
            errors.append("invalid task_id")
        if self.builder not in ALLOWED_BUILDERS:
            errors.append("builder must be kimi-k3 or codex")
        if not self.repository or "/" not in self.repository:
            errors.append("repository must be owner/name")
        if not os.path.isabs(self.working_directory):
            errors.append("working_directory must be absolute")
        if self.branch in FORBIDDEN_BRANCHES or not self.branch:
            errors.append("protected or empty branch")
        if not SHA_RE.fullmatch(self.baseline_commit):
            errors.append("invalid baseline_commit")
        if not os.path.isabs(self.contract_path):
            errors.append("contract_path must be absolute")
        if not (30 <= self.timeout_seconds <= 7200):
            errors.append("timeout_seconds out of range")
        return errors


@dataclass(frozen=True)
class BuilderSpec:
    executable: str
    args: tuple[str, ...]
    pass_env: tuple[str, ...] = ()
    path_entries: tuple[str, ...] = DEFAULT_PATH


def _secure_config(path: Path) -> None:
    st = path.stat()
    if st.st_uid not in (0, os.geteuid()):
        raise DispatchError("builder config owner is not trusted")
    if st.st_mode & 0o022:
        raise DispatchError("builder config must not be group/world writable")


def _validate_path_entries(raw: Any, builder: str) -> tuple[str, ...]:
    entries = tuple(str(x) for x in (raw if isinstance(raw, list) else DEFAULT_PATH))
    if not entries:
        raise DispatchError(f"{builder}: PATH cannot be empty")
    for entry in entries:
        if not os.path.isabs(entry) or "\x00" in entry:
            raise DispatchError(f"{builder}: PATH entries must be absolute")
    return entries


def load_config(path: str, *, enforce_permissions: bool = True) -> dict[str, BuilderSpec]:
    p = Path(path)
    if enforce_permissions:
        _secure_config(p)
    data = json.loads(p.read_text())
    specs: dict[str, BuilderSpec] = {}
    for builder, raw in data.get("builders", {}).items():
        if builder not in ALLOWED_BUILDERS:
            continue
        exe = str(raw.get("executable", ""))
        if not os.path.isabs(exe):
            raise DispatchError(f"{builder}: executable must be absolute")
        args = tuple(str(x) for x in raw.get("args", []))
        pass_env = tuple(str(x) for x in raw.get("pass_env", []))
        path_entries = _validate_path_entries(raw.get("path_entries", list(DEFAULT_PATH)), builder)
        specs[builder] = BuilderSpec(executable=exe, args=args, pass_env=pass_env, path_entries=path_entries)
    return specs


def _render(arg: str, *, job: BuilderJob, job_file: str) -> str:
    values = {
        "{task_id}": job.task_id,
        "{job_file}": job_file,
        "{working_directory}": job.working_directory,
        "{branch}": job.branch,
        "{baseline_commit}": job.baseline_commit,
        "{contract_path}": job.contract_path,
        "{repository}": job.repository,
    }
    out = arg
    for key, value in values.items():
        out = out.replace(key, value)
    return out


def _job_hash(job: BuilderJob) -> str:
    payload = {
        "task_id": job.task_id,
        "builder": job.builder,
        "repository": job.repository,
        "working_directory": job.working_directory,
        "branch": job.branch,
        "baseline_commit": job.baseline_commit,
        "contract_path": job.contract_path,
        "timeout_seconds": job.timeout_seconds,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def dispatch(job: BuilderJob, spec: BuilderSpec, *, state_dir: str = "/var/lib/hermes-builder") -> dict[str, Any]:
    errors = job.validate()
    if errors:
        raise DispatchError("; ".join(errors))
    workdir = Path(job.working_directory)
    contract = Path(job.contract_path)
    if not workdir.is_dir():
        raise DispatchError("working_directory does not exist")
    if not contract.is_file():
        raise DispatchError("contract_path does not exist")
    if not Path(spec.executable).is_file() or not os.access(spec.executable, os.X_OK):
        raise DispatchError("builder executable does not exist or is not executable")

    state = Path(state_dir)
    (state / "locks").mkdir(parents=True, exist_ok=True)
    (state / "jobs").mkdir(parents=True, exist_ok=True)
    lock_key = hashlib.sha256(f"{job.repository}:{job.branch}".encode()).hexdigest()
    lock_path = state / "locks" / f"{lock_key}.lock"

    started = time.time()
    with lock_path.open("w") as lock_fp:
        try:
            fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DispatchError("branch already has an active builder") from exc

        job_payload = {
            "task_id": job.task_id,
            "builder": job.builder,
            "repository": job.repository,
            "working_directory": job.working_directory,
            "branch": job.branch,
            "baseline_commit": job.baseline_commit,
            "contract_path": job.contract_path,
            "timeout_seconds": job.timeout_seconds,
            "job_sha256": _job_hash(job),
        }
        job_file = state / "jobs" / f"{job.task_id}.json"
        tmp = job_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(job_payload, indent=2))
        os.replace(tmp, job_file)

        cmd = [spec.executable] + [_render(arg, job=job, job_file=str(job_file)) for arg in spec.args]
        env = {
            "PATH": ":".join(spec.path_entries),
            "HOME": os.environ.get("HOME", "/nonexistent"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", ""),
        }
        for key in spec.pass_env:
            if key in os.environ:
                env[key] = os.environ[key]

        proc = subprocess.run(
            cmd,
            cwd=job.working_directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=job.timeout_seconds,
            shell=False,
        )
        finished = time.time()
        return {
            "task_id": job.task_id,
            "builder": job.builder,
            "status": "COMPLETED" if proc.returncode == 0 else "FAILED",
            "exit_code": proc.returncode,
            "duration_seconds": round(finished - started, 3),
            "job_sha256": job_payload["job_sha256"],
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "command_executable": spec.executable,
            "branch": job.branch,
            "baseline_commit": job.baseline_commit,
        }


def dispatch_from_files(job_path: str, config_path: str, result_path: str, *, state_dir: str = "/var/lib/hermes-builder") -> int:
    job = BuilderJob.from_dict(json.loads(Path(job_path).read_text()))
    specs = load_config(config_path)
    if job.builder not in specs:
        raise DispatchError(f"no configured adapter for {job.builder}")
    result = dispatch(job, specs[job.builder], state_dir=state_dir)
    out = Path(result_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2))
    os.replace(tmp, out)
    return 0 if result["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    parser.add_argument("config")
    parser.add_argument("result")
    parser.add_argument("--state-dir", default="/var/lib/hermes-builder")
    args = parser.parse_args()
    raise SystemExit(dispatch_from_files(args.job, args.config, args.result, state_dir=args.state_dir))
