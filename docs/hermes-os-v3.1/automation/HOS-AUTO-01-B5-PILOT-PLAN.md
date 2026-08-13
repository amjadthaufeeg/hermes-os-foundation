# HOS-AUTO-01 — B5 Pilot Plan

**First real workload for the execution bridge. Design only — no execution.**

---

## 1. Objective

After R1 is operational, use the remaining B5 fail-closed scenarios as the first controlled workload. This validates the bridge against a real, safety-critical test sequence.

---

## 2. B5 Scenario Authority Classification

| Scenario | Authority | Rationale |
|---|---|---|
| FC-05 remediation verification | **AUTO** | Disposable reader, no production |
| FC-03 regression (missing snapshot) | **AUTO** | Disposable reader |
| FC-04 regression (corrupt snapshot) | **AUTO** | Disposable reader |
| FC-05 regression (stale snapshot) | **AUTO** | Disposable reader |
| FC-06 (missing mount) | **GATED** | Requires reader compose modification |
| FC-12 (service restart) | **GATED** | Restarts Phase-B reader |
| FC-07 (external unavailable) | **AUTO** | Already steady-state, read-only |
| FC-08 (metrics) | N/A | NOT APPLICABLE |
| FC-09 (policy mismatch) | **GATED** | Env var change + restart |
| FC-10 (invalid env) | **GATED** | Env var change + restart |
| FC-11 (malformed config) | **AUTO** | Compose validation only, no container change |

---

## 3. Execution Sequence

```
1. FC-05 remediation verification (AUTO)
2. FC-03 regression (AUTO) — restore between
3. FC-04 regression (AUTO) — restore between
4. FC-05 regression (AUTO) — restore between
5. FC-06 missing mount (GATED) — restore mount
6. FC-12 service restart (GATED) — non-destructive
7. FC-09 policy mismatch (GATED) — restore env
8. FC-10 invalid env (GATED) — restore env
9. FC-11 malformed config (AUTO) — restore compose
```

---

## 4. Per-Scenario Contract Template

```yaml
task_id: B5-FC06
authority_class: GATED
authorization_token: AUTH-2026-XXXX
target: hermes-phase-b-reader
before_assertions:
  - reader_healthy
  - production_healthy
  - mutations_disabled
operations:
  - modify_reader_compose   # remove snapshot mount
  - recreate_reader
after_assertions:
  - http_503
  - no_simulation_fallback
  - mutations_disabled
restore:
  - restore_compose
  - recreate_reader
  - verify_healthy
```

---

## 5. Restore Checkpoints

Every destructive scenario MUST restore before the next scenario begins.

| Scenario | Restore Action |
|---|---|
| FC-03 | Recreate snapshot via timer service |
| FC-04 | Recreate valid snapshot |
| FC-05 | Reset snapshot timestamp / recreate |
| FC-06 | Restore compose mount line |
| FC-09 | Restore `MUTATIONS_DISABLED=true` |
| FC-10 | Restore valid `HERMES_ENVIRONMENT` |
| FC-11 | Restore compose from backup |

Bridge enforces: **next scenario cannot start until previous restore is verified.**

---

## 6. Evidence Required

Per scenario:
- stdout/stderr logs
- before/after state JSON
- assertion results
- HTTP response codes
- container health checks
- decision/audit count deltas
- receipt with verdict

---

## 7. Abort Conditions

| Condition | Action |
|---|---|
| Production container affected | **IMMEDIATE STOP** |
| Production DB changed | **IMMEDIATE STOP** |
| Mutations enabled | **IMMEDIATE STOP** |
| Unexpected HTTP status | STOP |
| Assertion FAIL | STOP |
| Restore verification fails | STOP — do not proceed |

---

## 8. Production Invariants (must never change)

- `hermes-product-os-prod` container: untouched, healthy
- `production.db`: unchanged
- `MUTATIONS_DISABLED`: always true
- Production snapshot pipeline: active

---

## 9. B4 Reader Invariants

- `hermes-phase-b-reader` returns to healthy after each restore
- No simulation fallback
- Snapshot-only data source
- Freshness enforcement active (post FC-05)

---

## 10. Acceptance

B5 pilot is successful when all scenarios execute via the bridge with:
- Correct authority classification
- Machine-checked assertions
- Tamper-evident receipts
- Zero production changes
- Zero manual Amjad intervention for routine steps
- Every GATED operation requiring (and consuming) a valid token

---

**B5 pilot plan complete.**