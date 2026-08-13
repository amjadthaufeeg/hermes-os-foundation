"""HOS-AUTO-01 Preflight — Test Environment Validation.

Ensures the execution environment is complete before any test suite runs.
Failure classification: TEST_ENVIRONMENT_INVALID (never FULL_REGRESSION_FAILED).
"""
import importlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PreflightResult:
    passed: bool = False
    checks: list = field(default_factory=list)
    fingerprint: Optional[str] = None


REQUIRED_MODULES = [
    "fastapi", "pydantic", "uvicorn", "requests",
    "yaml", "httpx", "pytest", "starlette", "cryptography",
]

REQUIRED_BINARIES = ["python3", "pytest", "git", "sqlite3"]


def check_module_import(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, f"IMPORT_OK: {module_name}"
    except ImportError as e:
        return False, f"MISSING: {module_name} ({e})"


def check_binary(binary: str) -> tuple[bool, str]:
    result = subprocess.run(["which", binary], capture_output=True, text=True)
    if result.returncode == 0:
        return True, f"BINARY_OK: {binary} → {result.stdout.strip()}"
    return False, f"MISSING_BINARY: {binary}"


def check_python_version(min_version: tuple = (3, 11)) -> tuple[bool, str]:
    v = sys.version_info[:2]
    ok = v >= min_version
    return ok, f"PYTHON_{v[0]}.{v[1]} {'OK' if ok else f'REQUIRES>=3.{min_version[1]}'}"


def check_source_sha(expected_sha: Optional[str] = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=os.getcwd(),
        )
        actual = result.stdout.strip()
        if expected_sha is None:
            return True, f"GIT_SHA: {actual[:12]} (no expected SHA)"
        ok = actual == expected_sha
        return ok, f"GIT_SHA: {'MATCH' if ok else f'MISMATCH expected={expected_sha[:12]} got={actual[:12]}'}"
    except Exception as e:
        return False, f"GIT_SHA_ERROR: {e}"


def run(expected_sha: Optional[str] = None) -> PreflightResult:
    result = PreflightResult()

    # Python version
    result.checks.append(check_python_version())

    # Required modules
    for mod in REQUIRED_MODULES:
        result.checks.append(check_module_import(mod))

    # Required binaries
    for bin in REQUIRED_BINARIES:
        result.checks.append(check_binary(bin))

    # Source SHA
    result.checks.append(check_source_sha(expected_sha))

    # Determine pass/fail
    result.passed = all(ok for ok, _ in result.checks)
    if not result.passed:
        failed = [msg for ok, msg in result.checks if not ok]
        print("PREFLIGHT FAILED — TEST_ENVIRONMENT_INVALID")
        for msg in failed:
            print(f"  {msg}")
    else:
        print("PREFLIGHT PASSED")
        for ok, msg in result.checks:
            print(f"  {msg}")

    # Environment fingerprint
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    result.fingerprint = f"python={py_ver}|git={expected_sha or 'none'}|cwd={os.getcwd()}"
    print(f"FINGERPRINT: {result.fingerprint}")

    return result


if __name__ == "__main__":
    result = run()
    sys.exit(0 if result.passed else 2)