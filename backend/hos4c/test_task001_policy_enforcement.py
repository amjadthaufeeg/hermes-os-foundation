"""
TASK-001: Policy Cross-Validation Security Tests

Verifies that environment policy is authoritative:
MUTATIONS_DISABLED=false can NEVER enable mutations in environments
whose policy prohibits them.

Tests the real implementation — no mocks on mutations_disabled().
"""
import os
import pytest

from backend.hos4c.environment import (
    Environment, POLICY, mutations_disabled, get_env,
    validate_startup, has_fatal_errors, startup_policy_check
)


# ---------------------------------------------------------------------------
# T1-T9: MUTATIONS_DISABLED value matrix under LOCAL_TEST
# ---------------------------------------------------------------------------

class TestPolicyEnforcement:

    def _setup(self, monkeypatch, flag=None):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        if flag is None:
            monkeypatch.delenv("MUTATIONS_DISABLED", raising=False)
        else:
            monkeypatch.setenv("MUTATIONS_DISABLED", flag)

    def test_t1_true_is_valid_and_disabled(self, monkeypatch):
        self._setup(monkeypatch, "true")
        errors = validate_startup()
        assert not has_fatal_errors(errors), f"Unexpected FATAL: {errors}"
        assert mutations_disabled() is True

    def test_t2_absent_is_valid_and_disabled(self, monkeypatch):
        self._setup(monkeypatch)  # no flag → absent
        errors = validate_startup()
        assert not has_fatal_errors(errors), f"Unexpected FATAL: {errors}"
        assert mutations_disabled() is True

    def test_t3_false_is_fatal_policy_conflict(self, monkeypatch):
        self._setup(monkeypatch, "false")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True

    def test_t4_empty_string_is_fatal(self, monkeypatch):
        self._setup(monkeypatch, "")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True

    def test_t5_whitespace_only_is_fatal(self, monkeypatch):
        self._setup(monkeypatch, "   ")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True

    def test_t6_maybe_is_fatal(self, monkeypatch):
        self._setup(monkeypatch, "maybe")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True

    def test_t7_zero_is_fatal(self, monkeypatch):
        self._setup(monkeypatch, "0")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True

    def test_t8_mixed_case_true_is_valid(self, monkeypatch):
        self._setup(monkeypatch, "TRUE")
        errors = validate_startup()
        assert not has_fatal_errors(errors), f"Unexpected FATAL: {errors}"
        assert mutations_disabled() is True

    def test_t9_mixed_case_false_is_fatal(self, monkeypatch):
        self._setup(monkeypatch, "FALSE")
        errors = validate_startup()
        assert has_fatal_errors(errors), f"No FATAL error in: {errors}"
        assert mutations_disabled() is True


# ---------------------------------------------------------------------------
# T10: Invalid HERMES_ENVIRONMENT
# ---------------------------------------------------------------------------

class TestInvalidEnvironment:
    def test_t10_invalid_env_raises(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "INVALID_ENV")
        with pytest.raises(ValueError):
            get_env()


# ---------------------------------------------------------------------------
# T11: Missing POLICY entry
# ---------------------------------------------------------------------------

class TestMissingPolicy:
    def test_t11_missing_policy_rejected(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        original = POLICY.pop(Environment.LOCAL_TEST, None)
        try:
            with pytest.raises(ValueError, match="has no policy entry"):
                get_env()
        finally:
            if original is not None:
                POLICY[Environment.LOCAL_TEST] = original
            monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_SIMULATION")


# ---------------------------------------------------------------------------
# T12: Startup policy check (lifespan-level)
# ---------------------------------------------------------------------------

class TestLifespanRejectsFatalConfig:
    def test_t12_lifespan_with_false_rejects(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "false")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("SIMULATION_MODE", "true")
        with pytest.raises(RuntimeError, match="fatal configuration"):
            startup_policy_check()

    def test_t12_lifespan_with_true_starts_ok(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "true")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("SIMULATION_MODE", "true")
        # Should not raise
        startup_policy_check()


# ---------------------------------------------------------------------------
# T13: Runtime gate still disabled even if startup bypassed
# ---------------------------------------------------------------------------

class TestRuntimeGateStillDisabled:
    def test_t13_bypassed_startup_still_disabled(self, monkeypatch):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "false")
        assert mutations_disabled() is True


# ---------------------------------------------------------------------------
# T14-T16: Real mutation endpoint (HTTP 503)
# ---------------------------------------------------------------------------

class TestMutationEndpointDenied:

    @staticmethod
    def _make_client():
        """Create a fresh TestClient with clean environment."""
        from starlette.testclient import TestClient
        from backend.hos4c.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_t14_returns_503(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "true")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("SIMULATION_MODE", "true")
        from backend.hos4c.database import init_db
        init_db()

        with self._make_client() as c:
            login = c.post("/api/auth/login")
            csrf = login.json()["csrf_token"]
            cookie = login.cookies.get("hermes_session")
            resp = c.post(
                "/api/decisions/DEC-HOS-001/actions",
                json={"action": "approve", "rationale": "T14 test"},
                headers={"X-CSRF-Token": csrf},
                cookies={"hermes_session": cookie},
            )
            assert resp.status_code == 503
            assert "Mutations disabled" in resp.text

    def test_t15_decision_unchanged(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "true")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("SIMULATION_MODE", "true")
        from backend.hos4c.database import init_db
        init_db()

        with self._make_client() as c:
            login = c.post("/api/auth/login")
            csrf = login.json()["csrf_token"]
            cookie = login.cookies.get("hermes_session")
            before = c.get("/api/decisions/DEC-HOS-001",
                          cookies={"hermes_session": cookie})
            before_state = before.json()["state"]

            c.post("/api/decisions/DEC-HOS-001/actions",
                   json={"action": "approve", "rationale": "T15 test"},
                   headers={"X-CSRF-Token": csrf},
                   cookies={"hermes_session": cookie})

            after = c.get("/api/decisions/DEC-HOS-001",
                         cookies={"hermes_session": cookie})
            assert after.json()["state"] == before_state

    def test_t16_no_audit_created(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENVIRONMENT", "LOCAL_TEST")
        monkeypatch.setenv("MUTATIONS_DISABLED", "true")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("SIMULATION_MODE", "true")
        from backend.hos4c.database import init_db
        init_db()

        with self._make_client() as c:
            login = c.post("/api/auth/login")
            csrf = login.json()["csrf_token"]
            cookie = login.cookies.get("hermes_session")
            before = c.get("/api/audit/events",
                          cookies={"hermes_session": cookie})
            before_count = before.json()["count"]

            c.post("/api/decisions/DEC-HOS-001/actions",
                   json={"action": "approve", "rationale": "T16 test"},
                   headers={"X-CSRF-Token": csrf},
                   cookies={"hermes_session": cookie})

            after = c.get("/api/audit/events",
                         cookies={"hermes_session": cookie})
            assert after.json()["count"] == before_count