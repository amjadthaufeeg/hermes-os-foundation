# Phase B — Production Read-Only Readiness Plan

**Status:** Planning | **No production systems connected. No production credentials. No authorization to read production data.**

---

## 1. Business Objective

Deploy Hermes Product OS with read-only access to production data sources so that the system can observe, monitor, alert, and verify — without any path to modify, approve, or mutate production state.

## 2. What "Read-Only" Means

- Hermes can read production database records for verification and monitoring
- Hermes can generate reports, alerts, and evidence from production data
- Hermes **cannot** execute INSERT, UPDATE, DELETE, or DDL on production tables
- Hermes **cannot** approve or reject decisions
- Hermes **cannot** mutate authoritative state
- Hermes **cannot** modify audit records
- The database connection is opened in read-only mode at the SQLite level

## 3. Production Data Sources

| Source | Access | Purpose |
|---|---|---|
| Production SQLite database | Read-only | Monitor decisions, audit chain, checkpoints |
| B2 backups | Reader only | Verify backup integrity |
| System metrics | Read | Health monitoring |

## 4. New Credentials Required

| Credential | Purpose | Custody |
|---|---|---|
| Production DB read-only credential | SQLite file access | Restricted host path, mode 400 |
| Production B2 reader key | Verify production backups | Separate from staging |
| Production alert destination | Real alerts | Amjad configures |

## 5. Credential Custody

- Production read-only credentials must be separate from staging credentials
- No credential may grant write access to any production system
- Hermes runtime receives only read-only credentials
- Write-capable credentials (recovery, admin) remain in Amjad's custody only

## 6. Network Trust Boundaries

- Production database is local to the production VPS (not Phase B scope)
- Phase B connects to production data sources from an isolated environment
- No public exposure of production data
- All access via private network or local filesystem only

## 7. Read-Only Enforcement

| Layer | Enforcement |
|---|---|
| SQLite | Connection opened with `?mode=ro` |
| Filesystem | Database file mode 400 (read-only) |
| Application | All mutation paths gated by `MUTATIONS_DISABLED=true` |
| Activation | LEVEL_2 disables all write operations |
| Authority | Hermes approval/mutation/recovery authority = 0 |

## 8. Proof Hermes Cannot Mutate

- Integration test: attempt INSERT/UPDATE/DELETE on read-only connection → must fail
- Integration test: attempt decision approval → must be rejected
- Integration test: attempt backup deletion → must be rejected
- Production acceptance: verified by independent security review

## 9. Production Database Access

**CRITICAL ARCHITECTURE DECISION: Snapshot/replica only. Direct live mount is REJECTED.**

SQLite in WAL mode requires write access...[truncated]

## 10. Logging and Audit

- All production read access logged with timestamp, query type, and source
- No production data values in logs
- Redaction rules apply to production data in logs
- Audit trail of Phase B activation recorded

## 11. Alerting

- Real alert delivery must be operational before Phase B activation
- Alerts for: service down, database unreachable, unauthorized write attempt, read-only violation
- Telegram alert configuration remains deferred from Phase A

## 12. Backup Implications

- Phase B does not create production backups
- Production backup schedule remains separate
- B2 reader key for production backup verification only

## 13. Rollback/Disable

- Phase B can be disabled by setting `MUTATIONS_DISABLED=true` and `ACTIVATION_LEVEL=1`
- Kill switch: remove production database file access
- Rollback: revert to Phase A configuration within one deployment cycle

## 14. Failure Modes

| Failure | Detection | Response |
|---|---|---|
| DB unreachable | Health check fails | Alert, fall back to cached state |
| Write attempt detected | Read-only error logged | Alert, investigate |
| Credential leak | Audit log review | Rotate credentials, incident response |
| Unauthorized access | Auth log review | Revoke access, investigate |

## 15. Security Threats

| Threat | Mitigation |
|---|---|
| Production data exfiltration | Read-only access, no export endpoints, logging |
| Credential escalation | Separate read-only credentials, filesystem enforced |
| Accidental write | SQLite read-only mode, application gates, activation level |
| Insider access | Least privilege, audit logging, Amjad-only authorization |

## 16. Blast Radius

- Phase B blast radius: production database observation only
- Cannot affect: production writes, existing services, authentication, decisions
- Worst case: production data read by unauthorized party if credentials leaked
- Mitigation: read-only credentials, no network exposure, audit logging

## 17. Kill Switch

- Remove production database mount from container
- Set `ACTIVATION_LEVEL=1` (back to Phase A)
- Restart container
- Verify mutations remain disabled

## 18. RPO/RTO Validation

- Production RPO: NOT PROVEN (requires production backup schedule)
- Production RTO: NOT PROVEN (requires production restore exercise)
- Phase B validates: read-only monitoring uptime and alert delivery latency

## 19. Deferred Controls

- Production write capabilities (Phase C)
- Production key custody (separate authorization)
- Production restore exercises (Phase C)
- Full incident response (Phase C-D)

## 20. Authorization Gates

| Gate | Authority |
|---|---|
| Phase B plan approval | Amjad |
| Production credential creation | Amjad |
| Phase B activation | Amjad |
| Phase C planning | Amjad |

---

## Permitted vs Not Permitted

| Permitted | NOT Permitted |
|---|---|
| Read production database | Write to production database |
| Monitor production state | Approve/reject decisions |
| Verify backup integrity | Delete production backups |
| Generate alerts from production data | Modify production configuration |
| Produce reports from production data | Create production keys |

---

*Planning only. No production systems connected. No production credentials. No production reads.*