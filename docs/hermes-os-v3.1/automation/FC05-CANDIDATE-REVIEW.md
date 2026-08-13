# FC-05 Candidate Review — Snapshot Freshness Implementation

**Review of uncommitted candidate on `b5-fc05-snapshot-freshness`.**  
**Review only. No modification to candidate.**

---

## Verdict: APPROVE_WITH_CHANGES

The core logic is correct and fail-closed **when enabled**. But three issues must be resolved before the candidate is committed and deployed.

---

## What the Candidate Does

| File | Change |
|---|---|
| `snapshot_freshness.py` (new) | `freshness_enforced()`, `snapshot_freshness()`, `snapshot_read_allowed()` |
| `main.py` | Health endpoint exposes snapshot state; both `/api/decisions` and `/api/decisions/{id}` gate on freshness |
| `test_snapshot_freshness_gate.py` (new) | 5 tests (fresh/stale/missing/future/opt-in) |

**Correct elements:**
- Missing snapshot → `UNAVAILABLE`, fail closed ✅
- Future timestamp (age < -5s) → `INVALID`, fail closed ✅
- Stale (> 900s) → `STALE`, fail closed ✅
- Both decision endpoints covered ✅
- Health endpoint exposes snapshot state ✅
- 28 focused tests all PASS ✅

---

## Required Changes

### CHANGE 1 — P0: Opt-in is fail-open in production

`freshness_enforced()` defaults to `"false"`. If `SNAPSHOT_FRESHNESS_ENFORCED` is omitted from the Phase-B reader environment, stale data is silently served.

**Fix:** Follow the TASK-001 pattern — environment POLICY must require it.

```python
# environment.py POLICY, for the Phase-B reader's environment:
"snapshot_freshness_required": True,

# validate_startup():
if policy("snapshot_freshness_required"):
    if os.environ.get("SNAPSHOT_FRESHNESS_ENFORCED", "").strip().lower() != "true":
        errors.append("FATAL: Phase-B reader requires SNAPSHOT_FRESHNESS_ENFORCED=true")
```

### CHANGE 2 — P1: Threshold ignores timer randomization

`MAX_SNAPSHOT_AGE_SECONDS = 900`, but the snapshot timer is `OnUnitActiveSec=900` + `RandomizedDelaySec=30` = up to 930s between refreshes. A legitimately fresh snapshot can be up to 930s old.

**Fix:** `MAX_SNAPSHOT_AGE_SECONDS = 990` (900 + 30 + 60 buffer), or compute from timer config.

### CHANGE 3 — P1: mtime is sole freshness authority

`os.stat().st_mtime` is trivially forged with `touch`. The snapshot pipeline already writes `snapshot.meta.json` with `created_at_utc` and `sha256`.

**Fix:** Read `created_at_utc` from `snapshot.meta.json` as the authoritative freshness source. Fall back to mtime only if metadata is absent (and document the residual risk).

### CHANGE 4 — P2: Mutations label regression

The candidate changes health payload from:
- `"mutations": "DISABLED" if mutations_disabled() else "SIMULATION_ONLY"`

to:
- `"mutations": "DISABLED" if mutations_disabled() else "ENABLED"`

The new `"ENABLED"` label is misleading — in production, `mutations_disabled()` returns `False` only when policy permits mutations AND the flag is `false`. In practice this never happens in PRODUCTION (policy prohibits). The `"SIMULATION_ONLY"` label was more accurate. Revert or rename to `"AVAILABLE_IN_SIMULATION"`.

---

## Bypass Analysis

| Bypass | Status |
|---|---|
| `SNAPSHOT_FRESHNESS_ENFORCED` omitted | **FAIL-OPEN** (P0) |
| `SNAPSHOT_FRESHNESS_ENFORCED=false` | **FAIL-OPEN** (P0) |
| Malformed value | Treated as "false" → fail-open (P0) |
| mtime forged via `touch` | **FAIL** (P1 — no metadata check) |
| Future timestamp | Correctly INVALID ✅ |
| DATABASE_PATH changed | Not validated (P1) |
| Symlink | Not resolved (P1) |
| Snapshot replaced after stat | TOCTOU (P2) |
| Atomic rename old timestamp | mtime reflects rename (acceptable) |

---

## Summary

**Correct core, fail-closed when enabled, but opt-in creates production fail-open risk.**

Before commit:
1. Add POLICY enforcement (P0)
2. Fix threshold to 990s (P1)
3. Use metadata timestamp (P1)
4. Revert mutations label (P2)

**28 focused tests already pass; add tests for the P0/P1 fixes.**

---

**FC-05 candidate review complete. Zero modifications made to candidate.**