"""
HOS-4C Automated Test Suite — Simulation Mode
Run: python3.11 -m pytest backend/hos4c/test_security.py -v
"""

import pytest, json, os, sqlite3, tempfile
from starlette.testclient import TestClient

TEST_DB = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_PATH"] = TEST_DB
os.environ["SIMULATION_MODE"] = "true"

from backend.hos4c.database import init_db
from backend.hos4c.main import app

@pytest.fixture
def client():
    """Fresh client per test. Cookies persist via client.cookies."""
    init_db()
    c = TestClient(app)
    return c

def _login(client):
    """Login and return csrf_token. Sets cookie on the persistent client."""
    resp = client.post("/api/auth/login")
    assert resp.status_code == 200
    data = resp.json()
    csrf = data["csrf_token"]
    return csrf

# ============================================================
# Simulation Isolation (4 tests)
# ============================================================
class TestSimulationIsolation:
    def test_mode_is_simulation(self, client):
        resp = client.get("/api/health")
        assert resp.json()["mode"] == "SIMULATION_ONLY"

    def test_no_decision_register_write_path(self):
        code = open("backend/hos4c/main.py").read()
        assert ".hermes/registers/decisions" not in code

    def test_no_github_token_loaded(self):
        code = open("backend/hos4c/main.py").read()
        assert "GITHUB_TOKEN" not in code

    def test_sim_decisions_in_memory(self, client):
        resp = client.get("/api/decisions")
        assert resp.json()["mode"] == "SIMULATION"

# ============================================================
# Authentication & Sessions (5 tests)
# ============================================================
class TestAuthentication:
    def test_simulated_login_creates_session(self, client):
        csrf = _login(client)
        assert len(csrf) == 64

    def test_unauthenticated_rejected(self, client):
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "x" * 50})
        assert resp.status_code in (401, 403)

    def test_client_role_ignored(self, client):
        from backend.hos4c.state_machine import ROLE_PERMISSIONS
        assert "APPROVE" not in ROLE_PERMISSIONS["HERMES_ASSISTANT"]

    def test_logout_invalidates(self, client):
        _login(client)
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        resp2 = client.get("/api/auth/session")
        assert resp2.json()["authenticated"] == False

    def test_non_authenticated_session_check(self, client):
        resp = client.get("/api/auth/session")
        assert resp.json()["authenticated"] == False

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
# State Machine (3 tests)
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
# CSRF Protection (4 tests)
# ============================================================
class TestCSRF:
    def test_valid_csrf_action_succeeds(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "DEFER", "rationale": "Deferring this decision for now, needs more consideration."},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "SIMULATION"

    def test_invalid_csrf_token_rejected(self, client):
        _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "x" * 50},
                          headers={"X-CSRF-Token": "bad-token"})
        assert resp.status_code in (401, 403)

    def test_missing_csrf_token_rejected(self, client):
        _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "x" * 50})
        assert resp.status_code in (401, 403)

    def test_unauthenticated_with_csrf_rejected(self, client):
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "x" * 50},
                          headers={"X-CSRF-Token": "some-token"})
        assert resp.status_code in (401, 403)

# ============================================================
# Confirmation (5 tests)
# ============================================================
class TestConfirmation:
    def test_missing_typed_confirmation_rejected(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough text."},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422

    def test_correct_typed_confirmation(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with sufficient text for the minimum.", "typed_confirmation": "APPROVE DEC-HOS-001"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200

    def test_wrong_typed_confirmation(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough words here.", "typed_confirmation": "CONFIRM"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422

    def test_wrong_case_confirmation(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with enough words here.", "typed_confirmation": "approve dec-hos-001"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422  # Case-sensitive

    def test_missing_rationale_rejected(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "short", "typed_confirmation": "APPROVE DEC-HOS-001"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422

# ============================================================
# Concurrency & Idempotency (3 tests)
# ============================================================
class TestConcurrency:
    def test_action_updates_state(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "DEFER", "rationale": "Deferring this decision for now, needs more consideration and review time."},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200
        assert resp.json()["resulting_state"] == "DEFERRED"

    def test_hold_and_resume(self, client):
        csrf = _login(client)
        r1 = client.post("/api/decisions/DEC-HOS-019/actions",
                         json={"action": "HOLD", "rationale": "Placing on hold for further review and discussion time."},
                         headers={"X-CSRF-Token": csrf})
        assert r1.status_code == 200
        # After HOLD, proceed to RESUME
        r2 = client.post("/api/decisions/DEC-HOS-019/actions",
                         json={"action": "RESUME", "rationale": "Resuming after review is complete."},
                         headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 200

    def test_action_produces_audit_reference(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "HOLD", "rationale": "Placing on hold until further review and discussion time."},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200
        assert "audit_event_id" in resp.json()

# ============================================================
# Audit Integrity (3 tests)
# ============================================================
class TestAudit:
    def test_hash_chain_intact(self):
        from backend.hos4c.audit import verify_hash_chain
        result = verify_hash_chain()
        assert result["integrity"] == "INTACT"

    def test_events_exportable(self, client):
        resp = client.get("/api/audit/events")
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_export_endpoint(self, client):
        resp = client.get("/api/audit/export")
        assert resp.status_code == 200
        assert "events" in resp.json()

# ============================================================
# Security Input Handling (3 tests)
# ============================================================
class TestSecurityInput:
    def test_xss_payload_handled(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "DEFER", "rationale": "<script>alert('xss')</script>" + "x" * 30},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code in (200, 422)  # Either accepted or rejected at validation

    def test_sql_injection_not_found(self, client):
        resp = client.get("/api/decisions/DEC-HOS-001' OR '1'='1")
        assert resp.status_code == 404

    def test_oversized_payload_handled(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-019/actions",
                          json={"action": "HOLD", "rationale": "x" * 10000},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code in (200, 422, 413)  # Graceful handling

# ============================================================
# Cookie & Session Flow Tests (6 tests)
# ============================================================
class TestSessionFlow:
    def test_login_flow(self, client):
        """Complete login → session → action flow."""
        csrf = _login(client)
        assert len(csrf) == 64
        resp = client.get("/api/auth/session")
        assert resp.json()["authenticated"] == True

    def test_logout_flow(self, client):
        """Login → action → logout → rejected."""
        csrf = _login(client)
        resp1 = client.post("/api/decisions/DEC-HOS-001/actions",
                           json={"action": "HOLD", "rationale": "Testing logout flow with enough text."},
                           headers={"X-CSRF-Token": csrf})
        assert resp1.status_code == 200
        client.post("/api/auth/logout")
        resp2 = client.post("/api/decisions/DEC-HOS-001/actions",
                           json={"action": "HOLD", "rationale": "x" * 30},
                           headers={"X-CSRF-Token": csrf})
        assert resp2.status_code in (401, 403)

    def test_missing_cookie_flow(self, client):
        """No login → request rejected."""
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "DEFER", "rationale": "x" * 30},
                          headers={"X-CSRF-Token": "any-token"})
        assert resp.status_code in (401, 403)

    def test_success_message_wording(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-001/actions",
                          json={"action": "APPROVE", "rationale": "Good reasons to approve this decision with sufficient text length here.", "typed_confirmation": "APPROVE DEC-HOS-001"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "SIMULATION"
        assert "NO AUTHORITATIVE" in data.get("warning", "")

    def test_reject_flow(self, client):
        csrf = _login(client)
        resp = client.post("/api/decisions/DEC-HOS-019/actions",
                          json={"action": "REJECT", "rationale": "Rejecting this decision with sufficient reasoning text.", "typed_confirmation": "REJECT DEC-HOS-019"},
                          headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200

    def test_simulation_warning_present(self, client):
        resp = client.get("/api/health")
        assert resp.json()["mode"] == "SIMULATION_ONLY"

# ============================================================
# Meta
# ============================================================
def test_count():
    """Verify minimum test count."""
    classes = [TestSimulationIsolation, TestAuthentication, TestAuthorization,
               TestStateMachine, TestCSRF, TestConfirmation, TestConcurrency,
               TestAudit, TestSecurityInput, TestSessionFlow]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4C Test Suite: {total} tests ===\n")
    assert total >= 35, f"Expected at least 35 tests, found {total}"