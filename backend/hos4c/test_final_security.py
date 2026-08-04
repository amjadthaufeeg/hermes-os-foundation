"""
HOS-4D.5: Final Security Tests
TOCTOU, concurrency, idempotency, replay, authority, activation levels.
Run: python3.11 -m pytest backend/hos4c/test_final_security.py -v
"""

import pytest
from backend.hos4c.final_security import (
    DecisionRecord, RevisionConflict, ActivationLevel,
    get_activation_level, mutations_authorized,
    idempotency_key, execute_idempotent, IDEMPOTENCY_STORE,
    consume_token, CONSUMED_TOKENS,
    check_authority, validate_transition,
    activation_readiness, CHECKLIST,
)

# --- TOCTOU / Concurrency ---
class TestTOCTOU:
    @pytest.fixture(autouse=True)
    def enable_mutex(self, monkeypatch):
        monkeypatch.setattr("backend.hos4c.final_security.CURRENT_ACTIVATION_LEVEL", ActivationLevel.LEVEL_3)
        monkeypatch.setattr("backend.hos4c.final_security.MUTATIONS_ENABLED", True)

    def test_expected_revision_match(self):
        d = DecisionRecord("DEC-001", "draft", revision=1)
        new_rev = d.mutate("proposed", 1)
        assert new_rev == 2
        assert d.state == "proposed"

    def test_stale_revision_rejected(self):
        d = DecisionRecord("DEC-001", "draft", revision=2)
        with pytest.raises(RevisionConflict) as exc:
            d.mutate("proposed", 1)
        assert exc.value.current == 2
        assert exc.value.expected == 1

    def test_mutations_blocked_at_level_0(self, monkeypatch):
        monkeypatch.setattr("backend.hos4c.final_security.CURRENT_ACTIVATION_LEVEL", ActivationLevel.LEVEL_0)
        monkeypatch.setattr("backend.hos4c.final_security.MUTATIONS_ENABLED", False)
        d = DecisionRecord("DEC-001", "draft")
        with pytest.raises(RuntimeError, match="MUTATIONS_DISABLED"):
            d.mutate("proposed", 1)

# --- Idempotency ---
class TestIdempotency:
    @pytest.fixture(autouse=True)
    def cleanup(self):
        IDEMPOTENCY_STORE.clear()
        yield

    def test_first_execution(self):
        key = idempotency_key("amjad", "approve", "hash123")
        result = execute_idempotent(key, "hash123", lambda: {"status": "ok"})
        assert result == {"status": "ok"}
        assert key in IDEMPOTENCY_STORE

    def test_duplicate_returns_prior(self):
        key = idempotency_key("amjad", "approve", "hash123")
        execute_idempotent(key, "hash123", lambda: {"status": "first"})
        result = execute_idempotent(key, "hash123", lambda: {"status": "second"})
        assert result == {"status": "first"}  # Prior result returned

# --- Replay Protection ---
class TestReplay:
    @pytest.fixture(autouse=True)
    def cleanup(self):
        CONSUMED_TOKENS.clear()
        yield

    def test_first_use(self):
        assert consume_token("csrf-token-1")

    def test_replay_rejected(self):
        consume_token("csrf-token-1")
        assert not consume_token("csrf-token-1")

# --- Authority ---
class TestAuthority:
    def test_hermes_cannot_approve(self):
        assert not check_authority("HERMES_ASSISTANT", "approve_decision")

    def test_amjad_can_approve(self):
        assert check_authority("AMJAD_OWNER", "approve_decision")

    def test_recovery_op_cannot_mutate(self):
        assert not check_authority("RECOVERY_OPERATOR", "mutate_decision")

# --- State Transitions ---
class TestStateMachine:
    def test_valid_transition(self):
        assert validate_transition("draft", "proposed")

    def test_invalid_transition(self):
        assert not validate_transition("closed", "proposed")

    def test_terminal_state(self):
        assert not validate_transition("closed", "approved")

# --- Activation Levels ---
class TestActivation:
    def test_level_0_current(self):
        assert get_activation_level() == 0

    def test_mutations_blocked(self):
        assert not mutations_authorized()

# --- Checklist ---
class TestChecklist:
    def test_not_ready(self):
        assert activation_readiness() == "NOT_READY"

    def test_checklist_has_domains(self):
        assert len(CHECKLIST) == 5
        assert "code" in CHECKLIST
        assert "security" in CHECKLIST

# --- Count ---
def test_security_count():
    classes = [TestTOCTOU, TestIdempotency, TestReplay, TestAuthority,
               TestStateMachine, TestActivation, TestChecklist]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.5 Security Tests: {total} ===\n")
    assert total >= 15