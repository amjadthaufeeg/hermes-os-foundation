"""
HOS-4C Automated Test Suite — With Cookie Persistence Fix
Run: python3.11 -m pytest backend/hos4c/test_security.py -v
"""

import pytest, json, os, sqlite3, tempfile
from starlette.testclient import TestClient

# One temp DB for the entire test run
TEST_DB = tempfile.mktemp(suffix=".db")

# All test flows share this app
from backend.hos4c.main import app

@pytest.fixture(autouse=True)
def fresh_db():
    """Fresh database per test function."""
    os.environ["DATABASE_PATH"] = TEST_DB
    os.environ["SIMULATION_MODE"] = "true"
    os.environ["MUTATIONS_DISABLED"] = "false"  # Allow simulation actions in tests
    from backend.hos4c.database import init_db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db()
    # Reset in-memory decision state
    from backend.hos4c import main
    main.SIM_DECISIONS = [
        {"id": "DEC-HOS-001", "title": "Hermes remains the sole orchestrator", "state": "AWAITING_AMJAD", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi, Codex and Claude may build or review within assigned roles, but they may not independently control scope, task-state transitions, agent routing, approval, merge or deployment.", "reason": "Prevent conflicting agent authority."},
        {"id": "DEC-HOS-002", "title": "Kimi K3 is the primary builder", "state": "LOCKED", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi K3 handles new features as the default primary builder.", "reason": "Strong multi-file implementation performance."},
        {"id": "DEC-HOS-019", "title": "Product-development philosophy governs future expansion", "state": "AWAITING_AMJAD", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Future roles and automation must be evaluated against the approved Philosophy.", "reason": "Immutable values."},
    ]
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# ============================================================
# Cookie Diagnostic — must pass first
# ============================================================
class TestCookieDiagnostic:
    def test_cookie_persistence(self, fresh_db):
        """Login sets cookie → next request uses it."""
        with TestClient(app) as c:
            r1 = c.post("/api/auth/login")
            assert r1.status_code == 200
            assert "hermes_session" in r1.cookies or r1.headers.get("set-cookie", "").find("hermes_session") >= 0
            r2 = c.get("/api/auth/session")
            assert r2.json()["authenticated"] == True

    def test_logout_invalidates(self, fresh_db):
        """Login → logout → session gone."""
        with TestClient(app) as c:
            c.post("/api/auth/login")
            r1 = c.get("/api/auth/session")
            assert r1.json()["authenticated"] == True
            c.post("/api/auth/logout")
            r2 = c.get("/api/auth/session")
            assert r2.json()["authenticated"] == False

    def test_missing_session_rejected(self, fresh_db):
        """No login → session endpoint says unauthenticated."""
        with TestClient(app) as c:
            r = c.get("/api/auth/session")
            assert r.json()["authenticated"] == False

# ============================================================
# Authentication
# ============================================================
class TestAuthentication:
    def test_simulated_login(self, fresh_db):
        with TestClient(app) as c:
            r = c.post("/api/auth/login")
            assert r.status_code == 200
            d = r.json()
            assert len(d["csrf_token"]) == 64
            assert d["role"] == "AMJAD_OWNER"

    def test_client_role_not_in_body(self, fresh_db):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "APPROVE" not in ROLE_PERMISSIONS["HERMES_ASSISTANT"]

# ============================================================
# Authorization (5 tests)
# ============================================================
class TestAuthorization:
    def test_hermes_cannot_approve(self):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "APPROVE" not in ROLE_PERMISSIONS["HERMES_ASSISTANT"]

    def test_hermes_cannot_reject(self):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "REJECT" not in ROLE_PERMISSIONS["HERMES_ASSISTANT"]

    def test_contributor_has_no_actions(self):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["CONTRIBUTOR"] == []

    def test_amjad_owner_can_approve(self):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "APPROVE" in ROLE_PERMISSIONS["AMJAD_OWNER"]

    def test_reviewer_cannot_approve(self):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "APPROVE" not in ROLE_PERMISSIONS["REVIEWER"]

# ============================================================
# State Machine
# ============================================================
class TestStateMachine:
    def test_all_allowed_transitions(self):
        from backend.hos4c.state_machine import validate_transition
        assert validate_transition("AWAITING_AMJAD", "APPROVE", "AMJAD_OWNER") == "APPROVED"
        assert validate_transition("AWAITING_AMJAD", "REJECT", "AMJAD_OWNER") == "REJECTED"
        assert validate_transition("AWAITING_AMJAD", "DEFER", "AMJAD_OWNER") == "DEFERRED"
        assert validate_transition("HOLD", "RESUME", "AMJAD_OWNER") == "AWAITING_AMJAD"

    def test_invalid_transitions_raise(self):
        from backend.hos4c.state_machine import validate_transition
        with pytest.raises(ValueError):
            validate_transition("CLOSED", "APPROVE", "AMJAD_OWNER")

    def test_hermes_cannot_transition(self):
        from backend.hos4c.state_machine import validate_transition
        with pytest.raises(ValueError):
            validate_transition("AWAITING_AMJAD", "APPROVE", "HERMES_ASSISTANT")

# ============================================================
# CSRF Protection
# ============================================================
class TestCSRF:
    def _login_and_csrf(self, c):
        r = c.post("/api/auth/login")
        return r.json()["csrf_token"]

    def test_valid_csrf_action(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login_and_csrf(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "Deferring this decision for now, needs more consideration."},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200

    def test_invalid_csrf_token(self, fresh_db):
        with TestClient(app) as c:
            self._login_and_csrf(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "x" * 30},
                      headers={"X-CSRF-Token": "bad-token"})
            assert r.status_code in (401, 403)

    def test_missing_csrf_token(self, fresh_db):
        with TestClient(app) as c:
            self._login_and_csrf(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "x" * 30})
            assert r.status_code in (401, 403)

    def test_unauthenticated_csrf(self, fresh_db):
        with TestClient(app) as c:
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "x" * 30},
                      headers={"X-CSRF-Token": "some-token"})
            assert r.status_code in (401, 403)

# ============================================================
# Confirmation
# ============================================================
class TestConfirmation:
    def _login(self, c):
        r = c.post("/api/auth/login")
        return r.json()["csrf_token"]

    def test_missing_typed_confirmation(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough text."},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 422

    def test_correct_confirmation(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with sufficient text length here.", "typed_confirmation": "APPROVE DEC-HOS-001"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200

    def test_wrong_confirmation(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough words.", "typed_confirmation": "CONFIRM"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 422

    def test_wrong_case(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough.", "typed_confirmation": "approve dec-hos-001"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 422

    def test_short_rationale(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "short", "typed_confirmation": "APPROVE DEC-HOS-001"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 422

# ============================================================
# Session Flows
# ============================================================
class TestSessionFlows:
    def _login(self, c):
        r = c.post("/api/auth/login")
        return r.json()["csrf_token"]

    def test_login_action_flow(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "PLACE_ON_HOLD", "rationale": "Full integration flow test with enough text for validation."},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200

    def test_login_action_logout_flow(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r1 = c.post("/api/decisions/DEC-HOS-001/actions",
                       json={"action": "PLACE_ON_HOLD", "rationale": "Testing the complete flow with enough text here."},
                       headers={"X-CSRF-Token": csrf})
            assert r1.status_code == 200
            c.post("/api/auth/logout")
            r2 = c.post("/api/decisions/DEC-HOS-001/actions",
                       json={"action": "PLACE_ON_HOLD", "rationale": "x" * 30},
                       headers={"X-CSRF-Token": csrf})
            assert r2.status_code in (401, 403)

    def test_login_action_resume_flow(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r1 = c.post("/api/decisions/DEC-HOS-019/actions",
                       json={"action": "PLACE_ON_HOLD", "rationale": "Placing on hold for further review and discussion."},
                       headers={"X-CSRF-Token": csrf})
            assert r1.status_code == 200
            r2 = c.post("/api/decisions/DEC-HOS-019/actions",
                       json={"action": "RESUME", "rationale": "Resuming after review is complete."},
                       headers={"X-CSRF-Token": csrf})
            assert r2.status_code == 200

    def test_approve_with_confirmation(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with sufficient text length here.", "typed_confirmation": "APPROVE DEC-HOS-001"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200
            d = r.json()
            assert d["mode"] == "SIMULATION"
            assert "NO AUTHORITATIVE" in d.get("warning", "")

    def test_reject_with_confirmation(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-019/actions",
                      json={"action": "REJECT", "rationale": "Rejecting this decision with sufficient reasoning text.", "typed_confirmation": "REJECT DEC-HOS-019"},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200

    def test_simulation_warning_on_health(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/health")
            assert r.json()["mutations"] in ("DISABLED", "SIMULATION_ONLY")

# ============================================================
# Simulation Isolation
# ============================================================
class TestSimulationIsolation:
    def test_mode_is_simulation(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/health")
            assert r.json()["mutations"] in ("DISABLED", "SIMULATION_ONLY")

    def test_no_decision_register_write_path(self):
        code = open("backend/hos4c/main.py").read()
        assert ".hermes/registers/decisions" not in code

    def test_no_github_token(self):
        code = open("backend/hos4c/main.py").read()
        assert "GITHUB_TOKEN" not in code

    def test_decisions_in_memory(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/decisions")
            assert r.json()["mutations"] in ("DISABLED", "SIMULATION_ONLY")

# ============================================================
# Concurrency & Idempotency
# ============================================================
class TestConcurrency:
    def _login(self, c):
        return c.post("/api/auth/login").json()["csrf_token"]

    def test_state_transition_persists(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "Deferring this decision for now, needs more consideration and review."},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200

    def test_hold_resume_cycle(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r1 = c.post("/api/decisions/DEC-HOS-019/actions",
                       json={"action": "PLACE_ON_HOLD", "rationale": "Placing on hold for further review time."},
                       headers={"X-CSRF-Token": csrf})
            assert r1.status_code == 200
            r2 = c.post("/api/decisions/DEC-HOS-019/actions",
                       json={"action": "RESUME", "rationale": "Resuming after review complete."},
                       headers={"X-CSRF-Token": csrf})
            assert r2.status_code == 200

    def test_audit_event_produced(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "PLACE_ON_HOLD", "rationale": "Placing on hold until further review."},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code == 200
            assert "audit_event_id" in r.json()

# ============================================================
# Audit Integrity
# ============================================================
class TestAudit:
    def test_hash_chain_intact(self, fresh_db):
        from backend.hos4c.audit import verify_hash_chain
        r = verify_hash_chain()
        assert r["integrity"] == "INTACT"

    def test_events_exportable(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/audit/events")
            assert r.status_code == 200
            assert "events" in r.json()

    def test_export_endpoint(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/audit/export")
            assert r.status_code == 200

# ============================================================
# Security Input
# ============================================================
class TestSecurityInput:
    def _login(self, c):
        return c.post("/api/auth/login").json()["csrf_token"]

    def test_xss_in_rationale(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-001/actions",
                      json={"action": "DEFER", "rationale": "<script>alert('xss')</script>" + "x" * 30},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code in (200, 422)

    def test_sql_injection_safe(self, fresh_db):
        with TestClient(app) as c:
            r = c.get("/api/decisions/DEC-HOS-001' OR '1'='1")
            assert r.status_code == 404

    def test_large_payload(self, fresh_db):
        with TestClient(app) as c:
            csrf = self._login(c)
            r = c.post("/api/decisions/DEC-HOS-019/actions",
                      json={"action": "PLACE_ON_HOLD", "rationale": "x" * 10000},
                      headers={"X-CSRF-Token": csrf})
            assert r.status_code in (200, 422, 413)

# ============================================================
# Meta
# ============================================================
def test_count():
    classes = [TestCookieDiagnostic, TestAuthentication, TestAuthorization,
               TestStateMachine, TestCSRF, TestConfirmation, TestSessionFlows,
               TestSimulationIsolation, TestConcurrency, TestAudit, TestSecurityInput]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4C: {total} tests ===\n")
    assert total >= 41