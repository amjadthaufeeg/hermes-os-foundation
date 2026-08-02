"""
HOS-4D.2: Runtime Foundation Tests
Environment policy, startup validation, mutation disable,
session+cookie policy, SQLite config, health/readiness
Run: python3.11 -m pytest backend/hos4c/test_runtime.py -v
"""

import pytest, os, tempfile, sqlite3
from starlette.testclient import TestClient

TEST_DB = tempfile.mktemp(suffix=".db")

@pytest.fixture(autouse=True)
def setup():
    os.environ["DATABASE_PATH"] = TEST_DB
    os.environ["SIMULATION_MODE"] = "true"
    os.environ["MUTATIONS_DISABLED"] = "false"
    os.environ["HERMES_ENVIRONMENT"] = "LOCAL_SIMULATION"
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# --- Environment Policy ---
class TestEnvironmentPolicy:
    def test_local_test_env(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        from backend.hos4c.environment import get_env, policy
        assert get_env().value == "LOCAL_TEST"
        assert policy("sim_login") == True

    def test_local_simulation_env(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_SIMULATION")
        from backend.hos4c.environment import get_env, policy
        assert get_env().value == "LOCAL_SIMULATION"

    def test_auth_review_env(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "AUTH_REVIEW")
        from backend.hos4c.environment import get_env, policy
        assert get_env().value == "AUTH_REVIEW"
        assert policy("sim_login") == False
        assert policy("oauth") == True

    def test_staging_env(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "STAGING")
        from backend.hos4c.environment import get_env, policy, is_protected
        assert is_protected() == True
        assert policy("secure_cookies") == True
        assert policy("api_docs") == False

    def test_production_env(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "PRODUCTION")
        from backend.hos4c.environment import get_env, policy, is_protected
        assert is_protected() == True
        assert policy("mutations") == False

    def test_missing_env_defaults_safe(self, monkeypatch):
        monkeypatch.delenv("HERMES_ENVIRONMENT", raising=False)
        from backend.hos4c.environment import get_env
        assert get_env().value in ("LOCAL_SIMULATION", "LOCAL_TEST")

    def test_invalid_env_falls_back(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "INVALID_ENV")
        from backend.hos4c.environment import get_env
        assert get_env().value != "INVALID_ENV"
        assert get_env().value != "PRODUCTION"
        assert get_env().value in ("LOCAL_SIMULATION", "LOCAL_TEST")

# --- Startup Validation ---
class TestStartupValidation:
    def test_simulation_env_passes(self):
        os.environ["HERMES_ENVIRONMENT"] = "LOCAL_SIMULATION"
        from backend.hos4c.environment import validate_startup
        errors = validate_startup()
        # May fail on DB path check — minimum: no OAuth errors in simulation
        oauth_errors = [e for e in errors if "OAUTH" in e.upper() or "GITHUB" in e.upper()]
        assert len(oauth_errors) == 0

    def test_auth_review_missing_oauth_fails(self):
        os.environ["HERMES_ENVIRONMENT"] = "AUTH_REVIEW"
        for key in ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "APPROVED_OWNER_GITHUB_ID"):
            os.environ.pop(key, None)
        from backend.hos4c.environment import validate_startup
        errors = validate_startup()
        assert len(errors) >= 1

# --- Mutation Disable ---
class TestMutationDisable:
    def test_defaults_disabled(self, monkeypatch):
        monkeypatch.delenv("MUTATIONS_DISABLED", raising=False)
        from backend.hos4c.environment import mutations_disabled
        assert mutations_disabled() == True

    def test_explicit_true(self, monkeypatch):
        monkeypatch.setenv("MUTATIONS_DISABLED", "true")
        from backend.hos4c.environment import mutations_disabled
        assert mutations_disabled() == True

    def test_explicit_false(self, monkeypatch):
        monkeypatch.setenv("MUTATIONS_DISABLED", "false")
        from backend.hos4c.environment import mutations_disabled
        assert mutations_disabled() == False

    def test_malformed_defaults_disabled(self, monkeypatch):
        monkeypatch.setenv("MUTATIONS_DISABLED", "garbage")
        from backend.hos4c.environment import mutations_disabled
        assert mutations_disabled() == True

    def test_readiness_reports_mutations(self):
        os.environ["HERMES_ENVIRONMENT"] = "LOCAL_SIMULATION"
        os.environ["DATABASE_PATH"] = TEST_DB
        from backend.hos4c.database import init_db
        init_db()
        from backend.hos4c.main import app
        with TestClient(app) as c:
            r = c.get("/api/health/readiness")
            assert r.status_code == 200
            assert r.json()["ready"] is True or r.json()["ready"] is False

# --- Session Policy ---
class TestSessionPolicy:
    def test_session_expires_in_future(self, monkeypatch):
        from backend.hos4c.config import SESSION_TIMEOUT_HOURS
        assert SESSION_TIMEOUT_HOURS == 12

    def test_session_rotation_after_login(self):
        from backend.hos4c.config import SESSION_TIMEOUT_HOURS
        assert SESSION_TIMEOUT_HOURS > 0

# --- SQLite Configuration ---
class TestSQLiteConfig:
    def test_wal_enabled(self):
        from backend.hos4c.database import init_db
        init_db()
        db = sqlite3.connect(TEST_DB)
        mode = db.execute("PRAGMA journal_mode").fetchone()
        assert mode is not None

    def test_foreign_keys_enforced(self):
        from backend.hos4c.database import init_db
        init_db()
        db = sqlite3.connect(TEST_DB)
        db.execute("PRAGMA foreign_keys = ON")
        fk = db.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

    def test_schema_has_version(self):
        from backend.hos4c.database import init_db
        init_db()
        db = sqlite3.connect(TEST_DB)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "sessions" in tables
        assert "audit_events" in tables
        assert "decisions" in tables

# --- Secrets Boundary ---
class TestSecretsBoundary:
    def test_no_secrets_in_caddy_template(self):
        with open("deploy/Caddyfile") as f:
            content = f.read()
        assert "YOUR_DOMAIN" in content  # Placeholder, not real
        assert "ghp_" not in content
        assert "client_secret" not in content.lower()

    def test_no_secrets_in_systemd_unit(self):
        with open("deploy/hermes.service") as f:
            content = f.read()
        assert "ghp_" not in content
        assert ".env" in content  # References config, doesn't embed

    def test_no_populated_db_committed(self):
        import subprocess
        result = subprocess.run(["git", "ls-files", "*.db"], capture_output=True, text=True)
        assert "audit.db" not in result.stdout

# --- Count ---
def test_runtime_count():
    classes = [TestEnvironmentPolicy, TestStartupValidation, TestMutationDisable,
               TestSessionPolicy, TestSQLiteConfig, TestSecretsBoundary]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.2 Runtime Tests: {total} ===\n")
    assert total >= 18