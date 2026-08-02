# HOS-4D.4 — Audit Checkpoint, Monitoring, Incident Response and Recovery

**Status:** Planning | **Release:** HOS-4D.4 | **No activation authorized**

---

## 1. Problem Statement

Hermes now has 114 passing tests, an atomic authoritative adapter, production-intent auth and runtime foundations — but no external audit integrity mechanism, no operational monitoring, no incident response process, and no production backup/recovery. Before live decision mutations can be authorized, the system must be externally verifiable, observable, recoverable, and demonstrably safe.

## 2. Scope

External audit checkpoint, monitoring/alerting, incident response, emergency disable, backup/recovery with off-host storage, restore testing, staging validation, operational runbooks.

## 3. Non-Scope

Deployment, live mutations, migration runner completion (HOS-4D.3.1), TOCTOU resolution (HOS-4D.5), final activation.

---

## 4. Release Split Recommendation

| Sub-release | Scope | Rationale |
|---|---|---|
| **HOS-4D.4A** | External audit checkpoint | Smallest verifiable safety increment |
| **HOS-4D.4B** | Monitoring and alerting | Depends on checkpoint for audit alerts |
| **HOS-4D.4C** | Backup, recovery, restore testing | Lifecycle gated; needs off-host storage |
| **HOS-4D.4D** | Incident response and staging drills | Tests all prior subsystems together |

**Recommendation:** Four separate branches with independent review and rollback boundaries.

---

## 5. External Audit Checkpoint (HOS-4D.4A)

### Recommended: Hybrid — Daily Signed Git + Local Verification

```
Daily: compute SHA-256 of audit chain head → sign → commit to separate repository
On mutation: optional triggered checkpoint
Local: verify integrity on startup and readiness check
```

| Option | Verdict |
|---|---|
| Same-VPS Git repo | Rejected — not independent |
| Same-VPS file | Rejected — same security boundary |
| Separate Git repo (different credentials) | **Recommended Stage 1** |
| Off-host object storage (S3) | Recommended Stage 1+ upgrade |
| External timestamp service | Overkill for Stage 1 |

### Checkpoint Payload

```json
{
  "checkpoint_id": "CKP-2026-08-02-001",
  "timestamp": "2026-08-02T00:00:00Z",
  "audit_chain_head": "sha256:abc123...",
  "last_audit_event_id": "evt-xyz",
  "last_decision_version": 42,
  "schema_version": 1,
  "projection_status": "CURRENT",
  "environment": "PRODUCTION",
  "prev_checkpoint_hash": "sha256:prev...",
  "signature": "ed25519:sig..."
}
```

### Frequency

- Routine: daily (midnight UTC)
- High-risk mutation: triggered
- Pre/post deployment: triggered
- Incident: ad-hoc

### Signing Key

- Ed25519 key, generated offline or via KMS
- Stored separate from VPS
- Rotation: annually or on compromise
- Verification: public key on VPS (read-only)

### Verification

- Startup: verify latest checkpoint signature + chain match
- Readiness: report if last checkpoint > 25h old
- Alert: missing/invalid checkpoint → CRITICAL

---

## 6. Monitoring and Alerting (HOS-4D.4B)

### Recommended Stack: Structured Logs + Health Endpoints + Future Prometheus

| Component | Stage 1 | Upgrade Path |
|---|---|---|
| Metrics | Health endpoints (/api/health/ready) | Prometheus `/metrics` |
| Logs | Structured JSON to file | Shipping to Loki or similar |
| Alerts | CRITICAL → in-app dashboard banner | Email/SMS for high severity |

### Alert Severity Model

| Severity | Examples | Response |
|---|---|---|
| **CRITICAL** | Audit chain mismatch, signing key compromise, DB corruption | Immediate emergency disable |
| **HIGH** | OAuth failures >5/5min, CSRF failures >10/5min, missed checkpoint | Investigate within 1h |
| **MEDIUM** | Backup failure, projection stale, elevated error rate | Resolve within 24h |
| **LOW** | Session expiry spike, projection retry count | Review weekly |
| **INFO** | Normal transitions, health checks, routine backups | Log only |

### Critical Alerts

1. Audit checkpoint signature INVALID
2. Audit-chain hash MISMATCH
3. Authoritative database CORRUPTION detected
4. Unauthorized write DETECTED
5. Hermes approval authority DETECTED
6. Production mutations UNEXPECTEDLY ENABLED
7. Backup RESTORE failed
8. Signing key COMPROMISED
9. Checkpoint MISSING > 48h
10. Service unable to FAIL CLOSED

---

## 7. Emergency Disable (HOS-4D.4B)

### Kill Switch Design

```
MUTATIONS_DISABLED=true (default)
EMERGENCY_DISABLE_REASON="" (set on activation)
EMERGENCY_DISABLE_TIMESTAMP="" (set on activation)
```

**Capabilities:**
- Disable all authoritative mutations (503 response)
- Disable OAuth login (redirect to maintenance)
- Revoke all active sessions
- Halt Git projection
- Enable read-only dashboard

**NOT controllable by:**
- Browser parameters
- API requests
- Hermes agent
- SYSTEM_SERVICE

**Amjad controls:**
- Activate via `systemctl` or environment flag
- Review reason + audit event
- Restore after verification

---

## 8. Incident Response (HOS-4D.4D)

### 14 Incident Classes

| # | Incident | Severity | Containment |
|---|---|---|---|
| 1 | GitHub account compromise | CRITICAL | Revoke all sessions, disable OAuth |
| 2 | OAuth secret compromise | CRITICAL | Rotate secret, disable OAuth, audit |
| 3 | Session theft | HIGH | Revoke all sessions, alert |
| 4 | Unauthorized mutation attempt | HIGH | Block, audit, alert |
| 5 | Successful unauthorized mutation | CRITICAL | Emergency disable, investigate, Amjad review |
| 6 | Audit checkpoint failure | CRITICAL | Disable mutations, verify chain, restore |
| 7 | Audit chain mismatch | CRITICAL | Disable mutations, investigate, restore |
| 8 | Database corruption | CRITICAL | Read-only mode, restore from backup |
| 9 | Projection corruption | MEDIUM | Rebuild from authoritative DB |
| 10 | Migration failure | HIGH | Halt, restore backup, review |
| 11 | Signing key compromise | CRITICAL | Rotate key, re-sign all checkpoints, audit |
| 12 | VPS compromise | CRITICAL | Isolate, restore from off-host backup |
| 13 | TLS compromise | HIGH | Revoke cert, reissue, audit |
| 14 | Hermes boundary violation | CRITICAL | Disable mutations, audit, report |

### Authority

| Action | Who |
|---|---|
| Emergency disable | Amjad (or automated fail-closed) |
| Session revocation | Amjad |
| Secret rotation | Amjad |
| Key rotation | Amjad |
| Backup restore | Amjad |
| Mutation re-enable | Amjad ONLY |
| Hermes | **ZERO authority** |

---

## 9. Backup and Recovery (HOS-4D.4C)

### Architecture: SQLite `.backup` → Encrypted → Off-Host

```
/opt/hermes/data/audit.db
    ↓ sqlite3 .backup (consistent snapshot)
/tmp/hermes-backup-YYYYMMDD.db
    ↓ gpg encrypt
/tmp/hermes-backup-YYYYMMDD.db.gpg
    ↓ scp/rsync to off-host storage
backups@backup-host:/backups/hermes/
```

### Off-Host Storage

- Separate VPS or cloud object storage
- Different provider recommended
- GPG-encrypted at rest
- 30-day retention
- Versioned (no overwrite)

### Frequency

| Type | Frequency |
|---|---|
| Database backup | Daily |
| Audit ledger backup | Daily (same as DB) |
| Pre-migration backup | Before every migration |
| High-risk action checkpoint | Triggered |

### RPO / RTO (Stage 1 targets)

| Metric | Target | Note |
|---|---|---|
| RPO | ≤ 24 hours | Daily backup frequency |
| RTO | ≤ 2 hours | Single VPS restore + verification |
| Audit loss | ≤ 24 hours | Aligned with daily checkpoint |

### Restore Procedure (8 steps)

1. `systemctl stop hermes` — mutations disabled
2. Preserve current DB for forensics
3. Download latest backup from off-host storage
4. Decrypt (`gpg --decrypt`)
5. Restore (`sqlite3 audit.db ".restore backup.db"`)
6. Verify: integrity check + audit chain + checkpoint
7. Invalidate all sessions
8. `systemctl start hermes` — read-only initially, Amjad re-enables

---

## 10. Linux Staging Gates (HOS-4D.4D)

| Gate | Command | Status |
|---|---|---|
| Caddy validate | `caddy validate --config deploy/Caddyfile` | DEFERRED → execute in staging |
| systemd-analyze | `systemd-analyze verify deploy/hermes.service` | DEFERRED → execute in staging |
| Restore drill | Full restore from off-host backup | Scheduled in staging |

---

## 11. Operational Runbooks (7)

1. Service unavailable → check systemd, Caddy, health endpoint
2. OAuth unavailable → verify GitHub, secrets, callback URI
3. Database corruption → emergency disable, restore from backup
4. Checkpoint invalid → verify signing key, re-sign, investigate
5. Backup failed → check off-host connectivity, retry, alert
6. Emergency disable → activate, audit, preserve evidence
7. Safe read-only mode → disable mutations, keep dashboard operational

---

## 12. HOS-4D.4 Blockers Addressed

| Blocker | Status After HOS-4D.4 |
|---|---|
| External audit checkpoint | ✅ Designed |
| Operational monitoring | ✅ Designed |
| Incident response | ✅ Planned |
| Production backup/recovery | ✅ Designed |
| Caddy binary validate | ✅ Gated for staging |
| systemd-analyze | ✅ Gated for staging |

## Remaining (4)

TOCTOU resolution, live-mutation review, migration runner, final Amjad activation.

---

*Planning only. No deployment. No activation.*