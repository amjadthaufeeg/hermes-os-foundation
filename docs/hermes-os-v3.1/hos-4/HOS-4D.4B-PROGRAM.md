# HOS-4D.4B — Monitoring and Alerting Foundation

**Status:** Planning | **Release:** HOS-4D.4B | **No deployment authorized**

---

## 1. Problem Statement

The Hermes system has no structured operational visibility. Failures in authentication, authorization, checkpoints, transactions, projections, and the database are invisible until manually inspected. HOS-4D.4B designs the minimal monitoring and alerting foundation needed to detect, classify, and respond to operational failures before live mutations are authorized.

## 2. Scope

Structured logging, health/metrics endpoints, alert severity model, deduplication/suppression/escalation, operational dashboard, monitoring runbooks.

## 3. Non-Scope

Production alert credentials, deployment, off-host storage, backup/recovery (HOS-4D.4C), incident response (HOS-4D.4D).

---

## 4. Recommended Architecture

### Hybrid Stage 1: Structured Logs + Metrics + Health Endpoints

```
Application
  ├── Structured JSON logs → systemd journal → log watcher
  ├── /api/health/live → liveness
  ├── /api/health/ready → readiness (config, DB, checkpoint, mutations)
  └── /api/metrics → Prometheus-compatible counters/gauges
```

| Component | Stage 1 | Upgrade Path |
|---|---|---|
| Logs | JSON to stdout/journal | Ship to Loki |
| Metrics | Prometheus text format on `/api/metrics` | Prometheus + Grafana |
| Alerts | In-app dashboard banner (CRITICAL) | Email/Telegram (future) |
| Dashboard | Mission Control panel | Separate monitoring dashboard |

---

## 5. Structured Log Schema

```json
{
  "timestamp": "2026-08-02T00:00:00Z",
  "level": "INFO|WARN|ERROR|CRITICAL",
  "event_type": "auth.oauth_success|checkpoint.signed|mutation.disabled",
  "environment": "LOCAL_SIMULATION",
  "correlation_id": "uuid",
  "component": "auth|checkpoint|adapter|projection",
  "result": "success|failure|denied",
  "failure_code": "STATE_MISMATCH|CSRF_INVALID|...",
  "latency_ms": 42,
  "decision_id": "DEC-001"
}
```

**Never logged:** tokens, secrets, cookies, CSRF tokens, verifiers, private keys, rationale text.

---

## 6. Metrics

| Metric | Type | Description |
|---|---|---|
| `hermes_requests_total` | Counter | Total HTTP requests |
| `hermes_request_errors_total` | Counter | Request errors by status |
| `hermes_auth_failures_total` | Counter | Failed auth attempts |
| `hermes_auth_denials_total` | Counter | Authorization denials |
| `hermes_csrf_failures_total` | Counter | CSRF validation failures |
| `hermes_checkpoint_failures_total` | Counter | Checkpoint verify/store failures |
| `hermes_checkpoint_age_seconds` | Gauge | Seconds since last checkpoint |
| `hermes_projection_backlog_total` | Gauge | Pending projections |
| `hermes_transaction_failures_total` | Counter | Failed authoritative transactions |
| `hermes_readiness_state` | Gauge | 1=ready, 0=not ready |
| `hermes_mutations_disabled` | Gauge | 1=disabled, 0=enabled |

No high-cardinality labels. No tokens in labels.

---

## 7. Alert Severity Model

| Severity | Response | Channel |
|---|---|---|
| **CRITICAL** | Immediate (15min) | Dashboard banner + future email |
| **HIGH** | Within 1h | Dashboard banner |
| **MEDIUM** | Within 24h | Dashboard indicator |
| **LOW** | Weekly review | Log only |

### Critical Alerts (10)

1. Audit checkpoint signature INVALID
2. Audit-chain hash MISMATCH
3. Database integrity FAILURE
4. Unauthorized authoritative write DETECTED
5. Hermes approval authority NONZERO
6. Mutations unexpectedly ENABLED
7. Owner identity COMPROMISE
8. Signing key COMPROMISE
9. Database CORRUPTION
10. Service cannot FAIL CLOSED

### High Alerts (8)

1. Checkpoint MISSING > 48h
2. Checkpoint STORAGE failed repeatedly
3. Projection failed > 3 retries
4. Transaction failures > 5 in 5 min
5. OAuth failures > 5 in 5 min
6. CSRF failures > 10 in 5 min
7. Readiness FAILED > 5 min
8. Secret rotation OVERDUE

---

## 8. Alert Deduplication + Suppression

- **Fingerprint:** `{alert_type}:{decision_id or component}`
- **Grouping window:** 5 minutes
- **Suppression:** Don't re-alert for same fingerprint within window
- **Repeat interval:** Every suppression window if unresolved
- **Flapping control:** 3 state changes in 10 min → suppress for 30 min
- **Recovery:** Send resolution alert when condition clears

---

## 9. Alert Acknowledgment

- Amjad may acknowledge CRITICAL/HIGH alerts
- Hermes may SURFACE but never CLOSE CRITICAL alerts
- Unacknowledged CRITICAL escalates after 1h
- Closure requires: acknowledgment + resolution evidence + timestamp

---

## 10. Monitoring Failure

When monitoring itself fails:

- Readiness reports `MONITORING_UNAVAILABLE`
- Dashboard shows `OBSERVABILITY DEGRADED`
- Existing alerts remain active (no false clearance)

---

## 11. Operational Dashboard

Minimal Mission Control panel showing:

- Service readiness + mutation-disabled status
- Checkpoint: last timestamp, age, verification status
- Auth: failure rate (last hour)
- AuthZ: denial count (last hour)
- Transactions: failure count (last hour)
- Projection: backlog count
- Active CRITICAL/HIGH alerts
- Database: integrity status

---

## 12. Sub-release Recommendation

| Release | Scope |
|---|---|
| HOS-4D.4B.1 | Structured logs + metrics endpoint |
| HOS-4D.4B.2 | Alert engine + dedup + suppression |
| HOS-4D.4B.3 | Dashboard + runbooks |

**Recommendation:** Three incremental merges for review quality.

---

## 13. Test Strategy

- Log schema validation
- Secret/token redaction in logs
- Metric correctness + bounded labels
- Alert trigger/threshold/dedup/escalation
- Monitoring failure behavior
- Hermes=0 authority for alert closure
- No production credentials

---

*Planning only. No deployment. No activation.*