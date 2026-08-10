# Phase B — Engineering Backlog

**Status:** PRE-ACTIVATION. Production = 0. Hermes authority = 0.

---

## A. 7 Production Blockers

### B1 — Policy Cross-Validation Gap (GAP-001)

| Field | Value |
|---|---|
| BlockeID | PHASE-B-BLK-001 |
| Priority | **P0** — blocks all Phase B activation |
| Why it blocks | `MUTATIONS_DISABLED=false` enables authoritative mutations in LOCAL_TEST. No independent check validates this against the Environment policy dict. Phase B must never permit mutations, even if an env var is misconfigured. |
| Security impact | Accidental mutation enablement could write authoritative state during what should be read-only observation. |
| Component | `backend/hos4c/environment.py`, `backend/hos4c/main.py` |
| Required change | Add startup check: if Environment is LOCAL_TEST/STAGING and `mutations_disabled()` is False, override to True + log CRITICAL. Add to `validate_startup()`. |
| Tests required | Unit test: LOCAL_TEST + MUTATIONS_DISABLED=false → startup overrides to true. Integration: attempt mutation → 503. FC-09 retest with fixed code. |
| Dependency | None |

### B2 — Production Snapshot Pipeline Timer

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-002 |
| Priority | **P0** — no production data without snapshot |
| Why it blocks | Hermes reads production data via snapshots. No snapshot = no production data to observe. |
| Security impact | None directly — without snapshots, Phase B has nothing to read. |
| Component | Root cron job or systemd timer on production VPS |
| Required change | Deploy timer that runs `sqlite3 production.db ".backup snapshot.db.tmp"` → integrity check → atomic rename → chmod 440 root:10010. |
| Tests required | Pipeline simulation already PASS. Production: schedule execution, integrity verification, atomic publish on real DB (read-only test: verify snapshot row count matches production). |
| Dependency | B3 (production credentials) |

### B3 — Production Read-Only Credentials

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-003 |
| Priority | **P0** |
| Why it blocks | Phase B requires 5 read-only credentials: snapshot path, B2 reader key, Telegram bot token, metrics proxy, production env file. |
| Security impact | Credential leak could expose production data to unauthorized reader. |
| Component | Host filesystem (`/etc/hermes-product-os-prod/`), Backblaze B2, Telegram |
| Required change | Amjad creates 5 credentials in secure custody. Hermes receives only read-only references. |
| Tests required | Credential separation test (G1.3 style). Reader key can't write. Writer key not deployed. No credential cross-contamination. |
| Dependency | Amjad authorization |

### B4 — Production Phase B Compose Deployment

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-004 |
| Priority | **P0** |
| Why it blocks | Phase B needs a separate production compose project with production mounts. |
| Security impact | Must not interfere with staging. Must not expose production ports. Must use `internal: true` network. |
| Component | `docker-compose.prod.yml` |
| Required change | Deploy production compose using same architecture as Test-B but with production snapshot path, production B2 reader key, production bot token. `restart: unless-stopped`. |
| Tests required | Compose validation. Container health. No host ports. No Traefik labels. Level 2 enforcement. Mutations disabled. |
| Dependency | B2, B3 |

### B5 — Fail-Closed Tests Against Production Compose

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-005 |
| Priority | **P1** |
| Why it blocks | Test-B tested 4/12 fail-closed scenarios at application layer. The remaining scenarios (FC-03, FC-04, FC-05) and all B2/credential scenarios must be verified against the actual production compose. |
| Security impact | Production compose may differ from Test-B in ways that break fail-closed behavior. |
| Component | Production compose + production credentials |
| Required change | Run FC-01 through FC-12 against production compose using production-level (but canary-scoped) data. |
| Tests required | 12 scenario results with observed vs expected. |
| Dependency | B4 |

### B6 — Production RPO/RTO Baseline

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-006 |
| Priority | **P1** |
| Why it blocks | Phase B must know the snapshot freshness (RPO) before it can responsibly report production state. |
| Security impact | Stale snapshot could show outdated decisions — misleading monitoring. |
| Component | Production snapshot timer + Hermes health endpoint |
| Required change | Measure snapshot age on production DB. Health endpoint reports snapshot freshness. |
| Tests required | RPO measurement on production data volume (not 28KB test). RTO measurement for full production restore (Phase C scope). |
| Dependency | B2 |

### B7 — Production Read-Only Canary Authorization

| Field | Value |
|---|---|
| Blocker ID | PHASE-B-BLK-007 |
| Priority | **P0** |
| Why it blocks | Amjad must explicitly authorize the first production read. |
| Security impact | Without authorization, any production access is unauthorized. |
| Component | Authorization gate (human decision) |
| Required change | Amjad authorizes single controlled production read canary. |
| Tests required | One verified read operation with audit evidence. Then STOP for review. |
| Dependency | B1-B6 |

---

## B. Architecture Gaps

### GAP-001 — Missing Policy Cross-Validation

| Field | Value |
|---|---|
| Classification | **PRODUCTION BLOCKER** (B1) |
| Finding | `MUTATIONS_DISABLED=false` enables mutations regardless of Environment enum policy. |
| Remediation | Startup cross-validation: if Environment restricts mutations AND `mutations_disabled()` is False, override to safe state. |
| Implemented in | `backend/hos4c/environment.py` → `validate_startup()` |

### GAP-002 — No Independent SQLite Read-Only URI Mode

| Field | Value |
|---|---|
| Classification | **DEFERRED HARDENING** (not a production blocker) |
| Finding | `sqlite3.connect(path)` without `?mode=ro`. Write prevention relies on L1 (filesystem 440) and L2 (mount :ro). Both independently proven. |
| Remediation | Add `?mode=ro` to snapshot observation connections for defense-in-depth. |
| Why deferred | L1+L2 provide equivalent enforcement. Adding mode=ro is a code change with no functional benefit given existing layers. Low priority. |

---

## C. Known Findings Classification

| # | Finding | Classification | Rationale |
|---|---|---|---|
| 1 | Policy cross-validation | **BLOCKER** (B1) | Fix before any production access |
| 2 | SQLite URI mode=ro | **DEFERRED** | L1+L2 proven equivalent |
| 3 | Runtime snapshot consumer | **DEFERRED** | No active consumer needed for Phase B canary — snapshot is mounted, health reports presence/staleness |
| 4 | Stale snapshot enforcement | **DEFERRED** | Shell simulation proven. Application enforcement is Phase B follow-up, not canary blocker |
| 5 | B2 application consumer | **DEFERRED** | B2 backup verification is Phase B operational scope, not canary minimum |
| 6 | Production credential provisioning | **BLOCKER** (B3) | Must exist for any production access |
| 7 | Metrics integration | **DEFERRED** | Phase B+ scoping |
| 8 | Production RPO/RTO | **BLOCKER** (B6) | Must be known for responsible monitoring |
| 9 | Production data-source config | **BLOCKER** (B2, B4) | Snapshot pipeline + compose |
| 10 | Audit/observability | **DEFERRED** | Audit logging code not yet implemented. Phase B canary can use Docker logs + health endpoint |

---

## D. Ordered Phase B Engineering Backlog

### PHASE B-CANARY-READY Sequence

```
STATE: PLANNED_ONLY
  │
  ├── TASK-001: Fix GAP-001 (policy cross-validation)      [P0, blocks all]
  │     Files: backend/hos4c/environment.py
  │     Test: FC-09 retest with fixed code
  │
  ├── TASK-002: Production canary authorization             [P0, human gate]
  │     Amjad authorizes production canary (single read)
  │
  ├── TASK-003: Create production credentials               [P0, B3]
  │     5 credentials, Amjad creates, Hermes verifies
  │
  ├── TASK-004: Deploy production snapshot timer            [P0, B2]
  │     Root cron on production VPS, WAL-safe .backup
  │
  ├── TASK-005: Deploy production compose                   [P0, B4]
  │     docker-compose.prod.yml, separate from staging
  │
  ├── TASK-006: Production baseline health checks           [P1]
  │     Verify Level 2, mutations disabled, snapshot accessible
  │
  ├── TASK-007: Run fail-closed tests against prod compose  [P1, B5]
  │     FC-01 through FC-12 on production deploy
  │
  ├── TASK-008: Measure production RPO                      [P1, B6]
  │     Snapshot freshness on production data
  │
  └── TASK-009: Execute production canary read              [P0, B7]
        Single verified read + audit evidence → STOP

STATE: PHASE_B_CANARY_READY
```

### TASK-001 — Fix GAP-001

| Field | Value |
|---|---|
| Objective | Prevent MUTATIONS_DISABLED=false from enabling mutations in restricted environments |
| Files | `backend/hos4c/environment.py` |
| Change | In `validate_startup()`: if Environment is LOCAL_TEST/LOCAL_SIMULATION/AUTH_REVIEW/STAGING and `mutations_disabled()` is False, log CRITICAL, override to True, continue startup. |
| Acceptance | Unit test: LOCAL_TEST + MUTATIONS_DISABLED=false → `mutations_disabled()` returns True. FC-09 retest: attempted mutation → 503. |
| Tests | 2 unit tests, 1 integration test |
| Rollback | Revert commit, no data impact |

### TASK-002 — Production Canary Authorization

| Field | Value |
|---|---|
| Objective | Amjad authorizes single controlled production read |
| Change | None — human decision gate |
| Acceptance | Authorization message from Amjad |
| Rollback | N/A |

### TASK-003 — Production Credentials

| Field | Value |
|---|---|
| Objective | Create 5 production read-only credentials |
| Change | Amjad creates: snapshot path (440 root:10010), B2 reader key, Telegram bot token, metrics proxy config, env file. Hermes verifies read-only, separation, no cross-contamination. |
| Acceptance | G1.3-style verification. All 5 credentials: readable by container, not writable, not deletable, not shared with staging. |
| Tests | Credential separation matrix |
| Rollback | Delete `/etc/hermes-product-os-prod/`, revoke B2 key, revoke bot token |

### TASK-004 — Production Snapshot Timer

| Field | Value |
|---|---|
| Objective | Deploy root cron/systemd timer that snapshots production DB every 15 min |
| Change | Timer script: `.backup` → integrity check → atomic mv → chmod 440 root:10010. No WAL truncate. |
| Acceptance | Snapshot appears at `/var/lib/hermes/snapshots/production-snapshot.db`. Integrity=ok. Freshness ≤ 15 min. |
| Tests | Pipeline simulation already PASS. Production: verify snapshot row count matches production. |
| Rollback | Disable timer, remove snapshot files |

### TASK-005 — Production Compose

| Field | Value |
|---|---|
| Objective | Deploy docker-compose.prod.yml on production VPS |
| Change | Compose file using production snapshot path, production B2 reader key, production bot token, production env. `restart: unless-stopped`. `internal: true` network. No host ports. |
| Acceptance | Container healthy. Level 2. Mutations disabled. Snapshot accessible. B2 reader configured. |
| Tests | Compose config validation. Container health. Mount verification. |
| Rollback | `docker compose down`, revert to Phase A compose |

### TASK-006 — Production Baseline Health

| Field | Value |
|---|---|
| Objective | Verify production container health and enforcement layers |
| Change | None — inspection only |
| Acceptance | Health: alive, LOCAL_TEST (or PRODUCTION if authorized), mutations=DISABLED. Snapshot mount: ro. No host ports. |
| Tests | Health endpoint, mount inspection, network check |
| Rollback | N/A |

### TASK-007 — Production Fail-Closed Tests

| Field | Value |
|---|---|
| Objective | Run all 12 fail-closed scenarios against production compose |
| Change | Temporary configuration changes per test, restored after each |
| Acceptance | FC-01 through FC-12 results. All security-critical scenarios PASS. Document any gaps. |
| Tests | 12 scenario matrix |
| Rollback | Restore production compose from backup after each test |

### TASK-008 — Production RPO Measurement

| Field | Value |
|---|---|
| Objective | Measure snapshot freshness on production data volume |
| Change | None — measurement only |
| Acceptance | RPO ≤ configured threshold (15 min). Staleness detection functional. |
| Tests | Snapshot age measurement over observation period (e.g., 1 hour) |
| Rollback | N/A |

### TASK-009 — Production Canary Read

| Field | Value |
|---|---|
| Objective | Execute single controlled production read with audit evidence |
| Change | None — one read operation only |
| Acceptance | Read succeeds. Audit record created. No mutation. Amjad reviews evidence. |
| Tests | Verify read result, verify audit record, verify zero writes |
| Rollback | N/A — read-only operation |

---

## E. Definition of PHASE_B_CANARY_READY

Phase B canary is ready when:

1. GAP-001 is fixed and retested (TASK-001)
2. Amjad has authorized the production canary (TASK-002)
3. All 5 production credentials exist and are verified read-only (TASK-003)
4. Production snapshot timer is deployed and verified (TASK-004)
5. Production compose is deployed and healthy (TASK-005)
6. Production baseline health checks pass (TASK-006)
7. Fail-closed tests pass against production compose (TASK-007)
8. Production RPO is baselined (TASK-008)
9. Production canary read is authorized (TASK-009)

---

## F. Revised GO/NO-GO Gate

| Check | Status |
|---|---|
| Test infrastructure ready | ✅ |
| GAP-001 fixed | ❌ (TASK-001) |
| Production credentials exist | ❌ (TASK-003) |
| Production snapshot timer | ❌ (TASK-004) |
| Production compose deployed | ❌ (TASK-005) |
| Production fail-closed tests | ❌ (TASK-007) |
| Production RPO baselined | ❌ (TASK-008) |
| Canary authorized | ❌ (TASK-002) |

**GO/NO-GO: NO-GO.** 8 prerequisites incomplete. Minimum safe path: TASK-001 → TASK-002 through TASK-009.

---

**Production credentials: 0. Production connections: 0. Production reads: 0. Hermes authority: 0.**