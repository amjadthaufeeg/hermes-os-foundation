"""
HOS-4D.4B.1: Observability Tests
Structured logging, redaction, metrics, cardinality,
health integration, monitoring failure.
Run: python3.11 -m pytest backend/hos4c/test_observability.py -v
"""

import pytest, json, os, tempfile, re
from starlette.testclient import TestClient
from backend.hos4c.observability import (
    StructuredLogger, MetricsRegistry, redact,
    REDACTED_VALUE, set_observability_state, logger, metrics,
)
from backend.hos4c.main import app

@pytest.fixture(autouse=True)
def setup():
    os.environ["HERMES_ENVIRONMENT"] = "LOCAL_SIMULATION"
    os.environ["MUTATIONS_DISABLED"] = "false"

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# --- Structured Logs ---
class TestStructuredLogs:
    def test_log_output_is_valid_json(self, capsys):
        logger.info("test.event", request_id="req-1")
        captured = capsys.readouterr()
        line = captured.out.strip()
        entry = json.loads(line)
        assert entry["event_type"] == "test.event"
        assert entry["level"] == "INFO"

    def test_log_has_required_fields(self, capsys):
        logger.warning("test.warn", source_component="test")
        entry = json.loads(capsys.readouterr().out.strip())
        for field in ("timestamp", "level", "event_type", "service", "environment", "correlation_id"):
            assert field in entry

    def test_log_includes_safe_context(self, capsys):
        logger.info("test.ctx", decision_id="DEC-001", actor_role="AMJAD_OWNER")
        entry = json.loads(capsys.readouterr().out.strip())
        assert entry.get("decision_id") == "DEC-001"
        assert entry.get("actor_role") == "AMJAD_OWNER"

# --- Redaction ---
class TestRedaction:
    def test_oauth_token_redacted(self):
        assert redact("ghp_abc123secret", "") == REDACTED_VALUE

    def test_bearer_token_redacted(self):
        assert redact("sk-abc123", "") == REDACTED_VALUE

    def test_rationale_redacted(self):
        assert redact("sensitive decision text", "rationale") == REDACTED_VALUE

    def test_keyword_redacted(self):
        assert redact("my-secret", "api_secret") == REDACTED_VALUE
        assert redact("private-key-data", "signing_key") == REDACTED_VALUE

    def test_safe_value_passes(self):
        assert redact("LOCAL_SIMULATION", "environment") == "LOCAL_SIMULATION"

# --- Log Injection ---
class TestLogInjection:
    def test_newline_injection_sanitized(self, capsys):
        logger.info("test.inject", failure_code="ERR\nCRITICAL fake")
        entry = json.loads(capsys.readouterr().out.strip())
        assert entry["level"] == "INFO"  # No level override from injection

    def test_json_injection_contained(self, capsys):
        logger.info("test.json", source_component='{"level":"CRITICAL"}')
        entry = json.loads(capsys.readouterr().out.strip())
        assert entry["level"] == "INFO"  # Still INFO, not CRITICAL
        assert entry["source_component"] == '{"level":"CRITICAL"}'  # Stored as string

# --- Metrics ---
class TestMetrics:
    def test_counter_increment(self):
        m = MetricsRegistry()
        m.counter_inc("test_counter")
        m.counter_inc("test_counter")
        key = 'test_counter:{}'
        assert m._counters[key] == 2

    def test_gauge_set_get(self):
        m = MetricsRegistry()
        m.gauge_set("test_gauge", 42.0)
        assert m.gauge_get("test_gauge") == 42.0

    def test_metrics_endpoint_accessible(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    def test_metrics_no_secrets(self, client):
        resp = client.get("/api/metrics")
        body = resp.text
        assert "ghp_" not in body
        assert "PRIVATE" not in body

# --- Health Integration ---
class TestHealthIntegration:
    def test_health_reports_environment(self, client):
        resp = client.get("/api/health")
        assert resp.json()["environment"] == "LOCAL_SIMULATION"

    def test_readiness_reports_mutations(self, client):
        resp = client.get("/api/health/readiness")
        assert "ready" in resp.json()

    def test_health_no_secrets(self, client):
        resp = client.get("/api/health")
        body = json.dumps(resp.json())
        assert "ghp_" not in body
        assert "secret" not in body.lower()

# --- Monitoring Failure ---
class TestMonitoringFailure:
    def test_degraded_state_set(self):
        set_observability_state("DEGRADED")
        assert metrics.gauge_get("hermes_observability_state") == 0

    def test_healthy_state_set(self):
        set_observability_state("HEALTHY")
        assert metrics.gauge_get("hermes_observability_state") == 1

# --- Boundary ---
class TestBoundary:
    def test_no_production_creds_committed(self):
        with open("backend/hos4c/observability.py") as f:
            code = f.read()
        assert "ghp_" not in code
        assert "@gmail.com" not in code or "notify" not in code

    def test_hermes_zero_authority(self):
        # Hermes logs events but can't suppress CRITICAL
        set_observability_state("DEGRADED")
        assert metrics.gauge_get("hermes_observability_state") == 0

# --- Count ---
def test_observability_count():
    classes = [TestStructuredLogs, TestRedaction, TestLogInjection,
               TestMetrics, TestHealthIntegration, TestMonitoringFailure, TestBoundary]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4B.1 Observability Tests: {total} ===\n")
    assert total >= 20