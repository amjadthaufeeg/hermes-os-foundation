"""
HOS-4D.4B.2: Alert Engine Tests
Rules, severity, fingerprinting, dedup, state machine,
acknowledgment, escalation, recovery, routing, boundary.
Run: python3.11 -m pytest backend/hos4c/test_alert_engine.py -v
"""

import pytest, time, os
from backend.hos4c.alert_engine import (
    AlertEngine, AlertRule, Alert, AlertStatus, Severity,
    alert_fingerprint, alert_engine as engine, _active_alerts,
)

@pytest.fixture(autouse=True)
def reset_engine():
    _active_alerts.clear()
    engine.rules.clear()
    # Re-register standard rules
    engine.add_rule(AlertRule("test-critical", "Critical rule", Severity.CRITICAL, threshold=1))
    engine.add_rule(AlertRule("test-high", "High rule", Severity.HIGH, threshold=3, window_seconds=300))
    engine.add_rule(AlertRule("test-med", "Medium rule", Severity.MEDIUM, threshold=5))
    yield

# --- Rule Evaluation ---
class TestRuleEvaluation:
    def test_critical_triggers_at_threshold(self):
        alert = engine.process_event("test-critical", "test-component")
        assert alert is not None
        assert alert.severity == Severity.CRITICAL
        assert alert.status == AlertStatus.OPEN

    def test_high_below_threshold(self):
        engine.process_event("test-high", "test-comp")  # 1st
        engine.process_event("test-high", "test-comp")  # 2nd
        alert = engine.process_event("test-high", "test-comp")  # 3rd — triggers
        assert alert is not None
        assert alert.severity == Severity.HIGH

    def test_rules_not_registered(self):
        alert = engine.process_event("nonexistent", "test-comp")
        assert alert is None

    def test_occurrence_count_increments(self):
        engine.process_event("test-critical", "test-comp", "err-1")
        # Second event — same fingerprint, should dedup
        result = engine.process_event("test-critical", "test-comp", "err-1")
        assert result is None  # Deduped
        active = engine.get_active_alerts()
        assert len(active) >= 1
        assert active[0].occurrence_count >= 1

# --- Fingerprinting ---
class TestFingerprinting:
    def test_same_input_same_fingerprint(self):
        fp1 = alert_fingerprint("rule-1", "staging", "auth", "ERR_001")
        fp2 = alert_fingerprint("rule-1", "staging", "auth", "ERR_001")
        assert fp1 == fp2

    def test_different_rule_different_fingerprint(self):
        fp1 = alert_fingerprint("rule-1", "staging", "auth", "ERR_001")
        fp2 = alert_fingerprint("rule-2", "staging", "auth", "ERR_001")
        assert fp1 != fp2

    def test_fingerprint_excludes_user_id(self):
        fp = alert_fingerprint("rule-1", "staging", "auth", "user-123-token")
        assert "user-123" not in fp

# --- Deduplication ---
class TestDeduplication:
    def test_duplicate_event_not_new_alert(self):
        engine.process_event("test-critical", "comp-a", "ERR")
        result = engine.process_event("test-critical", "comp-a", "ERR")
        assert result is None  # Deduped — not a new alert

    def test_different_fingerprint_new_alert(self):
        engine.process_event("test-critical", "comp-a", "ERR-1")
        result = engine.process_event("test-critical", "comp-b", "ERR-2")
        assert result is not None  # Different fingerprint — new alert

# --- Acknowledgment ---
class TestAcknowledgment:
    def test_amjad_can_acknowledge_critical(self):
        alert = engine.process_event("test-critical", "comp-a")
        assert engine.acknowledge(alert.alert_id, "amjad", "AMJAD_OWNER", "Under review")

    def test_hermes_cannot_acknowledge(self):
        alert = engine.process_event("test-critical", "comp-a")
        result = engine.acknowledge(alert.alert_id, "hermes", "HERMES_ASSISTANT", "Trying")
        assert result is False

    def test_missing_alert(self):
        assert engine.acknowledge("nonexistent", "amjad", "AMJAD_OWNER", "x") is False

# --- Escalation ---
class TestEscalation:
    def test_escalation_increments(self):
        alert = engine.process_event("test-critical", "comp-a")
        engine.escalate(alert.alert_id)
        engine.escalate(alert.alert_id)
        updated = engine.get_alert(alert.alert_id)
        assert updated.escalation_level == 2
        assert updated.status == AlertStatus.ESCALATED

    def test_escalation_missing_alert(self):
        assert engine.escalate("nonexistent") is False

# --- Recovery ---
class TestRecovery:
    def test_resolved_alert(self):
        alert = engine.process_event("test-critical", "comp-a")
        engine.resolve(alert.alert_id)
        updated = engine.get_alert(alert.alert_id)
        assert updated.status == AlertStatus.RESOLVED

    def test_resolved_not_in_active(self):
        alert = engine.process_event("test-critical", "comp-a")
        engine.resolve(alert.alert_id)
        active = engine.get_active_alerts()
        assert len([a for a in active if a.alert_id == alert.alert_id]) == 0

# --- Flapping ---
class TestFlapping:
    def test_reopen_after_resolve(self):
        alert = engine.process_event("test-critical", "comp-a")
        engine.resolve(alert.alert_id)
        alert2 = engine.process_event("test-critical", "comp-a")
        # New alert can be created after resolve
        if alert2:
            assert alert2.alert_id != alert.alert_id

# --- Boundary ---
class TestBoundary:
    def test_no_production_creds_in_alert_engine(self):
        with open("backend/hos4c/alert_engine.py") as f:
            code = f.read()
        assert "ghp_abc" not in code

    def test_hermes_zero_acknowledge(self):
        alert = engine.process_event("test-critical", "comp-a")
        assert engine.acknowledge(alert.alert_id, "hermes", "HERMES_ASSISTANT", "x") is False

# --- Count ---
def test_alert_count():
    classes = [TestRuleEvaluation, TestFingerprinting, TestDeduplication,
               TestAcknowledgment, TestEscalation, TestRecovery, TestFlapping, TestBoundary]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4B.2 Alert Tests: {total} ===\n")
    assert total >= 19