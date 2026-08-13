# B5 Overnight Independent Review — FC-05 Snapshot Freshness

**Mode:** ANALYSIS / REVIEW ONLY  
**Authority:** ZERO — no implementation authorization  
**Date:** 2026-08-12

---

## 1. Architecture Verdict

**Verdict: BLOCK — requires 3 critical fixes before approval.**

The candidate `SNAPSHOT_FRESHNESS_ENFORCED=true` design has a fundamental architectural weakness: **opt-in enforcement is fail-open by default**. An accidental omission or misconfiguration silently serves stale data. This contradicts the Phase B fail-closed principle.

---

## 2. SNAPSHOT_FRESHNESS_ENFORCED Analysis

### Critical Finding: Fail-Open Configuration Risk

If `SNAPSHOT_FRESHNESS_ENFORCED` is:
- **Not set** → Stale data served silently
- **Set to false** → Stale data served silently  
- **Set to malformed** → Depends on implementation; if truthy-check, malformed could pass
- **Set to true** → Correct behavior

**This is the same class of defect as pre-TASK-001 MUTATIONS_DISABLED=false.** The fix should follow the same pattern: **environment POLICY must be authoritative**.

### Recommended Fix: Environment Policy Integration

```python
# PRODUCTION policy should require freshness enforcement:
POLICY[Environment.PRODUCTION] = {
    ...
    "snapshot_freshness_required": True,  # NEW
    ...
}

# In validate_startup():
if env == Environment.PRODUCTION and policy("snapshot_freshness_required"):
    if os.environ.get("SNAPSHOT_FRESHNESS_ENFORCED", "").strip().lower() != "true":
        errors.append("FATAL: PRODUCTION requires SNAPSHOT_FRESHNESS_ENFORCED=true")
```

This makes freshness enforcement non-negotiable in PRODUCTION, matching the MUTATIONS_DISABLED pattern. **P0 CRITICAL.**

---

## 3. mtime as Authoritative Timestamp — Analysis

### Strengths
- Simple, no database schema changes needed
- Works with read-only mounts (no WAL dependency)
- Can be checked before opening the SQLite file

### Weaknesses
1. **Atomic rename resets mtime.** When the snapshot service does `mv snapshot.db.tmp → snapshot.db`, mtime reflects the rename time, not the snapshot creation time. **This is acceptable** — the rename time IS the publication time, and that's when the snapshot became available.

2. **Metadata file has authoritative timestamp.** The snapshot service writes `snapshot.meta.json` with `created_at_utc`. This is the true snapshot creation time. **mtime and metadata timestamp can diverge.**

### Recommendation

Use `snapshot.meta.json` as the **authoritative freshness source**, not mtime. The metadata file is written atomically alongside the snapshot and contains:
- `created_at_utc`: snapshot creation timestamp
- `sha256`: snapshot integrity hash
- `duration_s`: creation duration

**Read `created_at_utc` from metadata, compare against current time.** This is more authoritative than mtime.

If metadata is missing → fail closed.  
If metadata is corrupted → fail closed.  
If metadata SHA doesn't match snapshot SHA → fail closed.

**P1 BLOCKER:** mtime should not be the sole freshness authority.

---

## 4. TOCTOU Analysis

### Attack: Replace Snapshot Between stat() and open()

```
T1: stat(snapshot.db) → fresh (mtime = now)
T2: Attacker replaces snapshot.db with stale copy
T3: open(snapshot.db) → reads stale data
```

**Currently:**
- Snapshot directory is `root:10010, 440` — only root can replace the snapshot
- The snapshot service runs as root and uses atomic `mv`
- Container reads via `:ro` bind mount — cannot replace file

**Risk: LOW** in current architecture because the container has no write access to the snapshot directory. However, if the snapshot service is compromised or a race condition exists in the refresh pipeline, TOCTOU is possible.

**P2 HARDENING:** Verify `sha256` from metadata against the opened file after the read to detect replacement.

---

## 5. Endpoint Coverage

### Current Implementation

| Endpoint | Reads Decisions? | Freshness Check? |
|---|---|---|
| `/api/decisions` | YES (DB or SIM_DECISIONS) | NO |
| `/api/decisions/{id}` | YES | NO |
| `/api/health` | NO (reads environment + mutations) | N/A |
| `/api/health/readiness` | NO (validates startup) | N/A |
| `/api/audit/events` | NO (reads audit_events table) | N/A |

### Finding

**Both decision endpoints must have freshness enforcement.** A freshness check on `/api/decisions` alone is insufficient — `/api/decisions/{id}` is a separate read path that must also be protected.

**P1 BLOCKER:** Freshness check must be centralized and applied to ALL decision read paths.

---

## 6. Health Semantics

The health endpoint should expose snapshot freshness state:

```json
{
  "status": "alive",
  "environment": "PRODUCTION",
  "mutations": "DISABLED",
  "snapshot": {
    "fresh": true,
    "age_seconds": 120,
    "max_age_seconds": 900
  }
}
```

When stale:
```json
{
  "snapshot": {
    "fresh": false,
    "age_seconds": 950,
    "max_age_seconds": 900
  }
}
```

Health should NOT go unhealthy for stale snapshot — the container is operational but data may be stale. Consumers decide.

**P2 HARDENING:** Add snapshot freshness to health endpoint.

---

## 7. Threshold Alignment

| Component | Interval | Threshold |
|---|---|---|
| Snapshot timer | 900s (15 min) + 30s randomized delay | — |
| Proposed freshness check | 900s | — |
| Gap | 0-30s randomization means snapshot can be up to 930s old | Check: 900s may be too tight |

**Recommendation:** Set threshold to `OnUnitActiveSec + RandomizedDelaySec + buffer = 900 + 30 + 60 = 990s (~16.5 min)`. This prevents false positives from timer jitter while still detecting genuine staleness (a missed cycle = 2 × 900 = 1800s).

**P1 BLOCKER:** Threshold must account for timer randomization delay.

---

## 8. Bypass Vector Classification

| Vector | Classification | Mitigation |
|---|---|---|
| SNAPSHOT_FRESHNESS_ENFORCED not set | **P0 CRITICAL** | Environment POLICY enforcement |
| Set to false | **P0 CRITICAL** | Environment POLICY enforcement |
| Malformed value | **P0 CRITICAL** | Strict validation in validate_startup() |
| DATABASE_PATH changed to non-snapshot path | **P1 BLOCKER** | Environment POLICY requires snapshot path |
| Symlink attack | **P1 BLOCKER** | realpath() resolution, no-follow mount |
| Snapshot replaced after stat() | **P2 HARDENING** | SHA-256 verification post-read |
| mtime manually changed (touch) | **P1 BLOCKER** | Use metadata timestamp, not mtime |
| Host vs container clock skew | **P2 HARDENING** | Use monotonic timers, not wall clock |
| WAL/SHM interaction | **P3 FUTURE** | `mode=ro&immutable=1` prevents writes |
| Atomic rename preserving old timestamp | **P2 HARDENING** | Metadata-based freshness |
| Corrupt SQLite with fresh forged mtime | **P1 BLOCKER** | Integrity check + metadata SHA |
| Stale valid SQLite with fresh forged mtime | **P1 BLOCKER** | Metadata timestamp as authority |
| Snapshot path points at live production DB | **P1 BLOCKER** | Path validation in policy |
| Restart clearing cached state | **P2 HARDENING** | Freshness always re-checked on demand |

---

## 9. FC-05 Verdict

**NOT APPROVED.** The candidate design has:
- **3 P0 CRITICAL** issues (fail-open configuration, no policy enforcement)
- **6 P1 BLOCKER** issues (mtime reliance, threshold mismatch, endpoint coverage, path validation, metadata authority)
- **5 P2 HARDENING** recommendations (TOCTOU, clock skew, health exposure, atomic rename)

**Required before approval:**
1. Environment POLICY integration (like TASK-001)
2. Metadata-based freshness authority (not mtime)
3. Threshold accounting for timer randomization
4. Coverage of all decision read paths
5. Health endpoint freshness exposure

---

## 10. Generic HTTP 500 → 503 Consideration

FC-03 (missing snapshot) and FC-04 (corrupt snapshot) currently return HTTP 500. This is technically correct (fail-closed) but imprecise. A 503 (Service Unavailable) with explicit reason is preferred:

```json
{"error": "Snapshot unavailable — cannot serve production data"}
```

vs opaque 500. The 500 does not weaken fail-closed behavior but doesn't distinguish infrastructure failure from application bugs. **P2 HARDENING** — improve error specificity.

---

**Review complete. Zero implementation changes made. Zero VPS changes.**