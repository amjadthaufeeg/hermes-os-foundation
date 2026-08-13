"""HOS-AUTO-01 R1b — Privileged Docker Broker.

Root-owned, independently validating proxy for Docker operations.
Accepts typed operation requests via JSON stdin. Bridge is unprivileged.
No Docker socket exposed to Bridge. No arbitrary CLI forwarding.
"""
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


# ─── Disposable Namespace ──────────────────────────────────────────

DISPOSABLE_PREFIX = "hermes-b5-lab-"
ALLOWED_IMAGE_PREFIXES = ("hermes-product-os-hpos:", "disposable-")
ALLOWED_HOST_ROOT = "/tmp/hermes-b5-lab"
ALLOWED_NETWORKS = ("none", "hermes-b5-lab-net")

# ─── Hard-blocked Production Resources ────────────────────────────

BLOCKED_CONTAINER_NAMES = frozenset({
    "hermes-product-os-prod",
    "hermes-phase-b-reader",
    "hermes-product-os",
    "hermes-product-os-test-b",
})

BLOCKED_VOLUME_SOURCES = frozenset({
    "/var/lib/docker/volumes/hermes-product-os-prod",
    "/var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data",
    "/var/lib/docker/volumes/hermes-product-os_hpos-data",
    "/var/lib/docker/volumes/hermes-product-os_hpos-backup",
    "/var/lib/hermes/snapshots/production",
    "/var/lib/hermes/snapshots",
    "/etc/hermes-product-os-prod",
    "/etc/hermes-product-os",
    "/opt/hermes/data",
    "/production.db",
})

BLOCKED_PATH_PREFIXES = (
    "/var/run/docker.sock",
    "/var/lib/docker/volumes/",
    "/etc/",
    "/opt/hermes/",
    "/root/",
    "/home/",
)

BLOCKED_ENV_VARS = frozenset({
    "MUTATIONS_DISABLED", "DATABASE_PATH", "HERMES_ENVIRONMENT",
    "SIMULATION_MODE", "SNAPSHOT_FRESHNESS_ENFORCED",
})

BLOCKED_CAPS = frozenset({"ALL", "SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE"})


# ─── Typed Operation Definitions ───────────────────────────────────

ALLOWED_OPERATIONS = frozenset({
    "create_disposable_container",
    "start_disposable_container",
    "stop_disposable_container",
    "remove_disposable_container",
    "inspect_disposable_container",
    "build_disposable_image",
    "create_disposable_network",
    "remove_disposable_network",
})


@dataclass
class ValidationResult:
    allowed: bool = False
    reason: str = ""
    warnings: list = field(default_factory=list)


def validate_container_name(name: str) -> ValidationResult:
    if not name.startswith(DISPOSABLE_PREFIX):
        return ValidationResult(False, f"Container name must start with '{DISPOSABLE_PREFIX}', got: {name}")
    if name in BLOCKED_CONTAINER_NAMES:
        return ValidationResult(False, f"Container name '{name}' is blocked (production resource)")
    if "/" in name or ".." in name:
        return ValidationResult(False, f"Container name contains illegal characters: {name}")
    return ValidationResult(True, "OK")


def validate_image(image: str) -> ValidationResult:
    if not any(image.startswith(p) for p in ALLOWED_IMAGE_PREFIXES):
        return ValidationResult(False, f"Image '{image}' not in allowlist. Must be disposable")
    if image in BLOCKED_CONTAINER_NAMES:
        return ValidationResult(False, f"Image name '{image}' is blocked")
    return ValidationResult(True, "OK")


def validate_mount(source: str, destination: str, mode: str) -> ValidationResult:
    # Block production paths
    for blocked in BLOCKED_VOLUME_SOURCES:
        if source.startswith(blocked):
            return ValidationResult(False, f"Mount source '{source}' matches blocked production path: {blocked}")
    for blocked in BLOCKED_PATH_PREFIXES:
        if source.startswith(blocked) and not source.startswith(ALLOWED_HOST_ROOT):
            return ValidationResult(False, f"Mount source '{source}' blocked by prefix: {blocked}")

    if not source.startswith(ALLOWED_HOST_ROOT) and not source.startswith("/tmp/"):
        return ValidationResult(False, f"Mount source '{source}' outside allowed roots")

    if source in ("/", "/etc", "/var", "/opt", "/home"):
        return ValidationResult(False, f"Root-level mount blocked: {source}")

    if ".." in source or ".." in destination:
        return ValidationResult(False, "Path traversal detected in mount")

    if mode not in ("ro", "rw"):
        return ValidationResult(False, f"Mount mode must be 'ro' or 'rw', got: {mode}")

    return ValidationResult(True, "OK")


def validate_network(net: str) -> ValidationResult:
    if net not in ALLOWED_NETWORKS:
        return ValidationResult(False, f"Network '{net}' not allowed. Must be one of: {ALLOWED_NETWORKS}")
    return ValidationResult(True, "OK")


def validate_env(env: list[str]) -> ValidationResult:
    for var in env:
        name = var.split("=")[0] if "=" in var else var
        if name in BLOCKED_ENV_VARS:
            return ValidationResult(False, f"Environment variable '{name}' is blocked")
    return ValidationResult(True, "OK")


def validate_caps(caps: list[str]) -> ValidationResult:
    for cap in caps:
        if cap in BLOCKED_CAPS:
            return ValidationResult(False, f"Capability '{cap}' is blocked")
    return ValidationResult(True, "OK")


def validate_host_path(path: str) -> ValidationResult:
    try:
        resolved = os.path.realpath(path)
    except OSError:
        resolved = path
    # Check both raw and resolved against blocked sources
    candidates = {path, resolved}
    for blocked in BLOCKED_VOLUME_SOURCES:
        if any(c.startswith(blocked) for c in candidates):
            return ValidationResult(False, f"Path '{path}' matches blocked production path: {blocked}")
    for blocked in BLOCKED_PATH_PREFIXES:
        if any(c.startswith(blocked) for c in candidates) and not any(c.startswith(ALLOWED_HOST_ROOT) for c in candidates):
            return ValidationResult(False, f"Path '{path}' blocked by prefix: {blocked}")
    return ValidationResult(True, "OK")


# ─── Operation Handlers ────────────────────────────────────────────

def handle_inspect(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed:
        return {"allowed": False, "reason": v.reason}

    result = subprocess.run(
        ["docker", "inspect", name, "--format", params.get("format", "{{.Names}} {{.Status}}")],
        capture_output=True, text=True, timeout=30,
    )
    return {
        "allowed": True,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def handle_create(params: dict) -> dict:
    name = params["container_name"]
    image = params["image"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    v = validate_image(image)
    if not v.allowed: return {"allowed": False, "reason": v.reason}

    cmd = [
        "docker", "create",
        "--name", name,
        "--network", params.get("network", "none"),
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
    ]

    for mount in params.get("mounts", []):
        v = validate_mount(mount.get("source", ""), mount.get("destination", ""), mount.get("mode", "ro"))
        if not v.allowed: return {"allowed": False, "reason": v.reason}
        cmd += ["-v", f"{mount['source']}:{mount['destination']}:{mount['mode']}"]

    for env_var in params.get("env", []):
        v = validate_env([env_var])
        if not v.allowed: return {"allowed": False, "reason": v.reason}
        cmd += ["-e", env_var]

    cmd.append(image)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def handle_start(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    result = subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def handle_stop(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    result = subprocess.run(["docker", "stop", name], capture_output=True, text=True, timeout=30)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def handle_remove(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    result = subprocess.run(["docker", "rm", name], capture_output=True, text=True, timeout=30)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def handle_create_network(params: dict) -> dict:
    name = params["network_name"]
    if not name.startswith("hermes-b5-lab-"):
        return {"allowed": False, "reason": f"Network name must start with 'hermes-b5-lab-', got: {name}"}
    result = subprocess.run(["docker", "network", "create", name, "--internal"], capture_output=True, text=True, timeout=30)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def handle_remove_network(params: dict) -> dict:
    name = params["network_name"]
    if not name.startswith("hermes-b5-lab-"):
        return {"allowed": False, "reason": f"Network name must start with 'hermes-b5-lab-', got: {name}"}
    result = subprocess.run(["docker", "network", "rm", name], capture_output=True, text=True, timeout=30)
    return {"allowed": True, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


HANDLERS = {
    "inspect_disposable_container": handle_inspect,
    "create_disposable_container": handle_create,
    "start_disposable_container": handle_start,
    "stop_disposable_container": handle_stop,
    "remove_disposable_container": handle_remove,
    "create_disposable_network": handle_create_network,
    "remove_disposable_network": handle_remove_network,
}


# ─── Broker Main ───────────────────────────────────────────────────

def process_request(request: dict) -> dict:
    op_type = request.get("type", "")
    params = request.get("params", {})

    if op_type not in ALLOWED_OPERATIONS:
        return {"allowed": False, "reason": f"Operation '{op_type}' not in allowlist", "exit_code": 127}

    handler = HANDLERS.get(op_type)
    if not handler:
        return {"allowed": False, "reason": f"No handler for '{op_type}'", "exit_code": 127}

    return handler(params)


def main():
    try:
        raw = sys.stdin.read()
        request = json.loads(raw)
        response = process_request(request)
        print(json.dumps(response))
        sys.exit(0 if response.get("allowed") and response.get("exit_code", 0) == 0 else 1)
    except json.JSONDecodeError as e:
        print(json.dumps({"allowed": False, "reason": f"Invalid JSON: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"allowed": False, "reason": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()