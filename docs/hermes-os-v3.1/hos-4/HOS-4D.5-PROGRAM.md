# HOS-4D.5 — Final Live-Mutation Security Review and Activation Readiness

**Status:** Planning | **No VPS. No keys. No mutations. No deployment.**

---

## 1. Objective

System-wide review of the complete authoritative mutation path. TOCTOU closure, authority matrix, database/migration safety, audit/checkpoint integrity, observability readiness, backup/recovery readiness, key custody, follow-up reconciliation, activation checklist.

## 2. System Baseline

Merged releases: HOS-4C through HOS-4D.4D. Latest main commit: `8dfe474`. 242 tests.

## 3. TOCTOU Resolution

**Recommended:** Optimistic concurrency with `expected_version` field. Each decision carries a version integer. Mutations provide `expected_version`; the database transaction compares atomically. Stale versions → 409 Conflict. This closes the race between state-read and state-write without requiring heavy locks.

## 4. Authority Matrix

| Operation | Amjad | Hermes | Recovery Op | Backup Writer | Anonymous |
|---|---|---|---|---|---|
| Create decision | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approve decision | ✅ | ❌ | ❌ | ❌ | ❌ |
| Enable mutations | ✅ | ❌ | ❌ | ❌ | ❌ |
| Production restore | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete backup | ✅ | ❌ | ❌ | ❌ | ❌ |
| Rotate keys | ✅ | ❌ | ❌ | ❌ | ❌ |
| Decrypt backup | ✅ | ❌ | ✅ (test) | ❌ | ❌ |
| Upload backup | ✅ | ❌ | ❌ | ✅ | ❌ |

## 5. Activation Levels

| Level | Scope | Current |
|---|---|---|
| 0 | Local validation only | ✅ NOW |
| 1 | Private VPS staging | ❌ |
| 2 | Production read-only | ❌ |
| 3 | Controlled authoritative writes | ❌ |
| 4 | Full approved operations | ❌ |

## 6. Follow-up Register

| ID | Title | Blocks Activation |
|---|---|---|
| HOS-4D.4B.1-FOLLOWUP-001 | Sensitive-header cleanup | No |
| HOS-4D.4B.2-FOLLOWUP-002 | Persistent escalation | No |
| HOS-4D.4C.2-FOLLOWUP-002 | Real S3 provider | Yes |
| HOS-4D.4C.2-FOLLOWUP-004 | Key rotation exercise | Yes |
| HOS-4D.4D-FOLLOWUP-001 | SQLite WAL on VPS | Yes |
| HOS-4D.4D-FOLLOWUP-002 | Real incident monitoring | Yes |
| HOS-4D.4D-FOLLOWUP-003 | Private VPS readiness | Yes |
| HOS-4D.3.1 | Migration runner | Yes |
| HOS-4D.5 | TOCTOU closure | Yes |

## 7. Activation Checklist

| Domain | Item | Status |
|---|---|---|
| Code | 242 tests, CI green | ✅ |
| Runtime | Linux staging validated | ✅ |
| Security | Authority matrix, TOCTOU | 🟡 Pending |
| Recovery | Real S3, key custody, VPS exercise | ❌ |
| Database | WAL, migrations, single-instance | 🟡 |
| Authority | Hermes=0 verified | ✅ |

## 8. Next Steps

HOS-4D.5 implementation closes TOCTOU, validates authority matrix, reconciles follow-ups, defines activation levels. Level 1 (private VPS) requires new Amjad authorization.

---

*Planning only. No VPS, no production keys, no mutations, no deployment.*