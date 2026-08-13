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
    assert validate_image("hermes-product-os-hpos:prod-p4-release").allowed
    assert validate_image("disposable-test").allowed

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
            "image": "hermes-product-os-hpos:prod-p4-release",
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