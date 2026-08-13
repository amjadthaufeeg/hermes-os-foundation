"""HOS-AUTO-01 R1b — Privileged Docker Broker (hardened).

Root-owned, independently validating proxy for Docker operations.
Accepts typed operation requests via JSON stdin. Bridge is unprivileged.
No Docker socket exposed to Bridge. No arbitrary CLI forwarding.
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field


# ─── Disposable Namespace (hardened) ───────────────────────────────

DISPOSABLE_PREFIX = "hermes-b5-lab-"
# Image policy: disposable images ONLY. Production image (prod-*) is NOT allowed
# for disposable lab containers. Local-only images built from this repo.
ALLOWED_IMAGE_PREFIXES = ("disposable-",)
ALLOWED_HOST_ROOT = "/tmp/hermes-b5-lab"
ALLOWED_NETWORKS = ("none", "hermes-b5-lab-net")
# Absolute Docker binary path — do NOT trust caller-controlled PATH
DOCKER_BIN = "/usr/bin/docker"
MAX_REQUEST_BYTES = 65536  # 64KB

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

# Whitelist of allowed docker inspect format templates (no caller-controlled format)
ALLOWED_INSPECT_FORMATS = frozenset({
    "{{.Names}} {{.Status}}",
    "{{.Name}}",
    "{{.State.Status}}",
    "{{.Image}}",
})

# Container name charset: lowercase, digits, hyphen only
NAME_RE = re.compile(r"^[a-z0-9-]+$")


@dataclass
class ValidationResult:
    allowed: bool = False
    reason: str = ""
    warnings: list = field(default_factory=list)


def _canonicalize(path: str) -> str:
    """Resolve symlinks + collapse traversal. Returns canonical path or raw."""
    try:
        return os.path.realpath(path)
    except OSError:
        return os.path.abspath(path)


def _is_within(path: str, root: str) -> bool:
    """True if path is within root, after canonicalization."""
    canon_path = _canonicalize(path)
    canon_root = _canonicalize(root)
    return canon_path == canon_root or canon_path.startswith(canon_root + os.sep)


def validate_container_name(name: str) -> ValidationResult:
    if not name.startswith(DISPOSABLE_PREFIX):
        return ValidationResult(False, f"Container name must start with '{DISPOSABLE_PREFIX}', got: {name}")
    if name in BLOCKED_CONTAINER_NAMES:
        return ValidationResult(False, f"Container name '{name}' is blocked (production resource)")
    if not NAME_RE.match(name):
        return ValidationResult(False, f"Container name contains illegal characters: {name}")
    return ValidationResult(True, "OK")


def validate_image(image: str) -> ValidationResult:
    # Disposable images only. Reject production image (prod-*).
    if not any(image.startswith(p) for p in ALLOWED_IMAGE_PREFIXES):
        return ValidationResult(False, f"Image '{image}' not in disposable allowlist")
    if image in BLOCKED_CONTAINER_NAMES:
        return ValidationResult(False, f"Image '{image}' is blocked")
    if any(c in image for c in (";", "|", "&", ">", "<", "`", "$", " ")):
        return ValidationResult(False, f"Image '{image}' contains shell metacharacters")
    return ValidationResult(True, "OK")


def validate_mount(source: str, destination: str, mode: str) -> ValidationResult:
    # Canonicalize source to defeat symlink/path-traversal attacks
    canon_source = _canonicalize(source)

    # Block production paths (check both raw and canonical)
    for blocked in BLOCKED_VOLUME_SOURCES:
        if canon_source.startswith(blocked) or source.startswith(blocked):
            return ValidationResult(False, f"Mount source '{source}' matches blocked production path: {blocked}")
    for blocked in BLOCKED_PATH_PREFIXES:
        if canon_source.startswith(blocked):
            return ValidationResult(False, f"Mount source '{source}' blocked by prefix: {blocked}")

    # Source must be strictly within the disposable host root (canonicalized)
    if not _is_within(source, ALLOWED_HOST_ROOT):
        return ValidationResult(False, f"Mount source '{source}' outside disposable root '{ALLOWED_HOST_ROOT}'")

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
        name = var.split("=", 1)[0].strip() if "=" in var else var.strip()
        if name in BLOCKED_ENV_VARS:
            return ValidationResult(False, f"Environment variable '{name}' is blocked")
        if any(c in name for c in (";", "|", "&", "`", "$", " ")):
            return ValidationResult(False, f"Environment variable name contains illegal characters: {name}")
    return ValidationResult(True, "OK")


def validate_caps(caps: list[str]) -> ValidationResult:
    for cap in caps:
        if cap in BLOCKED_CAPS:
            return ValidationResult(False, f"Capability '{cap}' is blocked")
    return ValidationResult(True, "OK")


def validate_host_path(path: str) -> ValidationResult:
    canon = _canonicalize(path)
    candidates = {path, canon}
    for blocked in BLOCKED_VOLUME_SOURCES:
        if any(c.startswith(blocked) for c in candidates):
            return ValidationResult(False, f"Path '{path}' matches blocked production path: {blocked}")
    for blocked in BLOCKED_PATH_PREFIXES:
        if any(c.startswith(blocked) for c in candidates):
            return ValidationResult(False, f"Path '{path}' blocked by prefix: {blocked}")
    return ValidationResult(True, "OK")


# ─── Operation Handlers ────────────────────────────────────────────

def _docker(args: list[str], timeout: int = 30) -> dict:
    """Run a Docker command with absolute path, fixed env, no shell."""
    env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    try:
        result = subprocess.run(
            [DOCKER_BIN] + args, capture_output=True, text=True,
            timeout=timeout, env=env,
        )
        return {"allowed": True, "exit_code": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"allowed": False, "reason": f"Timeout after {timeout}s", "exit_code": 124}
    except Exception as e:
        return {"allowed": False, "reason": str(e), "exit_code": 1}


def handle_inspect(params: dict) -> dict:
    name = params["container_name"]
    fmt = params.get("format", "{{.Names}} {{.Status}}")
    v = validate_container_name(name)
    if not v.allowed:
        return {"allowed": False, "reason": v.reason}
    # Reject caller-controlled format strings — allowlist only
    if fmt not in ALLOWED_INSPECT_FORMATS:
        return {"allowed": False, "reason": f"Format string not in allowlist: {fmt}"}
    return _docker(["inspect", name, "--format", fmt])


def _validate_readonly_target(name: str) -> ValidationResult:
    """Read-only observation target — any valid container name/timer allowed."""
    if not NAME_RE.match(name):
        return ValidationResult(False, f"Invalid target name: {name}")
    return ValidationResult(True, "OK")


def handle_inspect_container(params: dict) -> dict:
    """Read-only docker inspect of ANY container (including production, for observation)."""
    name = params["container_name"]
    fmt = params.get("format", "{{.Names}} {{.Status}}")
    v = _validate_readonly_target(name)
    if not v.allowed:
        return {"allowed": False, "reason": v.reason}
    if fmt not in ALLOWED_INSPECT_FORMATS:
        return {"allowed": False, "reason": f"Format string not in allowlist: {fmt}"}
    return _docker(["inspect", name, "--format", fmt])


def handle_inspect_timer(params: dict) -> dict:
    """Read-only systemctl list-timers for any timer name."""
    name = params["timer_name"]
    if not NAME_RE.match(name):
        return {"allowed": False, "reason": f"Invalid timer name: {name}"}
    try:
        result = subprocess.run(
            ["systemctl", "list-timers", name, "--no-pager"],
            capture_output=True, text=True, timeout=15,
            env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"},
        )
        return {"allowed": True, "exit_code": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except Exception as e:
        return {"allowed": False, "reason": str(e), "exit_code": 1}


def handle_create(params: dict) -> dict:
    name = params["container_name"]
    image = params["image"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    v = validate_image(image)
    if not v.allowed: return {"allowed": False, "reason": v.reason}

    # Fixed hardened flags — caller cannot override these
    cmd = [
        "create",
        "--name", name,
        "--network", params.get("network", "none"),
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--user", params.get("user", "10010:10010"),
        "--pids-limit", "128",
        "--memory", "256m",
        "--cpus", "1.0",
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
    return _docker(cmd, timeout=120)


def handle_start(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    return _docker(["start", name])


def handle_stop(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    return _docker(["stop", name])


def handle_remove(params: dict) -> dict:
    name = params["container_name"]
    v = validate_container_name(name)
    if not v.allowed: return {"allowed": False, "reason": v.reason}
    return _docker(["rm", "-f", name])


def handle_create_network(params: dict) -> dict:
    name = params["network_name"]
    if not name.startswith("hermes-b5-lab-"):
        return {"allowed": False, "reason": f"Network name must start with 'hermes-b5-lab-', got: {name}"}
    return _docker(["network", "create", name, "--internal"])


def handle_remove_network(params: dict) -> dict:
    name = params["network_name"]
    if not name.startswith("hermes-b5-lab-"):
        return {"allowed": False, "reason": f"Network name must start with 'hermes-b5-lab-', got: {name}"}
    return _docker(["network", "rm", name])


HANDLERS = {
    "inspect_disposable_container": handle_inspect,
    "inspect_container": handle_inspect_container,
    "inspect_timer": handle_inspect_timer,
    "create_disposable_container": handle_create,
    "start_disposable_container": handle_start,
    "stop_disposable_container": handle_stop,
    "remove_disposable_container": handle_remove,
    "create_disposable_network": handle_create_network,
    "remove_disposable_network": handle_remove_network,
}

ALLOWED_OPERATIONS = frozenset(HANDLERS.keys())


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
        raw = sys.stdin.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            print(json.dumps({"allowed": False, "reason": "Request exceeds size limit"}))
            sys.exit(1)
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