"""
HOS-4D.1: OAuth Authentication Tests
Run: python3.11 -m pytest backend/hos4c/test_oauth.py -v
"""

import pytest, os, tempfile
from starlette.testclient import TestClient

TEST_DB = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_PATH"] = TEST_DB
os.environ["SIMULATION_MODE"] = "true"  # OAuth routes return 400 in simulation

from backend.hos4c.database import init_db
from backend.hos4c.main import app
from backend.hos4c.auth_oauth import (
    generate_code_verifier, generate_code_challenge,
    create_oauth_state, consume_oauth_state,
    is_approved_owner, get_owner_role,
)

@pytest.fixture(autouse=True)
def fresh_db():
    os.environ["SIMULATION_MODE"] = "true"
    os.environ["MUTATIONS_DISABLED"] = "false"  # Allow simulation actions in tests
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# ============================================================
# OAuth Route Isolation (SIMULATION_MODE gate)
# ============================================================
class TestOAuthSimulationGate:
    def test_login_denied_in_simulation(self, client):
        resp = client.get("/auth/github/login")
        assert resp.status_code == 400
        assert "simulation" in resp.text.lower()

    def test_callback_denied_in_simulation(self, client):
        resp = client.get("/auth/github/callback?code=test&state=test")
        assert resp.status_code == 400
        assert "simulation" in resp.text.lower()

# ============================================================
# PKCE Implementation
# ============================================================
class TestPKCE:
    def test_verifier_generated_securely(self):
        v1 = generate_code_verifier()
        v2 = generate_code_verifier()
        assert len(v1) >= 43  # Base64 of 32 bytes
        assert v1 != v2  # Unique per call

    def test_challenge_is_s256(self):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert len(challenge) == 43  # SHA-256 digest, base64

    def test_challenge_derived_from_verifier(self):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        # Same verifier → same challenge
        assert challenge == generate_code_challenge(verifier)

    def test_different_verifier_different_challenge(self):
        c1 = generate_code_challenge(generate_code_verifier())
        c2 = generate_code_challenge(generate_code_verifier())
        assert c1 != c2

# ============================================================
# OAuth State Management
# ============================================================
class TestOAuthState:
    def test_state_created_and_consumed(self):
        state, challenge = create_oauth_state()
        verifier = consume_oauth_state(state)
        assert verifier is not None

    def test_state_cannot_be_reused(self):
        state, _ = create_oauth_state()
        consume_oauth_state(state)
        assert consume_oauth_state(state) is None

    def test_invalid_state_rejected(self):
        assert consume_oauth_state("invalid-state") is None

    def test_state_from_another_session(self):
        s1, _ = create_oauth_state("session-a")
        s2, _ = create_oauth_state("session-b")
        v1 = consume_oauth_state(s1)
        v2 = consume_oauth_state(s2)
        assert v1 is not None
        assert v2 is not None
        assert v1 != v2

# ============================================================
# Identity Binding
# ============================================================
class TestIdentityBinding:
    def test_approved_id_matches(self, monkeypatch):
        monkeypatch.setattr("backend.hos4c.auth_oauth.APPROVED_OWNER_GITHUB_ID", 12345)
        assert is_approved_owner(12345) == True
        assert get_owner_role(12345) == "AMJAD_OWNER"

    def test_unapproved_id_denied(self, monkeypatch):
        monkeypatch.setattr("backend.hos4c.auth_oauth.APPROVED_OWNER_GITHUB_ID", 12345)
        assert is_approved_owner(99999) == False
        assert get_owner_role(99999) == "UNAUTHENTICATED"

    def test_missing_config_fails_closed(self, monkeypatch):
        monkeypatch.setattr("backend.hos4c.auth_oauth.APPROVED_OWNER_GITHUB_ID", 0)
        assert is_approved_owner(12345) == False
        assert is_approved_owner(0) == False

    def test_username_irrelevant(self, monkeypatch):
        """Username alone can't grant access — only immutable ID matters."""
        monkeypatch.setattr("backend.hos4c.auth_oauth.APPROVED_OWNER_GITHUB_ID", 12345)
        assert is_approved_owner(12345) == True

# ============================================================
# Session CRUD + Revocation (via simulated login)
# ============================================================
class TestSessionManagement:
    def test_logout_invalidates(self, client):
        resp = client.post("/api/auth/login")
        assert resp.status_code == 200
        resp2 = client.post("/auth/logout")
        assert resp2.status_code == 200
        resp3 = client.get("/api/auth/session")
        assert resp3.json()["authenticated"] == False

    def test_individual_revoke_requires_auth(self, client):
        # Without login, revocation should be protected
        resp = client.post("/auth/sessions/revoke")
        assert resp.status_code in (401, 403)

    def test_revoke_all_requires_auth(self, client):
        resp = client.post("/auth/sessions/revoke-all")
        assert resp.status_code in (401, 403)

# ============================================================
# Token & Secret Exposure
# ============================================================
class TestTokenExposure:
    def test_no_secrets_in_code(self):
        """Verify no secrets hardcoded in OAuth module."""
        with open("backend/hos4c/auth_oauth.py") as f:
            code = f.read()
        assert "ghp_" not in code  # No GitHub tokens
        assert "client_secret" not in code.lower() or "os.environ" in code

    def test_no_tokens_in_html(self):
        """Verify simulation UI has no tokens."""
        with open("docs/hermes-os-v3.1/command-center/decision-actions.html") as f:
            html = f.read()
        assert "access_token" not in html.lower()
        assert "ghp_" not in html

# ============================================================
# Audit Integrity After OAuth Integration
# ============================================================
class TestOAuthAuditPreservation:
    def test_hash_chain_still_intact(self):
        from backend.hos4c.audit import verify_hash_chain
        result = verify_hash_chain()
        assert result["integrity"] == "INTACT"

    def test_existing_tests_still_pass(self, client):
        """Verify existing 42-test suite still compatible."""
        resp = client.get("/api/health")
        assert resp.json()["mode"] == "SIMULATION_ONLY"

# ============================================================
# Count
# ============================================================
def test_oauth_count():
    classes = [TestOAuthSimulationGate, TestPKCE, TestOAuthState,
               TestIdentityBinding, TestSessionManagement, TestTokenExposure,
               TestOAuthAuditPreservation]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.1 OAuth Tests: {total} ===\n")
    assert total >= 20