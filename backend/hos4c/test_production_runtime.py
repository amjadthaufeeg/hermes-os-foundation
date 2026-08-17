"""Production runtime contract tests — Phase B P4.

Proves production configuration integrity: SIMULATION_MODE=false
prevents simulation data, PRODUCTION environment enforces GAP-001,
health endpoint reports correct state, decisions come from DB not
hardcoded data, and mutation remains blocked.
"""
import os, json, sqlite3, tempfile, yaml, pytest, hashlib
from datetime import datetime, timedelta, timezone
from starlette.testclient import TestClient
from backend.hos4c.environment import POLICY, Environment


# --- Compose validation tests ---

def test_compose_has_no_public_ports():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    svc = compose["services"]["hpos"]
    assert "ports" not in svc, "Production compose must not expose ports"
    assert "expose" not in svc, "Production compose must not expose"

def test_compose_uses_internal_network():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    net = compose["networks"]["prod-net"]
    assert net.get("internal") == True

def test_compose_read_only_rootfs():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    svc = compose["services"]["hpos"]
    assert svc.get("read_only") == True

def test_compose_cap_drop_all():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    svc = compose["services"]["hpos"]
    assert "ALL" in svc.get("cap_drop", [])

def test_compose_no_new_privileges():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    svc = compose["services"]["hpos"]
    opts = svc.get("security_opt", [])
    assert "no-new-privileges:true" in opts

def test_compose_user_is_10010():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    svc = compose["services"]["hpos"]
    assert svc.get("user") == "10010:10010"

def test_compose_environment_production():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    env = compose["services"]["hpos"]["environment"]
    assert "HERMES_ENVIRONMENT=PRODUCTION" in env
    assert "MUTATIONS_DISABLED=true" in env
    assert "SIMULATION_MODE=false" in env

def test_compose_no_staging_volumes():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    vols = [v for mount in compose["services"]["hpos"]["volumes"] for v in mount.split(":")]
    assert "hpos-data" not in vols, "No staging hpos-data volume"
    assert "hpos-backup" not in vols, "No staging hpos-backup volume"

def test_compose_snapshot_mount_is_read_only():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    mounts = compose["services"]["hpos"]["volumes"]
    assert "/var/lib/hermes/snapshots/snapshot.db:/opt/hermes/data/production.db:ro" in mounts
    assert "/var/lib/hermes/snapshots/snapshot.meta.json:/opt/hermes/data/snapshot.meta.json:ro" in mounts

def test_compose_no_b2_secrets():
    compose_text = open("deploy/docker-compose.prod.yml").read()
    assert "B2_" not in compose_text, "No B2 credentials in production compose"

def test_compose_datbase_path_correct():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    env = compose["services"]["hpos"]["environment"]
    assert "DATABASE_PATH=/opt/hermes/data/production.db" in env


# --- Runtime behavior tests ---

def _write_snapshot_metadata(db_path, created_at=None, sha=None):
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    if sha is None:
        h = hashlib.sha256()
        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        sha = h.hexdigest()
    meta = {
        "result": "published",
        "created_at_utc": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_id": "test-source",
        "sha256": sha,
        "duration_s": 0,
        "validation": {"integrity_check": "ok", "decisions_count": 0},
    }
    with open(os.path.join(os.path.dirname(db_path), "snapshot.meta.json"), "w") as f:
        json.dump(meta, f)

@pytest.fixture
def production_app(monkeypatch, tmp_path):
    """FastAPI app configured for production. Uses is_simulation_mode()
    which reads from os.environ at call time — no module reload needed."""
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)

    from backend.hos4c.main import app
    yield app, db_path
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix
    monkeypatch.delenv("SIMULATION_MODE", raising=False)

def test_production_starts_successfully(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["environment"] == "PRODUCTION"
        assert data["mutations"] == "DISABLED"

def test_production_health_has_no_simulation_data(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/health")
        assert "SIMULATION" not in r.text

def test_production_decisions_empty_db(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/decisions")
        data = r.json()
        assert data["count"] == 0
        assert data["mode"] == "PRODUCTION"
        assert data["decisions"] == []

def test_production_decisions_not_simulation(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/decisions")
        data = r.json()
        # Must NOT contain SIM_DECISIONS
        ids = [d["id"] for d in data["decisions"]]
        assert "DEC-HOS-001" not in ids
        assert "DEC-HOS-002" not in ids
        assert "DEC-HOS-019" not in ids

def test_production_nonexistent_decision_404(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/decisions/DEC-NONEXISTENT")
        assert r.status_code == 404

def test_production_mutation_blocked(production_app):
    app, _ = production_app
    with TestClient(app, raise_server_exceptions=False) as c:
        # Mutation gate runs before auth — no login needed for denial
        r = c.post(
            "/api/decisions/DEC-HOS-001/actions",
            json={"action": "approve", "rationale": "test"},
        )
        assert r.status_code == 503
        assert "Mutations disabled" in r.text

def test_production_mutation_does_not_create_rows(production_app):
    app, db_path = production_app
    conn_before = sqlite3.connect(db_path)
    before = conn_before.execute(
        "SELECT COUNT(*) FROM decisions").fetchone()[0]
    conn_before.close()

    with TestClient(app, raise_server_exceptions=False) as c:
        c.post("/api/decisions/DEC-HOS-001/actions",
               json={"action": "approve", "rationale": "test"})

    conn_after = sqlite3.connect(db_path)
    after = conn_after.execute(
        "SELECT COUNT(*) FROM decisions").fetchone()[0]
    conn_after.close()
    assert before == after

def test_production_read_works(production_app):
    app, db_path = production_app
    # Insert test data directly for read test
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO decisions (id, title, state, version, owner, project, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                 ("DEC-TEST-001", "Test Decision", "AWAITING_AMJAD", 1, "amjad", "hermes-os"))
    conn.commit()
    conn.close()
    _write_snapshot_metadata(db_path)

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/decisions")
        data = r.json()
        assert data["count"] == 1
        assert data["decisions"][0]["id"] == "DEC-TEST-001"

    # Cleanup
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM decisions")
    conn.commit()
    conn.close()

def test_production_gap001_fails_closed(monkeypatch, tmp_path):
    """MUTATIONS_DISABLED=false must fail startup in PRODUCTION."""
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "false")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)

    # Lifespan must raise RuntimeError
    from backend.hos4c.environment import startup_policy_check
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

# --- PRODUCTION SIMULATION_MODE startup enforcement ---

def test_production_simulation_mode_false_starts(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.environment import startup_policy_check
    startup_policy_check()  # must not raise
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_simulation_mode_true_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "true")
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_simulation_mode_missing_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.delenv("SIMULATION_MODE", raising=False)
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_simulation_mode_malformed_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "yes")
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_database_path_outside_snapshot_prefix_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.environment import startup_policy_check
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()

def test_production_missing_snapshot_metadata_fails_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "production.db"))
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db()
    from backend.hos4c.environment import startup_policy_check
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_stale_snapshot_fails_both_decision_reads(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path)
    from backend.hos4c.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        _write_snapshot_metadata(db_path, created_at=datetime.now(timezone.utc) - timedelta(seconds=1200))
        list_resp = c.get("/api/decisions")
        detail_resp = c.get("/api/decisions/DEC-TEST-001")
        assert list_resp.status_code == 503
        assert detail_resp.status_code == 503
        assert list_resp.json()["detail"]["reason"] == "stale"
        assert detail_resp.json()["detail"]["reason"] == "stale"
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix

def test_production_snapshot_sha_mismatch_fails_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    original_prefix = POLICY[Environment.PRODUCTION]["snapshot_path_prefix"]
    monkeypatch.setitem(POLICY[Environment.PRODUCTION], "snapshot_path_prefix", str(tmp_path))
    from backend.hos4c.database import init_db
    init_db(db_path)
    _write_snapshot_metadata(db_path, sha="0" * 64)
    from backend.hos4c.environment import startup_policy_check
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
    POLICY[Environment.PRODUCTION]["snapshot_path_prefix"] = original_prefix
