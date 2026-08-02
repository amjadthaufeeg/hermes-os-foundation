"""
HOS-4D.4B.1: Structured Logging + Metrics + Health Integration
JSON logs, Prometheus-compatible metrics, redaction, correlation IDs.
"""

import json, os, time, uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

# --- Log Levels ---
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# --- Redaction Rules ---
REDACTED_VALUE = "[REDACTED]"
SENSITIVE_HEADERS = {"authorization", "cookie", "x-csrf-token", "x-api-key"}
SENSITIVE_PARAMS = {"code", "state", "client_secret", "token", "access_token",
                    "csrf_token", "session_id", "private_key", "signing_key"}
SENSITIVE_FIELDS = {"rationale", "password", "secret", "key", "credential"}

def redact(value: str, field_name: str = "") -> str:
    """Redact sensitive values based on field name."""
    if not isinstance(value, str):
        return value
    name_lower = field_name.lower()
    for keyword in SENSITIVE_FIELDS:
        if keyword in name_lower:
            return REDACTED_VALUE
    # Token patterns: ghp_, sk-, eyJ (JWT), long hex
    if any(value.startswith(p) for p in ("ghp_", "sk-", "sk_")) or len(value) > 40:
        return REDACTED_VALUE
    return value

# --- Structured Logger ---
class StructuredLogger:
    def __init__(self, service: str = "hermes"):
        self.service = service
        self._metrics = MetricsRegistry()

    def _log(self, level: LogLevel, event_type: str, **kwargs):
        if os.environ.get("HERMES_ENVIRONMENT", "").upper() in ("PRODUCTION", "STAGING"):
            if level == LogLevel.DEBUG:
                return  # Debug disabled in protected envs

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "event_type": event_type,
            "service": self.service,
            "environment": os.environ.get("HERMES_ENVIRONMENT", "LOCAL_SIMULATION"),
            "correlation_id": kwargs.get("correlation_id", str(uuid.uuid4())),
            "request_id": kwargs.get("request_id", ""),
        }

        # Safe contextual fields
        for field in ("result", "failure_code", "source_component", "actor_role",
                      "decision_id", "checkpoint_id", "latency_ms", "route"):
            if field in kwargs:
                entry[field] = redact(str(kwargs[field]), field)

        print(json.dumps(entry, sort_keys=True))

    def info(self, event_type: str, **kwargs):
        self._log(LogLevel.INFO, event_type, **kwargs)

    def warning(self, event_type: str, **kwargs):
        self._log(LogLevel.WARNING, event_type, **kwargs)

    def error(self, event_type: str, **kwargs):
        self._log(LogLevel.ERROR, event_type, **kwargs)

    def critical(self, event_type: str, **kwargs):
        self._log(LogLevel.CRITICAL, event_type, **kwargs)

# --- Metrics Registry ---
class MetricsRegistry:
    def __init__(self):
        self._counters = {}
        self._gauges = {}
        self._histograms = {}

    def counter_inc(self, name: str, labels: dict = None):
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self._counters[key] = self._counters.get(key, 0) + 1

    def gauge_set(self, name: str, value: float):
        self._gauges[name] = value

    def gauge_get(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def observe(self, name: str, value: float, labels: dict = None):
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def export_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = []
        for key, val in sorted(self._gauges.items()):
            lines.append(f"# HELP {key} Gauge metric")
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {val}")
        for key, val in sorted(self._counters.items()):
            base = key.split(":")[0]
            lines.append(f"# HELP {base} Counter metric")
            lines.append(f"# TYPE {base} counter")
            lines.append(f"{key} {val}")
        return "\n".join(lines) + "\n"

# --- Global instance ---
logger = StructuredLogger()
metrics = logger._metrics

# --- Observability State ---
OBSERVABILITY_STATES = {
    "HEALTHY", "DEGRADED", "MONITORING_UNAVAILABLE",
    "OBSERVABILITY_DEGRADED", "NOT_READY"
}

def set_observability_state(state: str):
    if state in OBSERVABILITY_STATES:
        metrics.gauge_set("hermes_observability_state", 1 if state == "HEALTHY" else 0)
        if state != "HEALTHY":
            logger.warning("observability.degraded", source_component="observability",
                          failure_code=state)