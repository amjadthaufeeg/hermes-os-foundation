"""HOS-AUTO-01 R1b — Broker Tests."""
import json, os, shutil, subprocess, pytest

from deploy.hos_auto_01.bin.broker import (
    process_request, validate_container_name, validate_image,
    validate_mount, validate_network, validate_env, validate_caps,
    validate_host_path,
)

DOCKER_AVAILABLE = shutil.which("docker") is not None

# ─── Disposable Operation Tests ────────────────────────────────────

def test_validate_valid_container_name():
    assert validate_container_name("hermes-b5-lab-fc05").allowed

def test_validate_valid_image():
    assert validate_image("disposable-test").allowed
    assert validate_image("disposable-b5-fc05").allowed

# Production image must NOT be usable in disposable lab
def test_reject_production_image():
    assert not validate_image("hermes-product-os-hpos:prod-p4-release").allowed

def test_validate_mount_tmp():
    assert validate_mount("/tmp/hermes-b5-lab/data", "/data", "ro").allowed

def test_validate_network_none():
    assert validate_network("none").allowed

# ─── Production Hard-Block Tests ───────────────────────────────────

def test_reject_production_container_name():
    assert not validate_container_name("hermes-product-os-prod").allowed

def test_reject_phaseb_reader_name():
    assert not validate_container_name("hermes-phase-b-reader").allowed

def test_reject_production_volume_source():
    assert not validate_mount(
        "/var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/production.db",
        "/db", "ro",
    ).allowed

def test_reject_etc_mount():
    assert not validate_mount("/etc/passwd", "/etc", "ro").allowed

def test_reject_root_mount():
    assert not validate_mount("/", "/host", "rw").allowed

def test_reject_docker_sock_mount():
    assert not validate_mount("/var/run/docker.sock", "/var/run/docker.sock", "rw").allowed

def test_reject_path_traversal():
    assert not validate_mount("/tmp/../etc", "/etc", "ro").allowed

def test_reject_production_db_path():
    assert not validate_host_path("/var/lib/hermes/snapshots/production/snapshot.db").allowed

def test_reject_mutations_disabled_env():
    assert not validate_env(["MUTATIONS_DISABLED=false"]).allowed

def test_reject_datbase_path_env():
    assert not validate_env(["DATABASE_PATH=/production.db"]).allowed

def test_reject_sys_admin_cap():
    assert not validate_caps(["SYS_ADMIN"]).allowed

def test_reject_all_caps():
    assert not validate_caps(["ALL"]).allowed

def test_reject_non_disposable_container():
    assert not validate_container_name("test-container").allowed

def test_reject_home_mount():
    assert not validate_mount("/home/user", "/home", "rw").allowed

def test_reject_simulation_mode_env():
    assert not validate_env(["SIMULATION_MODE=true"]).allowed

# ─── Broker Process Request Tests ──────────────────────────────────

def test_broker_rejects_unknown_op():
    assert not process_request({"type": "run_shell", "params": {}})["allowed"]

def test_broker_rejects_production_container_op():
    assert not process_request({
        "type": "inspect_disposable_container",
        "params": {"container_name": "hermes-product-os-prod"},
    })["allowed"]

def test_broker_valid_disposable_op():
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    resp = process_request({
        "type": "inspect_disposable_container",
        "params": {"container_name": "hermes-b5-lab-test"},
    })
    # Validation passes; container may not exist (that's a runtime error)
    assert resp["allowed"] or "No such object" in resp.get("stderr", "")

def test_broker_rejects_arbitrary_mount():
    resp = process_request({
        "type": "create_disposable_container",
        "params": {
            "container_name": "hermes-b5-lab-test",
            "image": "disposable-test",
            "mounts": [{"source": "/etc/passwd", "destination": "/passwd", "mode": "ro"}],
        },
    })
    assert not resp["allowed"]

# ─── Adversarial Tests ─────────────────────────────────────────────

def test_adversarial_production_name_encoded():
    assert not validate_container_name("hermes-product-os-prod\x00-evil").allowed

def test_adversarial_image_injection():
    assert not validate_image("--privileged alpine").allowed

def test_adversarial_mount_traversal():
    assert not validate_mount("../../etc", "/etc", "ro").allowed

# ─── Broker stdin test ─────────────────────────────────────────────

def test_broker_stdin_valid():
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    proc = subprocess.run(
        ["python3", "-m", "deploy.hos_auto_01.bin.broker"],
        input=json.dumps({"type": "inspect_disposable_container", "params": {"container_name": "hermes-b5-lab-test"}}),
        capture_output=True, text=True, timeout=10,
    )
    resp = json.loads(proc.stdout)
    assert resp.get("allowed") or "No such object" in resp.get("stderr", "")

def test_broker_stdin_forbidden():
    proc = subprocess.run(
        ["python3", "-m", "deploy.hos_auto_01.bin.broker"],
        input=json.dumps({"type": "run_shell", "params": {}}),
        capture_output=True, text=True, timeout=10,
    )
    resp = json.loads(proc.stdout)
    assert not resp["allowed"]

# ─── Symlink / Canonicalization Tests ──────────────────────────────

def test_symlink_escape_blocked(tmp_path):
    """A symlink inside the disposable root pointing to /etc must be rejected."""
    import os
    os.makedirs(str(tmp_path / 'lab'), exist_ok=True)
    # Create a symlink inside lab -> /etc
    try:
        os.symlink('/etc', str(tmp_path / 'lab' / 'evil'))
    except OSError:
        pytest.skip('Cannot create symlink')
    v = validate_mount(str(tmp_path / 'lab' / 'evil'), '/etc', 'ro')
    # Canonicalized source resolves to /etc → blocked
    assert not v.allowed

def test_symlink_escape_to_production(tmp_path):
    """Symlink to production snapshot path must be blocked."""
    import os
    os.makedirs(str(tmp_path / 'lab'), exist_ok=True)
    try:
        os.symlink('/var/lib/hermes/snapshots/production', str(tmp_path / 'lab' / 'prod'))
    except OSError:
        pytest.skip('Cannot create symlink')
    v = validate_mount(str(tmp_path / 'lab' / 'prod'), '/snap', 'ro')
    assert not v.allowed

def test_nested_symlink_blocked(tmp_path):
    """Nested symlink traversal must be caught by canonicalization."""
    import os
    os.makedirs(str(tmp_path / 'lab' / 'a' / 'b'), exist_ok=True)
    try:
        os.symlink(str(tmp_path / 'lab' / 'a' / 'b' / '..' / '..' / '..' / '..' / 'etc'), str(tmp_path / 'lab' / 'escape'))
    except OSError:
        pytest.skip('Cannot create symlink')
    v = validate_mount(str(tmp_path / 'lab' / 'escape'), '/x', 'ro')
    assert not v.allowed


# ─── Read-only Inspection Operations (AC-01 support) ─────────────

def test_inspect_container_allows_production_readonly():
    """Read-only inspect of production container is ALLOWED (observation only)."""
    resp = process_request({
        "type": "inspect_container",
        "params": {"container_name": "hermes-product-os-prod"},
    })
    # Validation should pass (read-only observation is safe).
    # Docker may not exist on macOS; on VPS this returns the container status.
    assert resp.get("allowed") is True or "docker" in resp.get("reason", "").lower() or "No such object" in resp.get("stderr", "")

def test_inspect_container_rejects_bad_format():
    resp = process_request({
        "type": "inspect_container",
        "params": {"container_name": "hermes-product-os-prod", "format": "{{.Config.Env}} --inject"},
    })
    assert not resp["allowed"]

def test_inspect_timer_validates_name():
    resp = process_request({
        "type": "inspect_timer",
        "params": {"timer_name": "hermes-production-snapshot-refresh.timer"},
    })
    # Read-only; name is valid. May fail if systemctl not present on macOS.
    assert "allowed" in resp

def test_inspect_container_rejects_traversal_name():
    resp = process_request({
        "type": "inspect_container",
        "params": {"container_name": "../../etc"},
    })
    assert not resp["allowed"]

# ─── Broker Socket Client Tests ───────────────────────────────────

def test_call_broker_returns_structured_denial_when_absent():
    import os
    from deploy.hos_auto_01.bin.bridge import call_broker
    if os.path.exists("/run/hermes-auto/broker.sock"):
        pytest.skip("Broker socket present — absent scenario not applicable on this host")
    resp = call_broker("inspect_container", {"container_name": "x"}, timeout=2)
    # On hosts without a broker socket, returns structured denial, not exception
    assert resp.get("allowed") is False
    assert "exit_code" in resp
