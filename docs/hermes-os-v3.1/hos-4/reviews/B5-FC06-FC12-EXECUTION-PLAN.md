# B5 — FC-06 through FC-12 Execution Plan

**All scenarios reviewed against current production architecture. No execution.**

---

## Architecture Context Update

The original G1.2 fail-closed plan was designed for **Test-B** (LOCAL_TEST, synthetic credentials, internal network). The current production Phase B architecture has evolved significantly:

| Aspect | Original (G1.2 Plan) | Current (B5) |
|---|---|---|
| Target | Test-B container | **B4 Phase-B reader** + production snapshot |
| Network | internal:true | internal:true (same principle) |
| Credentials | B2 stubs | **No B2 credentials** (snapshot-only) |
| Database | Stub source | **Production snapshot** (refreshed every 15 min) |
| Decisions | Synthetic test data | **Authoritative production decisions** |

**Many original scenarios are superseded or need reinterpretation for the current architecture.**

---

## FC-01 — Missing Credential

| Field | Value |
|---|---|
| **Original requirement** | Remove B2_READER_KEY_ID mount, verify no staging fallback |
| **Current applicability** | **SUPERSEDED** — Phase B reader uses snapshot-only architecture. No B2 credentials are mounted. No credential fallback exists. |
| **Expected behavior** | Already proven: NO_B2_CREDENTIALS, no fallback, no crash |
| **Risk** | NONE (architecture change eliminated the concern) |
| **Execution** | NOT REQUIRED — proven by current steady state |
| **Classification** | SUPERSEDED ✅ |

---

## FC-02 — Invalid Credential

| Field | Value |
|---|---|
| **Original requirement** | Replace B2 credentials with invalid values |
| **Current applicability** | **SUPERSEDED** — No B2 credentials in architecture |
| **Expected behavior** | Already proven: no credential validation path exists |
| **Risk** | NONE |
| **Execution** | NOT REQUIRED |
| **Classification** | SUPERSEDED ✅ |

---

## FC-03 — Missing Snapshot

| Field | Value |
|---|---|
| **Original requirement** | Remove snapshot file, verify fail-closed |
| **Current applicability** | **DIRECTLY APPLICABLE** |
| **Expected behavior** | Application fails to read snapshot, returns error (currently HTTP 500) |
| **PASS criteria** | No staging/simulation fallback, no crash, mutations DISABLED |
| **Observed result** | ✅ PASS — returns HTTP 500, no fallback |
| **Current behavior** | Generic HTTP 500. Adequate for fail-closed. P2: improve to explicit 503. |
| **Target** | B4 reader |
| **Restore** | Recreate snapshot via `systemctl start hermes-snapshot-refresh.service` |
| **Execution order** | **1st** (safe, no data risk since snapshot is a copy) |

---

## FC-04 — Corrupt Snapshot

| Field | Value |
|---|---|
| **Original requirement** | Replace snapshot with non-DB file |
| **Current applicability** | **DIRECTLY APPLICABLE** |
| **Expected behavior** | SQLite integrity check fails, no data served |
| **PASS criteria** | "file is not a database" error, no fallback, mutations DISABLED |
| **Observed result** | ✅ PASS — SQLite reports corrupt, HTTP 500, no fallback |
| **Current behavior** | Acceptable. P2: explicit error message. |
| **Target** | B4 reader |
| **Restore** | Recreate snapshot |
| **Execution order** | **2nd** (after FC-03 restore) |

---

## FC-05 — Stale Snapshot

| Field | Value |
|---|---|
| **Original requirement** | Snapshot timestamp > policy threshold → refuse reads |
| **Current applicability** | **DIRECTLY APPLICABLE — CURRENTLY FAILING** |
| **Observed** | Stale snapshot served (HTTP 200, empty decisions) |
| **Root cause** | No freshness enforcement implemented yet |
| **Expected** | Health reports STALE, reads refused, mutations DISABLED |
| **Remediation** | Branch `b5-fc05-snapshot-freshness` (under review — see B5 independent review) |
| **Target** | B4 reader |
| **Restore** | `touch` snapshot to current time or recreate snapshot |
| **Execution order** | **3rd** — after FC-05 remediation is merged and deployed |

**See B5-OVERNIGHT-INDEPENDENT-REVIEW.md for detailed FC-05 architecture analysis.**

---

## FC-06 — Missing Mount

| Field | Value |
|---|---|
| **Original requirement** | Remove snapshot mount from compose |
| **Current applicability** | **APPLICABLE — reinterpreted** |
| **Current architecture** | B4 reader mounts published snapshot via `:ro` bind mount. Removing mount means no snapshot path |
| **Expected behavior** | Path absent → container fails to open DB → fail closed |
| **PASS criteria** | Graceful failure, mutations DISABLED |
| **Target** | B4 reader |
| **Change** | Comment out snapshot bind mount line in production compose |
| **Restore** | Restore mount line, recreate container |
| **Execution order** | **4th** (after FC-05) |

---

## FC-07 — External/B2 Unavailable

| Field | Value |
|---|---|
| **Original requirement** | B2 endpoint unreachable → graceful degradation |
| **Current applicability** | **SUPERSEDED** — No B2 credentials or backup verification in current architecture |
| **Current state** | `internal: true` network blocks all outbound. No B2 dependency. |
| **Classification** | SUPERSEDED ✅ (architecture eliminated the dependency) |

---

## FC-08 — Metrics Unavailable

| Field | Value |
|---|---|
| **Original requirement** | Metrics source absent → graceful degradation |
| **Current applicability** | **NOT APPLICABLE** — Metrics are Phase C concern |
| **Classification** | NOT APPLICABLE — deferred |

---

## FC-09 — Policy Mismatch (MUTATIONS_DISABLED=false)

| Field | Value |
|---|---|
| **Original requirement** | Set MUTATIONS_DISABLED=false → gate still active |
| **Current applicability** | **DIRECTLY APPLICABLE — ALREADY PROVEN** |
| **Implementation** | GAP-001 (TASK-001) enforces policy cross-validation |
| **Observed** | PRODUCTION + false → container exits at startup (RuntimeError) |
| **PASS criteria** | ✅ Already satisfied |
| **Classification** | COMPLETE (via GAP-001) ✅ |

---

## FC-10 — Invalid Environment

| Field | Value |
|---|---|
| **Original requirement** | HERMES_ENVIRONMENT=INVALID_ENV → container exits |
| **Current applicability** | **DIRECTLY APPLICABLE — ALREADY PROVEN** |
| **Implementation** | Environment enum raises ValueError at module import |
| **Observed** | Container exits before serving |
| **PASS criteria** | ✅ Already satisfied |
| **Classification** | COMPLETE (proven during Test-B G1.2) ✅ |

---

## FC-11 — Malformed Configuration

| Field | Value |
|---|---|
| **Original requirement** | Broken YAML → compose validation blocks |
| **Current applicability** | **DIRECTLY APPLICABLE — ALREADY PROVEN** |
| **Implementation** | `docker compose config` catches syntax errors |
| **Observed** | Deployment blocked before container creation |
| **PASS criteria** | ✅ Already satisfied |
| **Classification** | COMPLETE (proven during Test-B G1.2) ✅ |

---

## FC-12 — Service Restart

| Field | Value |
|---|---|
| **Original requirement** | Restart preserves all security state |
| **Current applicability** | **DIRECTLY APPLICABLE** |
| **Expected behavior** | After restart: same image, same env, mutations DISABLED, snapshot intact |
| **Target** | B4 reader (production container) |
| **Change** | `docker compose restart` or `docker compose down && up -d` |
| **Restore** | N/A |
| **Execution order** | **5th** (safe, non-destructive) |

---

## Mandatory Restore Checkpoints

| After Scenario | Restore |
|---|---|
| FC-03 → | Recreate snapshot via timer service |
| FC-04 → | Recreate snapshot |
| FC-05 → | Reset snapshot timestamp or recreate |
| FC-06 → | Restore compose mount line |
| FC-12 → | N/A (non-destructive) |

---

## Revised B5 Execution Sequence

| Order | Scenario | Target | Classification |
|---|---|---|---|
| 0 | FC-01, FC-02, FC-07, FC-08, FC-09, FC-10, FC-11 | — | **Already COMPLETE or SUPERSEDED** |
| 1 | FC-03 — Missing Snapshot | B4 reader | ✅ PASS (known behavior) |
| 2 | FC-04 — Corrupt Snapshot | B4 reader | ✅ PASS (known behavior) |
| 3 | **FC-05 — Stale Snapshot** | B4 reader | **REMEDIATION REQUIRED** |
| 4 | FC-06 — Missing Mount | B4 reader | Pending |
| 5 | FC-12 — Service Restart | B4 reader | Pending |
| — | FC-05 regression verification | B4 reader | After remediation |

---

**B5 completion blocked on FC-05 remediation. All other scenarios complete or superseded. Restore between every destructive test.**