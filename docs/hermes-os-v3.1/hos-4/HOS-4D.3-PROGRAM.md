# HOS-4D.3 — Authoritative Decision Adapter and Migration Foundation

**Status:** Planning | **Release:** HOS-4D.3 | **No authoritative writes authorized**

---

## 1. Problem Statement

HOS-4C provides a simulation-only decision action system with server-side role enforcement, CSRF, sessions, and an audit ledger. HOS-4D.1-4D.2 delivered production-intent authentication and runtime foundations. But the system has no authoritative decision source — actions are performed against in-memory simulation data. HOS-4D.3 designs the controlled boundary where simulated actions become authoritative decisions backed by persistent storage, versioning, and an audit trail.

## 2. Scope

Authoritative source architecture, SQLite operational decision database, adapter interface, transaction contract, versioning, idempotency, Git-backed read-only projection, migration runner, legacy decision import, conflict handling, corrective actions.

## 3. Non-Scope

Authoritative writes, deployment, live mutations, external audit checkpoint, monitoring, production backup/recovery (HOS-4D.4).

---

## 4. Authoritative Source Recommendation

### Recommended: Hybrid — SQLite Operational + Git Read-Only Projection

```
SQLite decisions table (authoritative runtime)
    ↓
Append-only audit ledger (same transaction)
    ↓
Periodic Git export of decision snapshots (read-only projection)
```

| Criterion | SQLite-only | Git-only | Hybrid SQLite+Git |
|---|---|---|---|
| Transactional consistency | ✅ | ❌ | ✅ |
| Human readability | ⚠️ | ✅ | ✅ (via Git) |
| Concurrency | ✅ (single writer) | ❌ | ✅ |
| Rollback | ✅ | ✅ | ✅ |
| Complexity | Low | Low | Medium |
| Stage 1 suitability | ✅ | ❌ | ✅ |

**Rationale:** Git alone cannot provide transactional consistency for mutations. SQLite alone loses the human-readable governance history. The hybrid model keeps SQLite as the single writable authority with Git as a read-only governance projection.

---

## 5. Canonical Source Declaration

| Representation | Role |
|---|---|
| SQLite `decisions` table | **Authoritative** — single writable source |
| Audit ledger (SQLite) | Append-only evidence chain |
| Git YAML export | Read-only governance projection |
| Dashboard API response | Cache (derived from authoritative) |
| Simulation SIM_DECISIONS | Non-authoritative (HOS-4C only) |

**Rule:** Only the SQLite decisions table may be written through the authoritative adapter. No other path creates, updates, or deletes authoritative decision records.

---

## 6. Adapter Interface Contract

```python
# === Read Operations ===
get_decision(decision_id: str) -> DecisionRecord | None
list_decisions(filters: dict = {}) -> list[DecisionRecord]
get_decisions_by_state(state: str) -> list[DecisionRecord]
get_version(decision_id: str) -> int

# === Mutation Operations ===
apply_transition(
    decision_id: str,
    action: str,
    expected_state: str,
    expected_version: int,
    actor_id: str,
    actor_role: str,
    rationale: str,
    idempotency_key: str,
    correlation_id: str,
    evidence_ids: list[str] = [],
) -> TransitionResult

# === Migration Operations ===
import_legacy_decision(record: dict) -> ImportResult
dry_run_import(records: list[dict]) -> DryRunReport

# === Projection ===
export_decisions(format: str = "yaml") -> str
verify_projection() -> VerificationResult
```

---

## 7. Transaction Contract

```
apply_transition():
1.  Verify mutations_enabled = true
2.  Verify actor_role in ROLE_PERMISSIONS for action
3.  Validate idempotency (check key not already used)
4.  Read current decision from authoritative DB
5.  Verify current_state == expected_state
6.  Verify current_version == expected_version
7.  Validate transition in state machine
8.  Validate rationale and confirmation
9.  BEGIN TRANSACTION
10.   Prepare audit event (previous state, action, resulting state)
11.   UPDATE decisions SET state=target, version=version+1
12.   INSERT audit event
13.   INSERT idempotency record
14.   Re-read decision to verify resulting state
15. COMMIT TRANSACTION
16. Return TransitionResult with new state, version, audit_id

Failure: ROLLBACK entire transaction. Return error with reason.
```

**Atomicity guarantee:** State write + audit write + idempotency write share one SQLite transaction. Partial success is impossible.

---

## 8. Decision Schema

```sql
CREATE TABLE authoritative_decisions (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    project         TEXT NOT NULL,
    workflow_state  TEXT NOT NULL,  -- HOS-4C normalized state
    display_status  TEXT,           -- Frozen HOS-3 display status
    owner           TEXT NOT NULL DEFAULT 'amjad',
    risk            TEXT DEFAULT 'NOT_ASSESSED',
    options         TEXT,           -- JSON array
    recommendation  TEXT,
    requested_action TEXT,
    rationale       TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    due_at          TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    source_origin   TEXT DEFAULT 'LEGACY_IMPORT',
    source_reference TEXT,
    evidence_ids    TEXT,           -- JSON array
    related_task_ids TEXT,
    related_release_ids TEXT,
    related_commit_refs TEXT,
    last_action     TEXT,
    last_actor_id   TEXT,
    last_audit_event_id TEXT,
    export_status   TEXT DEFAULT 'NOT_EXPORTED',
    export_version  INTEGER DEFAULT 0,
    archived_at     TEXT
);
```

---

## 9. Workflow State Mapping

| Legacy Source Value | Normalized HOS-4C State | Confidence | Migration Warning |
|---|---|---|---|
| `locked` | `LOCKED` | HIGH | None |
| `proposed` | `AWAITING_AMJAD` | HIGH | None |
| `approved` | `APPROVED` | HIGH | None |
| `rejected` | `REJECTED` | HIGH | None |
| `deferred` | `DEFERRED` | HIGH | None |
| `closed` | `CLOSED` | MEDIUM | Verify whether CLOSED means APPROVED |
| `hold` | `HOLD` | HIGH | None |
| `blocked` | `BLOCKED` | HIGH | None |
| Unknown value | `MIGRATION_REVIEW_REQUIRED` | — | Manual review required |

**Rule:** Ambiguous records (e.g., `closed` maps to both APPROVED and CLOSED) → `MIGRATION_REVIEW_REQUIRED`. No automatic conversion.

---

## 10. Migration Runner

```
Schema version table: schema_versions(migration_id, checksum, applied_at)
Migration lock: single-writer SQLite lock
Dry run: validates all records, reports stats, creates zero writes
Pre-flight: validates schema compatibility, lock availability
Pre-migration backup: sqlite3 .backup before any write
Forward migration: INSERT INTO authoritative_decisions
Failed migration: ROLLBACK + halt + report
Rollback migration: compensating DELETE (with audit record)
```

---

## 11. Legacy Decision Import Classification

For each existing `.hermes/registers/decisions/DEC-*.yaml` record:

| Classification | Criteria | Count Estimate |
|---|---|---|
| READY | Valid schema, unique ID, known state, has owner | TBD |
| READY_WITH_WARNINGS | Valid but missing optional fields | TBD |
| MANUAL_REVIEW_REQUIRED | Ambiguous state, duplicate ID, missing required fields | TBD |
| REJECTED | Malformed, no ID, no title | TBD |

No inference. No fabricated values. Missing data → `NULL` or `NOT_RECORDED`.

---

## 12. Git Projection Model

- **Format:** YAML, one file per decision in `.hermes/registers/decisions/`
- **Commit identity:** `Hermes <hermes@hermes-os.local>` — automated, non-human
- **Branch:** `main` (governance projection only — not a writable authority)
- **Frequency:** After every successful mutation + periodic (hourly) reconciliation
- **Conflict:** If Git export fails, retry with backoff. Mark decision `export_status=FAILED`. Alert.
- **Verification:** `verify_projection()` compares authoritative DB snapshot to Git files. Mismatches → alert.

**Hermes must not have write access to the Git export.** Export is performed by a service account with push access only to the decisions path.

---

## 13. Conflict Handling

| Scenario | Behavior |
|---|---|
| Stale version (UI behind DB) | 409 Conflict → refresh UI |
| Concurrent mutation attempt | 409 Conflict (version check) |
| Git export stale | Retry with backoff; mark `export_status=STALE` |
| Manual YAML edit after migration | Ignored (DB is authoritative) |
| Duplicate ID in migration | Rejected → MANUAL_REVIEW_REQUIRED |
| Duplicate mutation request | 409 Conflict (idempotency key) |

**No last-write-wins.** Conflicts always fail closed.

---

## 14. Corrective Actions

| Action | Behavior |
|---|---|
| REOPEN | Return decision to AWAITING_AMJAD with reason |
| SUPERSEDE | Mark as SUPERSEDED, reference new decision ID |
| CORRECT | Create new version with corrected data, reference original |
| REVERSE_WITH_REASON | Reverse prior action, record reason, new audit event |

**Original history never deleted.** All corrections create new versions.

---

## 15. Activation Blockers Affected

| Blocker | Status After HOS-4D.3 |
|---|---|
| Authoritative decision adapter | ✅ Designed (NOT activated) |
| Migration runner | ✅ Designed (NOT executed on production) |

## Remaining After HOS-4D.3 (8)

External audit checkpoint, monitoring, incident response, backup/recovery, Caddy binary validate, systemd-analyze verify, live-mutation review, final Amjad activation.

---

*Planning only. No authoritative writes. No deployment. No activation.*