"""Production runtime contract tests — Phase B P4.

Proves production configuration integrity: SIMULATION_MODE=false
prevents simulation data, PRODUCTION environment enforces GAP-001,
health endpoint reports correct state, decisions come from DB not
hardcoded data, and mutation remains blocked.
"""
import os, json, sqlite3, tempfile, yaml, pytest
from starlette.testclient import TestClient


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

def test_compose_no_b2_secrets():
    compose_text = open("deploy/docker-compose.prod.yml").read()
    assert "B2_" not in compose_text, "No B2 credentials in production compose"

def test_compose_datbase_path_correct():
    compose = yaml.safe_load(open("deploy/docker-compose.prod.yml"))
    env = compose["services"]["hpos"]["environment"]
    assert "DATABASE_PATH=/opt/hermes/data/production.db" in env


# --- Runtime behavior tests ---

@pytest.fixture
def production_app(monkeypatch, tmp_path):
    """FastAPI app configured for production. Uses is_simulation_mode()
    which reads from os.environ at call time — no module reload needed."""
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    db_path = str(tmp_path / "production.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    from backend.hos4c.database import init_db
    init_db(db_path)

    from backend.hos4c.main import app
    yield app, db_path
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
    from backend.hos4c.database import init_db
    init_db(db_path)

    # Lifespan must raise RuntimeError
    from backend.hos4c.environment import startup_policy_check
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()

# --- PRODUCTION SIMULATION_MODE startup enforcement ---

def test_production_simulation_mode_false_starts(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "false")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from backend.hos4c.database import init_db
    init_db()
    from backend.hos4c.environment import startup_policy_check
    startup_policy_check()  # must not raise

def test_production_simulation_mode_true_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "true")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from backend.hos4c.database import init_db
    init_db()
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()

def test_production_simulation_mode_missing_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.delenv("SIMULATION_MODE", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from backend.hos4c.database import init_db
    init_db()
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()

def test_production_simulation_mode_malformed_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
    monkeypatch.setenv("MUTATIONS_DISABLED", "true")
    monkeypatch.setenv("SIMULATION_MODE", "yes")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from backend.hos4c.database import init_db
    init_db()
    from backend.hos4c.environment import startup_policy_check
    import pytest
    with pytest.raises(RuntimeError, match="fatal configuration"):
        startup_policy_check()
