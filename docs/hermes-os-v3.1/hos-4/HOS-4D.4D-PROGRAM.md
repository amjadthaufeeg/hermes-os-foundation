# HOS-4D.4D — Private Linux Staging and Incident-Response Validation

**Status:** Planning | **No real VPS, no deployment, no activation**

---

## 1. Objective

Validate Hermes Product OS on local/containerized Linux: systemd unit, Caddy reverse proxy, SQLite WAL, non-root service, backup/restore exercises, incident-response drills, RPO/RTO measurement.

## 2. Three-Tier Separation

| Tier | Scope | Authorized |
|---|---|---|
| **Tier 1** | Local Linux container/VM validation | ✅ This release |
| Tier 2 | Private VPS staging deployment | ❌ New authorization needed |
| Tier 3 | Public production deployment | ❌ New authorization needed |
| Tier 4 | Live authoritative activation | ❌ New authorization needed |

## 3. Linux Runtime Validation

- Non-root `hermes` user, systemd unit, Caddy reverse proxy
- SQLite WAL mode, filesystem permissions, secrets file 0600
- Health/readiness endpoints, structured JSON logs, Prometheus metrics

## 4. Incident Exercise Matrix

| Scenario | Exercise |
|---|---|
| Service crash | Restart, verify health, check no data loss |
| DB corruption | Detect via integrity, restore from backup, verify |
| Disk near full | Alert, prevent new writes, verify degraded mode |
| Storage unavailable | Upload fails, alert fires, retry succeeds |
| Key unavailable | Encryption blocked, key unavailable state visible |
| Backup overdue | Alert fires, manual trigger, verify |
| Restore failure | Wrong key → rejected, corruption → rejected |
| Audit mismatch | Reconciliation fails, recovery quarantined |
| Session invalidation | All sessions cleared after restore |

## 5. Recovery Exercise

1. Create test data → backup → encrypt → upload → verify
2. Retrieve → decrypt → restore → integrity → reconcile
3. Sessions invalidated → mutations confirmed disabled
4. RPO measured → RTO measured → evidence recorded

## 6. RPO/RTO

| Metric | Target | Production |
|---|---|---|
| RPO | ≤24h | NOT PROVEN |
| RTO | ≤2h | NOT PROVEN |

## 7. Reviews

Technical, security, operational, recovery/incident — all 4 required.

---

*Planning only. No real VPS, no deployment, no activation.*