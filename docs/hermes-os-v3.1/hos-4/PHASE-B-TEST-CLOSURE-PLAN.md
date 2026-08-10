# Phase B — Test Closure Plan (Group 1)

**Objective:** Eliminate NOT TESTED controls without crossing production boundary.  
**Status:** PLANNING. No production.

---

## G1.1 — Six-Layer Read-Only Enforcement

**Current status:** PARTIAL. 4 layers partially proven in snapshot simulation. Activation-level and runtime verification layers require Level 2 deployment.

**Objective:** Prove each layer independently, then prove multi-layer defense survives single-layer failure.

**Layers:**

| # | Layer | How Proven | Status |
|---|---|---|---|
| L1 | Credential | Filesystem mode 440, root:10010 — host enforces no-write | PARTIAL (snapshot simulation) |
| L2 | Filesystem/mount | Container bind mount `:ro` — kernel enforces no-write | NOT TESTED (requires compose deployment) |
| L3 | DB/API | SQLite `?mode=ro` on connection — SQLite rejects writes | NOT TESTED (requires Level 2 compose) |
| L4 | Application | `MUTATIONS_DISABLED=true` — mutation paths return 403 | PARTIAL (verified in Phase A, needs Level 2 context) |
| L5 | Activation | `LEVEL_2` disables write code paths | NOT TESTED (requires Level 2 deployment) |
| L6 | Runtime verification | Health endpoint validates all layers at startup + heartbeat | NOT TESTED |

**Test design:**
- Deploy simulated Phase B compose with Level 2, snapshot mount, B2 stub, metrics stub
- Test each layer by attempting writes through various paths
- For each layer, deliberately weaken/remove ONE layer, prove remaining layers still block writes
- Test: L1+L2+L3+L4+L5+L6 → write blocked
- Test: Remove L2 (mount rw) → L3 catches write → write blocked
- Test: Remove L3 (open rw) → L4 catches write → write blocked
- Test: Remove L4 (mutations enabled) → L5 catches write → write blocked

**Prerequisites:** Phase B compose with all 6 layers configured, staging snapshot for test reads.

**Risk:** LOW — all test writes are to staging snapshot, not production.

**Expected evidence:** 6 layer-tests + 4 single-failure tests = 10 PASS/FAIL results.

**VPS commands required:** YES — compose deployment + test execution.

---

## G1.2 — Twelve Fail-Closed Scenarios

**Current status:** NOT TESTED. Scenarios documented, stubs created.

**Objective:** Execute all 12 scenarios against Phase B-like compose. Every failure must reduce capability.

**Scenarios:**

| # | Scenario | Expected | Test Method |
|---|---|---|---|
| F1 | Missing credential | Container fails to start or readiness NOT_READY | Remove P1 mount from compose |
| F2 | Invalid credential | DB open fails, health UNHEALTHY | Replace snapshot with corrupt file |
| F3 | Missing snapshot | Readiness NOT_READY | Remove snapshot file from host path |
| F4 | Corrupt snapshot | Integrity check fails, health UNHEALTHY | Replace with non-DB file |
| F5 | Stale snapshot (>1hr) | Health shows STALE, REFUSE_READ | touch old timestamp |
| F6 | Missing mount | Container starts but path not present | Remove mount from compose |
| F7 | B2 unavailable | Backup verification skipped, alert raised | Block B2 endpoint via iptables (temp) |
| F8 | Metrics unavailable | Metrics endpoint returns error | Remove metrics proxy |
| F9 | Policy mismatch | Container exits at startup | Set MUTATIONS_DISABLED=false |
| F10 | Activation mismatch | Container exits at startup | Set ACTIVATION_LEVEL=INVALID |
| F11 | Malformed config | docker compose config fails | Break YAML |
| F12 | Service restart | All checks re-run, passes or exits | docker compose restart |

**Prerequisites:** Phase B compose with all components.

**Risk:** LOW — all in staging, no production impact.

**Expected evidence:** 12 results with observed behavior vs expected.

**VPS commands required:** YES — 12 scenario tests.

---

## G1.3 — Credential Separation

**Current status:** NOT TESTED. Naming scheme documented but not exercised.

**Objective:** Prove staging and production-style credentials are structurally separate with no fallback path.

**Test design:**
1. Create synthetic "production" credential files at `PROD_PATH=/etc/hermes-product-os-prod/secrets/*`
2. Verify `STAGING_PATH=/etc/hermes-product-os/secrets/*` exists separately
3. Prove no file, env var, or mount references cross between staging and prod paths
4. Test: remove staging B2_WRITER_KEY_ID, verify prod path is NOT used as fallback
5. Test: set `B2_WRITER_KEY_ID` env var incorrectly, verify it doesn't override file mount
6. Prove revocation: remove prod credential files → container restart → access lost

**Prerequisites:** Synthetic prod credential directory with stub files.

**Risk:** LOW — stub credentials only.

**Expected evidence:** 6 tests with PASS/FAIL on separation, fallback, and revocation.

**VPS commands required:** YES — file creation + container tests.

---

## G1.4 — Audit Logging

**Current status:** NOT TESTED. Hermes audit logging is not yet implemented.

**Objective:** Prove simulated Phase B reads produce structured audit records.

**Test design:**
1. Add audit logging to Hermes health/monitoring endpoints (if not present)
2. Execute a simulated read (SELECT on snapshot, B2 list, metrics poll)
3. Verify audit record contains: actor, source, operation, timestamp, activation_level, policy_decision, result, correlation_id
4. Verify audit record does NOT contain: secret values, private keys, credential values, decision content
5. Verify audit records are written to a file that is separate from the snapshot (not writing to read-only source)

**Prerequisites:** Audit logging code in Hermes (may be stub for simulation).

**Risk:** LOW — test reads only.

**Expected evidence:** Sample audit records with redaction verification.

**VPS commands required:** YES — but depends on audit logging implementation status. May need code change first.

---

## G1.5 — Rollback

**Current status:** NOT TESTED. Kill switch verified at Level 1. Level 2 → Level 1 rollback not yet tested.

**Objective:** Prove Phase B can be disabled and returned to Level 1 without disruption.

**Test design:**
1. Deploy Phase B-like compose with Level 2, snapshot mount
2. Start, verify reads work, verify Level 2 + mutations DISABLED
3. Invoke kill switch: `docker compose stop hpos`
4. Verify container stopped
5. Deploy Phase A compose: `docker compose up -d`
6. Verify Level 1 active, mutations DISABLED
7. Verify simulated production snapshot NOT accessible from Phase A
8. Verify unrelated services healthy
9. Record timing: stop → Level 1 restored

**Prerequisites:** Both Phase A and Phase B compose files available.

**Risk:** LOW — staging only.

**Expected evidence:** 9-step procedure with timing and PASS/FAIL.

**VPS commands required:** YES — compose switching.

---

## G1.6 — Concurrent-Write Tolerance

**Current status:** NOT TESTED / NOT CLAIMED.

**Objective:** Prove SQLite .backup produces consistent snapshot while source is actively written.

**Test design:**
1. Create WAL-mode source DB with initial data
2. Start background writer process that inserts rows continuously
3. While writer is running, execute `sqlite3 source.db ".backup snapshot.db.tmp"`
4. After backup completes, stop writer
5. Verify: backup returned successfully (no error)
6. Verify: snapshot passes integrity_check
7. Verify: all rows in source are present in snapshot (no partial rows)
8. Verify: source writer never received errors
9. Verify: snapshot row count <= source row count (if writer was still inserting during backup, snapshot may have fewer rows — this is acceptable)
10. Verify: no WAL TRUNCATE was used

**Prerequisites:** Background writer script.

**Risk:** LOW — simulation only, no production DB.

**Expected evidence:** Row counts, integrity result, writer health.

**VPS commands required:** YES — concurrent writer + backup.

---

## Summary

| # | Control | Status | VPS Needed | Can Test Now? |
|---|---|---|---|---|
| G1.1 | 6-layer enforcement | PARTIAL | YES | Requires Phase B compose |
| G1.2 | 12 fail-closed | NOT TESTED | YES | Requires Phase B compose |
| G1.3 | Credential separation | NOT TESTED | YES | Can test with stubs |
| G1.4 | Audit logging | NOT TESTED | YES (depends on code) | May need code change |
| G1.5 | Rollback | NOT TESTED | YES | Requires both composes |
| G1.6 | Concurrent-write | NOT TESTED | YES | Can test with simulation |

**Dependency:** G1.1, G1.2, and G1.5 all require a simulated Phase B compose deployment. I recommend creating a `docker-compose.test-b.yml` that mirrors the planned production compose but uses staging/stub resources. This single compose enables 3 of 6 tests.

**Recommendation:** Authorize creation of Phase B test compose + Group 1 test execution. All tests are staging-only. No production. No credentials. No Level 2 activation of production systems.