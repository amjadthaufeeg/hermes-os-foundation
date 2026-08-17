# Phase B — Readiness Assessment

**Generated:** 2026-08-10  
**Updated:** 2026-08-17  
**Status:** PRE-ACTIVATION. Phase B NOT yet authorized.  
**Recommendation:** NOT_READY_FOR_PRODUCTION_READONLY_ACTIVATION

---

## 1. All Controls Summary

### Preventive Enforcement (G1.1)

| Layer | Control | Status |
|---|---|---|
| L1 | Host filesystem permissions (mode 440) | ✅ PASS |
| L2 | Docker read-only bind mount | ✅ PASS |
| L3 | Application authoritative mutation gate | ✅ PASS |

### Fail-Closed Behaviour (G1.2)

| # | Scenario | Status |
|---|---|---|
| FC-12 | Service restart preserves boundary | ✅ PASS |
| FC-10 | Invalid environment fails closed | ✅ PASS |
| FC-11 | Malformed config rejected before deploy | ✅ PASS |
| FC-06 | Missing snapshot mount — no fallback | ✅ PASS |
| FC-07a | External network unavailable (steady state) | ✅ PASS |
| FC-07b | B2 application fail-closed | NOT TESTED |
| FC-04 | Corrupt snapshot runtime rejection | SKIP (pipeline proven) |
| FC-03 | Missing snapshot runtime rejection | SKIP (pipeline proven) |
| FC-02 | Invalid B2 credential | NOT TESTABLE |
| FC-01 | Missing B2 credential | NOT TESTABLE |
| FC-05 | Stale snapshot enforcement | ✅ CLOSED LOCALLY — metadata freshness + SHA binding + decision-read gate |
| FC-08 | Metrics unavailable | NOT APPLICABLE |
| FC-09 | Policy mismatch (MUTATIONS_DISABLED=false) | ✅ CLOSED |

### Credential Separation (G1.3)

| Check | Status |
|---|---|
| Separate staging/test-b namespaces | ✅ PASS |
| Cross-access denied | ✅ PASS |
| No production credentials | ✅ PASS |
| Public key sharing intentional | ✅ PASS |
| No credentials in env/logs/inspect | ✅ PASS |

### Snapshot Pipeline (Pre-Test-B)

| Control | Status |
|---|---|
| Snapshot creation (.backup, no WAL truncate) | ✅ PASS |
| Pre-publication integrity gate | ✅ PASS |
| Atomic publication (rename) | ✅ PASS |
| Point-in-time consistency | ✅ PASS |
| Corrupt-candidate rejection | ✅ PASS |
| Published-snapshot preservation | ✅ PASS |
| Fresh-policy evaluation | ✅ PASS |
| Stale-policy evaluation | ✅ PASS |
| Kill switch | ✅ PASS |
| Mutation boundary | ✅ PASS |

### Rollback (G1.5)

| Check | Status |
|---|---|
| Baseline → change → restore | ✅ PASS |
| Security state preserved | ✅ PASS |
| Operational DB preserved | ✅ PASS |
| Staging unaffected | ✅ PASS |

---

## 2. PASS Controls — 22

| Domain | Count |
|---|---|
| Preventive enforcement | 3 |
| Fail-closed tested | 5 |
| Credential separation | 5 |
| Snapshot pipeline | 8 |
| Rollback | 1 |

---

## 3. NOT TESTED / NOT TESTABLE — 4

| Control | Reason |
|---|---|
| FC-07b B2 app fail-closed | No B2 consumer in application code |
| FC-02 Invalid B2 credential | No B2 consumer |
| FC-01 Missing B2 credential | No B2 consumer |
| FC-08 Metrics | Deferred to production deployment |

---

## 4. NOT IMPLEMENTED — 1

| Control | Impact |
|---|---|
| SQLite split read-only decisions connection | Current shared DB helper also supports operational session/idempotency writes; production is protected by read-only snapshot mount, metadata freshness, SHA binding, and mutation policy |

---

## 5. NOT APPLICABLE — 3

| Control | Reason |
|---|---|
| FC-08 Metrics | No metrics integration at Test-B scope |
| FC-04 Runtime corrupt snapshot | Pipeline-level rejection already proven |
| FC-03 Runtime missing snapshot | Pipeline-level protection already proven |

---

## 6. Documented Architecture Gaps — Current Status

### GAP-001: Policy Mismatch (FC-09)

**Severity:** HIGH  
**Finding:** Setting `MUTATIONS_DISABLED=false` in LOCAL_TEST would enable authoritative mutations because the `POLICY` dict in `environment.py` is never cross-validated against the env var at runtime.  
**Remediation:** Add startup validation: if `Environment.LOCAL_TEST` is active and `mutations_disabled()` returns `False`, refuse to start (or at minimum, emit CRITICAL log and override to disabled).  
**Status:** CLOSED. Environment policy is authoritative and full regression covers the mutation-denial path.

### FC-05: Snapshot Freshness and Path Validation

**Severity:** P0/P1  
**Finding:** Production decision reads lacked a centralized freshness gate and startup did not validate that `DATABASE_PATH` points at the approved snapshot mount.  
**Remediation:** Production policy now requires snapshot freshness; startup/readiness fail closed on missing/stale/mismatched metadata; both decision read endpoints return 503 if the snapshot becomes stale after startup; health exposes snapshot freshness.  
**Status:** CLOSED LOCALLY. VPS certification remains GATED.

### GAP-002: No Independent SQLite Read-Only Mode

**Severity:** MEDIUM  
**Finding:** Application uses `sqlite3.connect(path)` without `?mode=ro` URI parameter. Write prevention relies entirely on filesystem (L1) and mount (L2) layers.  
**Remediation:** Production compose now uses read-only snapshot and metadata mounts; application validates snapshot prefix/freshness/SHA before reads. A split operational DB/read snapshot connection remains future hardening.  
**Blocker for production?** No for local release-candidate code. VPS certification still must verify the mounts and runtime behavior.

---

## 7. Remaining Production Blockers

| # | Blocker | Required Before Activation |
|---|---|---|
| B1 | Fix GAP-001 (policy cross-validation) | ✅ CLOSED |
| FC-05 | Snapshot freshness/path/hash enforcement | ✅ CLOSED LOCALLY; VPS certification required |
| B2 | Production snapshot pipeline timer | **GATED** — root/systemd on VPS |
| B3 | Production source access | **GATED** — Amjad-controlled production path/read access |
| B4 | Production Phase B compose deployment | **GATED** — separate from staging and Test-B |
| B5 | 12 fail-closed tests against production compose | **YES** — all scenarios that Test-B couldn't exercise |
| B6 | Production RPO/RTO baseline | **YES** — measured on production data volume |
| B7 | Production read-only canary authorization | **YES** — separate Amjad authorization |

---

## 8. Deferred Hardening (Not Blockers)

| Item | Notes |
|---|---|
| GAP-002: Split read-only decision connection | Defense-in-depth, not a blocker |
| B2 application consumer | No B2 backup verification endpoint exists yet — future work |
| Stale snapshot application enforcement | Closed locally; VPS runtime evidence pending |
| Metrics integration | Phase B+ scoping |
| Concurrent-write tolerance | NOT TESTED — requires separate experiment |

---

## 9. Recommended Next Engineering Work

1. **VPS/root certification** — Run the Docker/root/flock-backed suites in the target Linux environment.
2. **Production source authorization** — Amjad authorizes the production path/read access required for B2b.
3. **Production snapshot pipeline certification** — Verify timer, freshness, metadata SHA, and RPO on the production source.
4. **Production canary authorization** — Execute the single read-only canary only after explicit approval.
5. **Future hardening** — Split operational session/idempotency storage from read-only decision snapshot access.

---

## 10. GO / NO-GO Recommendation

| Question | Answer |
|---|---|
| Is the test infrastructure ready? | **YES** — Test-B composition, isolation, and rollback proven |
| Is the snapshot pipeline ready? | **YES** — All pipeline controls pass in simulation |
| Is the enforcement model ready? | **LOCAL READY** — mutation policy and freshness/path/hash gates pass local regression |
| Is the fail-closed model ready? | **LOCAL READY / VPS PENDING** — local app gates pass; Docker/root/flock scenarios need VPS |
| Is the credential model ready? | **YES** — Namespace separation proven |
| Can production be activated? | **NO** — 7 blockers remain |

**Recommendation: LOCAL_RELEASE_CANDIDATE_READY; NOT_READY_FOR_PRODUCTION_READONLY_ACTIVATION until GATED VPS certification completes.**

Proceed next with explicit Amjad authorization for VPS/root certification. Phase A remains APPROVED_COMPLETE. Phase B production activation remains GATED.

---

**Production credentials: 0. Production connections: 0. Production reads: 0. Production writes: 0. Live mutations: 0. Hermes authority: 0.**
