"""
HOS-4D.4B.2: Alert Engine Foundation
Rule evaluation, fingerprinting, deduplication, acknowledgment,
escalation, recovery, isolated routing. Test mode only.
"""

import json, time, uuid, hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

from backend.hos4c.observability import logger

# --- Severity ---
class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"

# --- Alert Status ---
class AlertStatus(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"
    DELIVERY_FAILED = "DELIVERY_FAILED"

# --- Alert Record ---
@dataclass
class Alert:
    alert_id: str
    fingerprint: str
    rule_id: str
    title: str
    description: str
    severity: Severity
    status: AlertStatus
    source_component: str
    environment: str
    first_seen_at: str
    last_seen_at: str
    occurrence_count: int
    correlation_id: str
    acknowledgment_actor: str = ""
    acknowledgment_at: str = ""
    escalation_level: int = 0
    next_escalation_at: str = ""
    recovery_at: str = ""

# --- In-memory alert store (test mode) ---
_active_alerts: dict[str, Alert] = {}

# --- Fingerprint ---
def alert_fingerprint(rule_id: str, environment: str, source_component: str,
                      failure_code: str = "") -> str:
    """Deterministic fingerprint from bounded fields."""
    key = f"{rule_id}|{environment}|{source_component}|{failure_code}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

# --- Rule Evaluation ---
class AlertRule:
    def __init__(self, rule_id: str, title: str, severity: Severity,
                 threshold: int = 1, window_seconds: int = 300):
        self.rule_id = rule_id
        self.title = title
        self.severity = severity
        self.threshold = threshold
        self.window_seconds = window_seconds
        self._counters: dict[str, list[float]] = {}  # fingerprint → timestamps

    def evaluate(self, fingerprint: str, count: int = 1) -> Optional[Alert]:
        now = time.time()
        if fingerprint not in self._counters:
            self._counters[fingerprint] = []
        self._counters[fingerprint].append(now)
        # Prune old timestamps outside window
        self._counters[fingerprint] = [
            t for t in self._counters[fingerprint]
            if now - t < self.window_seconds
        ]
        total = len(self._counters[fingerprint])
        if total >= self.threshold:
            return self._create_alert(fingerprint, total)
        return None

    def _create_alert(self, fingerprint: str, count: int) -> Alert:
        now_str = datetime.now(timezone.utc).isoformat()
        return Alert(
            alert_id=str(uuid.uuid4())[:8],
            fingerprint=fingerprint,
            rule_id=self.rule_id,
            title=self.title,
            description="",
            severity=self.severity,
            status=AlertStatus.NEW,
            source_component="alert-engine",
            environment="LOCAL_SIMULATION",
            first_seen_at=now_str,
            last_seen_at=now_str,
            occurrence_count=count,
            correlation_id=str(uuid.uuid4()),
        )

# --- Alert Engine ---
class AlertEngine:
    def __init__(self):
        self.rules: dict[str, AlertRule] = {}
        self.grouping_window = 300  # 5 minutes
        self.suppression_window = 300

    def add_rule(self, rule: AlertRule):
        self.rules[rule.rule_id] = rule

    def process_event(self, rule_id: str, source_component: str,
                      failure_code: str = "") -> Optional[Alert]:
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        fp = alert_fingerprint(rule_id, "LOCAL_SIMULATION", source_component, failure_code)
        alert = rule.evaluate(fp)
        if alert:
            # Dedup: check if existing alert with same fingerprint is open
            for existing in _active_alerts.values():
                if existing.fingerprint == alert.fingerprint and \
                   existing.status not in (AlertStatus.RESOLVED, AlertStatus.SUPPRESSED):
                    existing.occurrence_count += 1
                    existing.last_seen_at = alert.last_seen_at
                    return None  # Suppressed — not a new alert
            # New alert
            alert.status = AlertStatus.OPEN
            _active_alerts[alert.alert_id] = alert
            logger.warning("alert.created", source_component="alert-engine",
                          failure_code=rule_id, decision_id=alert.alert_id)
            return alert
        return None

    def acknowledge(self, alert_id: str, actor: str, role: str,
                   reason: str) -> bool:
        alert = _active_alerts.get(alert_id)
        if not alert:
            return False
        # Only AMJAD_OWNER may acknowledge CRITICAL
        if alert.severity == Severity.CRITICAL and role != "AMJAD_OWNER":
            logger.error("alert.unauthorized_ack", source_component="alert-engine",
                        failure_code="UNAUTHORIZED_ROLE", actor_role=role)
            return False
        if role == "HERMES_ASSISTANT":
            return False
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledgment_actor = actor
        alert.acknowledgment_at = datetime.now(timezone.utc).isoformat()
        return True

    def escalate(self, alert_id: str) -> bool:
        alert = _active_alerts.get(alert_id)
        if not alert:
            return False
        alert.escalation_level += 1
        alert.status = AlertStatus.ESCALATED
        return True

    def resolve(self, alert_id: str) -> bool:
        alert = _active_alerts.get(alert_id)
        if not alert:
            return False
        alert.status = AlertStatus.RESOLVED
        alert.recovery_at = datetime.now(timezone.utc).isoformat()
        logger.info("alert.resolved", source_component="alert-engine",
                   failure_code=alert.rule_id, decision_id=alert_id)
        return True

    def get_active_alerts(self) -> list[Alert]:
        return [a for a in _active_alerts.values()
                if a.status not in (AlertStatus.RESOLVED, AlertStatus.SUPPRESSED)]

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return _active_alerts.get(alert_id)

# --- Global instance ---
alert_engine = AlertEngine()

# Register critical + high rules (test mode)
alert_engine.add_rule(AlertRule("checkpoint-signature-invalid", "Checkpoint signature invalid",
                                Severity.CRITICAL, threshold=1))
alert_engine.add_rule(AlertRule("audit-chain-mismatch", "Audit chain mismatch",
                                Severity.CRITICAL, threshold=1))
alert_engine.add_rule(AlertRule("checkpoint-missing", "Checkpoint missing > 48h",
                                Severity.CRITICAL, threshold=1))
alert_engine.add_rule(AlertRule("auth-failure-spike", "Authentication failure spike",
                                Severity.HIGH, threshold=5, window_seconds=300))
alert_engine.add_rule(AlertRule("csrf-failure-spike", "CSRF failure spike",
                                Severity.HIGH, threshold=10, window_seconds=300))
alert_engine.add_rule(AlertRule("transaction-failure-spike", "Transaction failure spike",
                                Severity.HIGH, threshold=5, window_seconds=300))
alert_engine.add_rule(AlertRule("projection-failure", "Projection failure repeated",
                                Severity.HIGH, threshold=3))