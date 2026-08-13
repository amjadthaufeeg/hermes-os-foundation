# FC-05 Independent Architecture Review — Snapshot Freshness

**Reviewer:** Independent Subagent (FC-05 Analysis)
**Date:** 2026-08-12
**Scope:** FC-05 snapshot freshness candidate design from proposed branch `b5-fc05-snapshot-freshness`
**Status:** Design Review — NO branch exists yet; evaluating the proposal
**Authority:** Advisory only — no implementation authorization

---

## 0. Executive Summary

### Verdict: **BLOCK — Do Not Approve As Proposed**

The candidate design has a **fundamental architectural weakness**: `SNAPSHOT_FRESHNESS_ENFORCED` is an opt-in, fail-open configuration flag. An accidental omission, misconfiguration, or downgrade silently serves stale production data. This is structurally identical to the pre-TASK-001 `MUTATIONS_DISABLED` defect that was already remediated following the authoritative POLICY pattern. The fix is well-understood and low-risk: integrate freshness enforcement into the environment POLICY matrix using the same pattern.

Additionally, the proposal's reliance on `mtime` as the sole freshness authority introduces multiple bypass vectors (`touch`, clock skew, atomic rename timing) that metadata-based freshness (`snapshot.meta.json` → `created_at_utc`) would eliminate.

---

## 1. Architecture Context

### 1.1 Current State (P4 Production Runtime)

```
┌─────────────────────────────────────────────────────────────┐
│ HOST (root)                                                  │
│   systemd timer: hermes-snapshot-refresh.timer              │
│   OnUnitActiveSec=900 (15 min) + RandomizedDelaySec=30      │
│   │                                                          │
│   └── hermes-snapshot-refresh (bash, root)                  │
│         ├─ flock /var/lock/hermes-snapshot.lock             │
│         ├─ sqlite3 SOURCE .backup → snapshot.db.tmp         │
│         ├─ PRAGMA integrity_check                           │
│         ├─ chown root:10010, chmod 440                      │
│         ├─ mv snapshot.db.tmp → snapshot.db (atomic)        │
│         └─ Write snapshot.meta.json (sha256, created_at_utc)│
│                                                              │
│   /var/lib/hermes/snapshots/snapshot.db      (root:10010, 440)│
│   /var/lib/hermes/snapshots/snapshot.meta.json               │
└─────────────────────────────────────────────────────────────┘
                           │ :ro bind mount
┌──────────────────────────┼──────────────────────────────────┐
│ CONTAINER (UID 10010, read_only: true, cap_drop: ALL)       │
│   DATABASE_PATH=/opt/hermes/data/production.db              │
│   HERMES_ENVIRONMENT=PRODUCTION                             │
│   MUTATIONS_DISABLED=true                                   │
│   SIMULATION_MODE=false (enforced at startup)               │
│                                                              │
│   GET /api/decisions     → get_db() → SELECT * FROM decisions│
│   GET /api/decisions/{id}→ get_db() → SELECT WHERE id=?     │
│   POST /api/decisions/{id}/actions → 503 (mutations block)  │
│                                                              │
│   ⚠️ NO FRESHNESS CHECK EXISTS                              │
└─────────────────────────────────────────────────────────────┘
```

**Key observation:** In the current architecture, `DATABASE_PATH` points to `/opt/hermes/data/production.db`. For production snapshot reads, this must be the bind-mounted snapshot path. There is currently NO validation that ensures `DATABASE_PATH` actually points at a snapshot rather than a live production database.

### 1.2 Relevant Existing Protections

| Protection | Implemented | Pattern |
|---|---|---|
| `MUTATIONS_DISABLED` + POLICY enforcement | ✅ TASK-001 | Policy-authoritative, fail-closed |
| `SIMULATION_MODE=false` startup enforcement | ✅ P4 | `validate_startup()` FATAL on violation |
| Snapshot atomic publish (`mv`) | ✅ TASK-002 | No partial reads |
| Candidate integrity check | ✅ TASK-002 | `PRAGMA integrity_check` before publish |
| Snapshot `flock` concurrency | ✅ TASK-002 | Single writer |
| Container `read_only: true` | ✅ P4 | Cannot modify snapshot |
| Container `cap_drop: ALL` | ✅ P4 | Minimal attack surface |

---

## 2. Critical Question Analysis

### Q1: Is opt-in `SNAPSHOT_FRESHNESS_ENFORCED` safe? Could it be accidentally omitted/misconfigured?

**Answer: NO. This is a P0 CRITICAL defect.**

The proposed design makes freshness enforcement opt-in via an environment variable. This is structurally fail-open:

| Configuration | Behavior | Risk |
|---|---|---|
| `SNAPSHOT_FRESHNESS_ENFORCED` not set | Stale data served SILENTLY | **CRITICAL** |
| `SNAPSHOT_FRESHNESS_ENFORCED=false` | Stale data served SILENTLY | **CRITICAL** |
| `SNAPSHOT_FRESHNESS_ENFORCED=yes` | Depends on parser — truthy check may pass | **CRITICAL** |
| `SNAPSHOT_FRESHNESS_ENFORCED=` (empty) | Ambiguous — undefined behavior | **CRITICAL** |
| `SNAPSHOT_FRESHNESS_ENFORCED=true` | Correct behavior | OK |

This is **exactly the same class of defect** as the pre-TASK-001 `MUTATIONS_DISABLED=false` issue, which allowed mutations in production when misconfigured. TASK-001 fixed this by making environment POLICY authoritative — the fix for FC-05 should follow the identical pattern.

**Fix:** Environment POLICY must be authoritative. In PRODUCTION, freshness enforcement must be non-negotiable regardless of any env var value. The env var becomes irrelevant for PRODUCTION — the policy overrides it.

### Q2: Should production environment POLICY validate this setting (like MUTATIONS_DISABLED)?

**Answer: YES. P0 CRITICAL.**

This is the single most important architectural decision for FC-05. Following the TASK-001 pattern:

```python
# In environment.py: POLICY matrix
Environment.PRODUCTION: {
    "snapshot_freshness_required": True,   # NEW — non-negotiable
    ...
}

# In validate_startup():
if env == Environment.PRODUCTION and policy("snapshot_freshness_required"):
    # Freshness is always enforced — env var is informational only
    # Validate freshness infrastructure is available
    if not os.path.exists(DATABASE_PATH + ".meta.json"):
        errors.append("FATAL: PRODUCTION requires snapshot metadata at %s" % ...)
```

The critical advantage of POLICY enforcement: even if `SNAPSHOT_FRESHNESS_ENFORCED=false` is set (deliberately or accidentally), PRODUCTION ignores it. The policy is authoritative. This eliminates the entire class of configuration bypass vectors.

Additionally, `validate_startup()` should verify the freshness infrastructure is operational:
- Snapshot file exists and is readable
- Metadata file exists and is parseable
- SHA-256 in metadata matches snapshot file

### Q3: Is mtime the correct authoritative timestamp? What about atomic rename operations changing mtime?

**Answer: NO. P1 BLOCKER. Use snapshot metadata instead.**

#### mtime weaknesses:

1. **Atomic rename resets mtime.** When the snapshot service does `mv snapshot.db.tmp → snapshot.db`, mtime reflects the rename time, not the backup creation time. While the rename time IS the publication time, this conflates two distinct events.

2. **`touch` bypass.** `touch snapshot.db` resets mtime to now, making any stale snapshot appear fresh. An attacker with filesystem access (root compromise of host) can trivially forge freshness.

3. **Filesystem restore.** If a backup tool restores `snapshot.db` from tape/archive, mtime may be set to the restore time or preserved from the archive — neither reflects true freshness.

4. **Clock changes.** NTP corrections, manual clock changes, or VM suspend/resume can shift mtime relative to real elapsed time.

5. **No cryptographic binding.** mtime has no relationship to the snapshot content. A corrupt snapshot with a fresh mtime passes a naive check.

#### Metadata strengths:

The existing snapshot pipeline ALREADY writes `snapshot.meta.json` with authoritative metadata:

```json
{
  "result": "published",
  "created_at_utc": "2026-08-12T14:30:00Z",
  "source_id": "/var/lib/hermes/source-test.db",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "duration_s": 2,
  "validation": {
    "integrity_check": "ok",
    "decisions_count": 31
  }
}
```

**Recommendation:**
- `created_at_utc` is the authoritative freshness timestamp
- `sha256` enables cryptographic verification of snapshot identity
- If metadata is missing → fail closed (no freshness can be asserted)
- If metadata is corrupted/unparseable → fail closed
- If SHA in metadata ≠ SHA of opened file → fail closed (detect replacement/TOCTOU)

### Q4: TOCTOU risks: stat then open — snapshot could be replaced between check and read

**Answer: Real but mitigated by architecture. P2 HARDENING recommended.**

#### Attack scenario:

```
T1: Freshness check: stat(snapshot.db) → mtime = now, metadata = fresh
T2: [Attacker replaces snapshot.db with stale copy]
T3: get_db() → sqlite3.connect(snapshot.db) → reads stale data
```

#### Current mitigations:

| Mitigation | Effectiveness |
|---|---|
| Container `read_only: true` | Container cannot write to snapshot — TOCTOU from inside container is impossible |
| Snapshot dir `root:10010, 440` | Container user (10010) cannot write |
| No container writable volume to snapshot dir | No path for container process to modify snapshot |
| Atomic `mv` by snapshot service | No window where snapshot.db is partially written |

**Risk assessment: LOW** in the current architecture because the container process has no write access to the snapshot directory. TOCTOU becomes relevant only if:
1. The host root is compromised (snapshot service runs as root)
2. A race exists between the snapshot service's `mv` and the container's read

#### Recommended hardening (P2):

```python
def is_snapshot_fresh(meta_path: str, db_path: str, max_age_s: int) -> tuple[bool, str]:
    """Verify snapshot freshness with SHA-256 post-read binding."""
    # 1. Read metadata
    meta = read_metadata(meta_path)
    
    # 2. Check age
    age = now_utc() - parse_iso(meta["created_at_utc"])
    if age > max_age_s:
        return False, f"stale: {age}s > {max_age_s}s"
    
    # 3. Open snapshot and compute SHA
    actual_sha = sha256_file(db_path)
    
    # 4. Verify SHA matches metadata (detects replacement)
    if not hmac.compare_digest(actual_sha, meta["sha256"]):
        return False, "tampered: SHA mismatch"
    
    return True, "fresh"
```

**Key insight:** The SHA verification in step 3-4 closes the TOCTOU window because the SHA is computed from the ACTUAL opened file, not a pre-read stat. If the file was replaced after the metadata read, the SHA will not match.

### Q5: Does the check apply to BOTH `/api/decisions` and `/api/decisions/{id}`?

**Answer: MUST apply to both. P1 BLOCKER.**

The read path inventory confirms two decision read paths:

| Endpoint | Reads decisions? | Current freshness |
|---|---|---|
| `GET /api/decisions` | YES — `SELECT * FROM decisions` | **NONE** |
| `GET /api/decisions/{id}` | YES — `SELECT * FROM decisions WHERE id=?` | **NONE** |

A freshness check on only one endpoint would leave the other as a bypass. Any endpoint reading from the production database (the snapshot) must enforce freshness.

**Architecture recommendation:** Centralize freshness in a helper, called from BOTH endpoints before the DB read:

```python
def require_fresh_snapshot():
    """Fail-closed freshness gate. Raises HTTPException if stale."""
    if not is_snapshot_fresh():
        raise HTTPException(503, "Snapshot data unavailable — stale or missing")

@app.get("/api/decisions")
def list_decisions():
    if not is_simulation_mode():
        require_fresh_snapshot()  # <-- CENTRALIZED
        with get_db() as db:
            ...

@app.get("/api/decisions/{decision_id}")
def get_decision(decision_id: str):
    if not is_simulation_mode():
        require_fresh_snapshot()  # <-- CENTRALIZED
        with get_db() as db:
            ...
```

### Q6: Are there other endpoints that read decision data without freshness checks?

**Answer: Two additional paths exist with lower but non-zero risk. P3 FUTURE.**

| Endpoint | Risk | Assessment |
|---|---|---|
| `GET /api/audit/export` | **Medium** | Reads decisions indirectly via export — may include decision data. Currently session-authenticated. |
| `GET /api/health` | **Low** | Does not read decisions, but SHOULD expose snapshot freshness state for operational monitoring. |
| `GET /api/health/readiness` | **Low** | Should validate snapshot freshness infrastructure. |
| `GET /api/metrics` | **None** | Prometheus metrics — no decision data. |
| `GET /api/audit/events` | **None** | Reads `audit_events` table, not `decisions`. |
| `GET /api/audit/verify` | **None** | Hash chain verification — no decision reads. |

**For Phase B:** Fixing the two primary decision endpoints is sufficient. Audit export is an operational endpoint with session authentication. Future phases should audit all read paths.

### Q7: Is 900s (15 min) the right threshold matching the snapshot timer's OnUnitActiveSec?

**Answer: No. P1 BLOCKER. The threshold must account for timer randomization.**

The timer configuration:

```
[Timer]
OnUnitActiveSec=900        # 15 minutes between activations
RandomizedDelaySec=30      # +0–30s random jitter
```

**Actual maximum interval between snapshots:** 900 + 30 = 930 seconds.

A 900s threshold means a snapshot can be flagged as "stale" when it's actually within the normal refresh window. This creates false positives from timer jitter alone.

**Recommendation:** Threshold = `OnUnitActiveSec + RandomizedDelaySec + buffer`:

```
threshold = 900 + 30 + 60 = 990s (16.5 minutes)
```

Rationale:
- 900s (OnUnitActiveSec): base timer interval
- 30s (RandomizedDelaySec): worst-case jitter
- 60s (buffer): snapshot creation time + NTP slewing + general margin

A missed cycle would produce a snapshot age of ~1800s (2 × 900), well above the 990s threshold, ensuring genuine staleness is detected.

---

## 3. Bypass Vector Analysis — Complete Classification

### 3.1 Configuration Bypass Vectors

| # | Vector | Class | Mechanism | Mitigation |
|---|---|---|---|---|
| V1 | `SNAPSHOT_FRESHNESS_ENFORCED` not set | **P0 CRITICAL** | Omission — env var absent → fail open → stale data served silently | Environment POLICY makes freshness non-negotiable in PRODUCTION |
| V2 | `SNAPSHOT_FRESHNESS_ENFORCED=false` | **P0 CRITICAL** | Explicit disable — operator sets false, thinking it's safe | POLICY overrides — PRODUCTION ignores this env var |
| V3 | `SNAPSHOT_FRESHNESS_ENFORCED` malformed | **P0 CRITICAL** | `yes`, `1`, `enabled`, empty string — parser-dependent behavior | `validate_startup()` rejects malformed values as FATAL |
| V4 | `DATABASE_PATH` changed to non-snapshot path | **P1 BLOCKER** | Operator points DATABASE_PATH at live production DB or arbitrary file | `validate_startup()` verifies path is within approved snapshot directory |
| V5 | `DATABASE_PATH` changed to `/dev/null` or `/dev/zero` | **P1 BLOCKER** | Path validation bypass — "file exists" check passes for device nodes | Verify path is a regular file, within snapshot directory, with valid SQLite header |
| V6 | `DATABASE_PATH` points at snapshot DIR not file | **P1 BLOCKER** | Path confusion — directory exists, SQLite fails silently or returns empty | Validate path is a regular file |

### 3.2 Filesystem Attack Vectors

| # | Vector | Class | Mechanism | Mitigation |
|---|---|---|---|---|
| V7 | Symlink attack — snapshot.db → live production DB | **P1 BLOCKER** | Attacker replaces snapshot.db with symlink to /var/lib/hermes/production.db | `realpath()` resolution; container read-only prevents symlink creation from inside |
| V8 | Symlink attack — snapshot.db → /dev/zero | **P1 BLOCKER** | Return empty results, no error | `realpath()` + regular file check |
| V9 | Snapshot replaced after stat() (TOCTOU) | **P2 HARDENING** | stat fresh → attacker replaces → read stale | SHA-256 post-read verification (see Q4) |
| V10 | mtime manually changed (`touch snapshot.db`) | **P1 BLOCKER** | Forge fresh timestamp on stale snapshot | Use metadata `created_at_utc` — not forgeable without also forging SHA |
| V11 | Atomic rename preserving old timestamp | **P2 HARDENING** | `cp -p` preserves mtime from old file | Metadata-based freshness unaffected by mtime |
| V12 | Snapshot path pointing at live production DB | **P1 BLOCKER** | Container reads live DB directly — defeats snapshot isolation | `validate_startup()` path validation; container capability restrictions |

### 3.3 Temporal / Clock Vectors

| # | Vector | Class | Mechanism | Mitigation |
|---|---|---|---|---|
| V13 | Host vs container clock skew | **P2 HARDENING** | Container clock drifts from host → freshness threshold wrong | Use monotonic timer relative to metadata timestamp; both host and container should use UTC |
| V14 | NTP step correction | **P2 HARDENING** | NTP jumps clock backward → snapshot appears fresher than it is | Monotonic clock for relative age calculations |
| V15 | VM suspend/resume | **P2 HARDENING** | VM paused for hours → wall clock shows brief gap → snapshot appears stale when it shouldn't | Same as clock skew — monotonic timer |
| V16 | `created_at_utc` in metadata is future-dated | **P1 BLOCKER** | Metadata forged with future timestamp → snapshot appears permanently fresh | Reject `created_at_utc` > now + 60s as invalid |

### 3.4 SQLite / Data Integrity Vectors

| # | Vector | Class | Mechanism | Mitigation |
|---|---|---|---|---|
| V17 | WAL/SHM interaction with snapshot reads | **P3 FUTURE** | Snapshot created from WAL-mode source may have pending WAL entries | `.backup` command handles WAL correctly; `mode=ro` on snapshot prevents writes; `immutable=1` prevents WAL creation |
| V18 | Corrupt SQLite with fresh forged mtime | **P1 BLOCKER** | Replace snapshot with corrupt file, `touch` mtime to now | `PRAGMA integrity_check` fails → corrupt rejection; SHA-256 in metadata detects replacement |
| V19 | Stale valid SQLite with fresh forged mtime | **P1 BLOCKER** | Old valid snapshot, `touch` mtime to now | Metadata `created_at_utc` reveals true age |
| V20 | Empty SQLite database (valid but zero rows) | **P2 HARDENING** | Attacker replaces snapshot with empty-but-valid SQLite → "no decisions" | Metadata `decisions_count` comparison; alert on count drop |
| V21 | SQLite database with forged schema (no decisions table) | **P1 BLOCKER** | Attacker creates valid SQLite without expected schema | Schema validation in freshness check: verify `decisions` table exists |

### 3.5 Operational / Runtime Vectors

| # | Vector | Class | Mechanism | Mitigation |
|---|---|---|---|---|
| V22 | Restart clearing cached state | **P2 HARDENING** | Process restart → freshness state lost → must re-check | Freshness is always checked on-demand (stateless), so restart is safe. Verify no caching. |
| V23 | Snapshot refresh service stopped/crashed | **P1 BLOCKER** | systemd timer disabled → snapshot never updates → grows stale | Freshness check detects staleness; health endpoint exposes age; alert on timer inactive |
| V24 | Snapshot refresh service stuck (lock held, hung process) | **P1 BLOCKER** | `flock` held by hung process → no new snapshots → stale | systemd `TimeoutSec=120` kills hung process → lock released → next cycle runs |
| V25 | Disk full — snapshot cannot be written | **P2 HARDENING** | Snapshot refresh fails silently, old snapshot persists → eventually stale | Freshness check detects age; disk space alerting; health endpoint |

### 3.6 Summary Classification

| Priority | Count | Vectors |
|---|---|---|
| **P0 CRITICAL** | 3 | V1 (not set), V2 (set to false), V3 (malformed) — fail-open configuration |
| **P1 BLOCKER** | 12 | V4-V8 (path attacks), V10 (mtime forge), V12 (live DB), V16 (future timestamp), V18-V19 (forged metadata), V21 (schema forge), V23-V24 (service stopped/stuck) |
| **P2 HARDENING** | 7 | V9 (TOCTOU), V11 (rename preserves mtime), V13-V15 (clock), V20 (empty DB), V22 (restart) |
| **P3 FUTURE** | 1 | V17 (WAL/SHM) |

---

## 4. Architecture-Level Recommendations

### R1: Environment POLICY Integration (P0 — Blocks Approval)

Follow the TASK-001 `MUTATIONS_DISABLED` pattern exactly:

```python
# environment.py — POLICY matrix addition
Environment.PRODUCTION: {
    ...
    "snapshot_freshness_required": True,    # NEW — authoritative, non-negotiable
    "snapshot_max_age_seconds": 990,        # NEW — OnUnitActiveSec + jitter + buffer
    "snapshot_path_prefix": "/opt/hermes/data",  # NEW — validate DATABASE_PATH
    ...
}

# validate_startup() additions:
def validate_startup():
    errors = []
    ...
    
    # FC-05: Snapshot freshness enforcement required in PRODUCTION
    if policy("snapshot_freshness_required"):
        db_path = os.environ.get("DATABASE_PATH", "")
        prefix = POLICY[env].get("snapshot_path_prefix", "")
        
        # Validate DATABASE_PATH is under approved directory
        if not os.path.realpath(db_path).startswith(prefix):
            errors.append("FATAL: DATABASE_PATH must be within %s" % prefix)
        
        # Validate snapshot metadata exists
        meta_path = db_path + ".meta.json"
        if not os.path.isfile(meta_path):
            errors.append("FATAL: Snapshot metadata missing at %s" % meta_path)
    
    return errors
```

### R2: Metadata-Based Freshness Authority (P1 — Blocks Approval)

```python
def snapshot_freshness(db_path: str = None, max_age_s: int = None) -> tuple[bool, dict]:
    """Check snapshot freshness using authoritative metadata.
    
    Returns (is_fresh, diagnostics).
    Fail-closed: any error returns (False, error_info).
    """
    if db_path is None:
        db_path = os.environ.get("DATABASE_PATH", "")
    if max_age_s is None:
        max_age_s = POLICY.get(get_env(), {}).get("snapshot_max_age_seconds", 990)
    
    meta_path = db_path + ".meta.json"
    
    # --- Metadata must exist ---
    if not os.path.isfile(meta_path):
        return False, {"error": "metadata_missing", "path": meta_path}
    
    # --- Metadata must be parseable ---
    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return False, {"error": "metadata_unreadable", "detail": str(e)}
    
    # --- Metadata must have required fields ---
    if "created_at_utc" not in meta:
        return False, {"error": "metadata_incomplete", "missing": "created_at_utc"}
    if "sha256" not in meta:
        return False, {"error": "metadata_incomplete", "missing": "sha256"}
    
    # --- Validate age ---
    try:
        created = datetime.fromisoformat(meta["created_at_utc"].replace("Z", "+00:00"))
    except ValueError:
        return False, {"error": "metadata_bad_timestamp", "value": meta["created_at_utc"]}
    
    now = datetime.now(timezone.utc)
    age_s = (now - created).total_seconds()
    
    # Reject future timestamps
    if age_s < -60:
        return False, {"error": "future_timestamp", "age_s": age_s}
    
    # Age check
    if age_s > max_age_s:
        return False, {"error": "stale", "age_s": age_s, "max_age_s": max_age_s}
    
    # --- SHA-256 verification (TOCTOU closure) ---
    import hashlib
    sha = hashlib.sha256()
    try:
        with open(db_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
    except IOError as e:
        return False, {"error": "snapshot_unreadable", "detail": str(e)}
    
    actual_sha = sha.hexdigest()
    if not secrets.compare_digest(actual_sha, meta["sha256"]):
        return False, {"error": "sha_mismatch", 
                       "expected": meta["sha256"][:16] + "...",
                       "actual": actual_sha[:16] + "..."}
    
    return True, {
        "age_s": age_s,
        "max_age_s": max_age_s,
        "decisions_count": meta.get("validation", {}).get("decisions_count", "unknown"),
        "created_at_utc": meta["created_at_utc"],
    }
```

### R3: Health Endpoint Freshness Exposure (P2)

```python
@app.get("/api/health")
def health():
    fresh, diag = snapshot_freshness() if not is_simulation_mode() else (True, {})
    return {
        "status": "alive",
        "environment": get_env().value,
        "mutations": "DISABLED" if mutations_disabled() else "SIMULATION_ONLY",
        "snapshot": {
            "fresh": fresh,
            "age_seconds": diag.get("age_s"),
            "max_age_seconds": diag.get("max_age_s"),
        } if not is_simulation_mode() else None,
    }
```

### R4: Threshold Accounting for Timer Jitter (P1)

```python
# In POLICY:
snapshot_max_age_seconds = 990  # 900 (OnUnitActiveSec) + 30 (RandomizedDelaySec) + 60 (buffer)

# Document the derivation:
# - 900s: minimum interval between snapshot cycles
# -  30s: worst-case RandomizedDelaySec jitter
# -  60s: snapshot script execution time + NTP fudge + margin
# - 990s: total threshold — any snapshot older than this missed at least one cycle
#
# A legitimately stale snapshot (missed cycle) would be ~1800s old, well above threshold.
```

### R5: Readness Endpoint Freshness Validation (P2)

```python
@app.get("/api/health/readiness")
def readiness():
    errors = validate_startup()
    
    # Add snapshot freshness check for production
    if not is_simulation_mode() and policy("snapshot_freshness_required"):
        fresh, diag = snapshot_freshness()
        if not fresh:
            errors.append("Snapshot not fresh: %s" % diag.get("error", "unknown"))
    
    if errors:
        return {"ready": False, "errors": errors}
    return {"ready": True, "environment": get_env().value, "mutations_disabled": mutations_disabled()}
```

---

## 5. Implementation Guidance

### 5.1 Centralized Freshness Gate (preferred pattern)

Rather than embedding freshness checks in each endpoint, create a FastAPI dependency:

```python
from fastapi import Depends

def require_snapshot_freshness():
    """Dependency: ensures snapshot is fresh before serving data.
    Only enforced when not in simulation mode and policy requires it.
    """
    if is_simulation_mode():
        return  # Simulation uses hardcoded data — no freshness needed
    
    if not policy("snapshot_freshness_required"):
        return  # Environment doesn't require freshness (e.g., LOCAL_TEST)
    
    fresh, diag = snapshot_freshness()
    if not fresh:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "snapshot_not_fresh",
                "detail": diag.get("error", "unknown"),
                "age_seconds": diag.get("age_s"),
            }
        )

# Usage:
@app.get("/api/decisions")
def list_decisions(freshness=Depends(require_snapshot_freshness)):
    ...
```

### 5.2 Files to Modify

| File | Change |
|---|---|
| `backend/hos4c/environment.py` | Add `snapshot_freshness_required`, `snapshot_max_age_seconds`, `snapshot_path_prefix` to POLICY; add validation in `validate_startup()` |
| `backend/hos4c/main.py` | Add `require_snapshot_freshness` dependency; apply to `list_decisions()` and `get_decision()`; update health/readiness endpoints |
| `backend/hos4c/config.py` | No changes — freshness is policy-driven, no new env vars needed |
| `deploy/docker-compose.prod.yml` | No mandatory changes — POLICY handles enforcement |
| `test_production_runtime.py` | Add tests: freshness enforced, stale rejection, SHA mismatch, metadata missing |

### 5.3 Test Plan

| Test | Expected |
|---|---|
| `PRODUCTION` starts with fresh snapshot | 200 OK, decisions returned |
| `PRODUCTION` starts with stale snapshot (>990s) | 503, "snapshot_not_fresh" |
| `PRODUCTION` starts with missing metadata | 503, "metadata_missing" |
| `PRODUCTION` starts with SHA mismatch | 503, "sha_mismatch" |
| `PRODUCTION` starts with `DATABASE_PATH` outside approved prefix | RuntimeError at startup |
| `PRODUCTION` with future-dated `created_at_utc` | 503, "future_timestamp" |
| `LOCAL_SIMULATION` ignores freshness entirely | 200 OK, SIMULATION mode |
| `STAGING` with stale snapshot | 503 (staging also should enforce) |
| Health endpoint reports snapshot state | `snapshot.fresh: true/false` |
| Health endpoint does NOT go unhealthy for stale snapshot | Health stays "alive" — consumers decide |
| `/api/decisions` and `/api/decisions/{id}` both enforce | Both return 503 on stale |
| Threshold accounts for timer jitter | 990s threshold, not 900s |

---

## 6. Final Verdict

### BLOCK — Do NOT approve as proposed. 3 fixes required before approval.

| # | Issue | Priority | Fix |
|---|---|---|---|
| 1 | Fail-open configuration (`SNAPSHOT_FRESHNESS_ENFORCED` opt-in) | **P0 CRITICAL** | Environment POLICY integration (TASK-001 pattern) |
| 2 | mtime as sole freshness authority | **P1 BLOCKER** | Use `snapshot.meta.json` → `created_at_utc` + SHA-256 |
| 3 | Threshold mismatch with timer randomization | **P1 BLOCKER** | Set threshold to 990s (900 + 30 + 60) |

| # | Issue | Priority | Recommendation |
|---|---|---|---|
| 4 | No centralized freshness gate | **P1 BLOCKER** | FastAPI dependency applied to all decision read paths |
| 5 | No `DATABASE_PATH` validation | **P1 BLOCKER** | `validate_startup()` rejects paths outside approved prefix |
| 6 | No TOCTOU post-read verification | **P2 HARDENING** | SHA-256 compare after file read |
| 7 | Health endpoint doesn't expose freshness | **P2 HARDENING** | Add `snapshot.fresh` and `age_seconds` to `/api/health` |
| 8 | Error codes too generic (500 vs 503) | **P2 HARDENING** | Use 503 for infrastructure unavailability |

### Approval Gate

Approval requires:
1. ✅ Environment POLICY integration committed and tested
2. ✅ Metadata-based freshness authority replacing mtime
3. ✅ Threshold set to 990s with documented derivation
4. ✅ Both decision endpoints protected with centralized freshness gate
5. ✅ `validate_startup()` path validation for `DATABASE_PATH`
6. ⬜ 6+ tests proving each bypass vector is closed

### Risk if Approved As-Is

- **P0 (Critical):** Accidental omission of `SNAPSHOT_FRESHNESS_ENFORCED=true` silently serves stale data in production. This is NOT a hypothetical — the identical `MUTATIONS_DISABLED` pattern was already fixed for being fail-open.
- **P1 (Blocker):** `touch` on a stale snapshot file defeats mtime-based freshness entirely.
- **P1 (Blocker):** Timer jitter causes false staleness alerts at the 900s boundary during normal operation.

---

**Review complete. Zero implementation changes made. File: FC-05-ARCHITECTURE-REVIEW.md**