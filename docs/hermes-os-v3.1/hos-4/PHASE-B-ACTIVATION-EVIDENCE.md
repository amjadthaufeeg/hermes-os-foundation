# Phase B — Activation Evidence Package

**Generated:** 2026-08-09  
**Source:** Engineering-supervised non-production snapshot simulation  
**Status:** PRE-ACTIVATION. Phase B NOT yet authorized.

---

## 1. Control Status Matrix

| # | Control | Status | Evidence Source |
|---|---|---|---|
| C1 | Kill switch | PASS | Targeted `docker compose stop hpos`, all services preserved |
| C2 | Snapshot creation (.backup, no WAL truncate) | PASS | `integrity_check=ok`, content verified |
| C3 | Pre-publication integrity gate | PASS | .tmp validated before `mv` publish |
| C4 | Atomic publication (rename) | PASS | Same filesystem confirmed, no .tmp remains |
| C5 | Published snapshot permissions | PASS | root:10010, mode 440 |
| C6 | Live-source mount isolation | PASS | SOURCE_NOT_IN_CONTAINER |
| C7 | Snapshot mount isolation | PASS | SNAPSHOT_NOT_MOUNTED |
| C8 | Point-in-time consistency | PASS | source=2, snapshot=1 |
| C9 | Corrupt-candidate rejection | PASS | Caught, removed, never published |
| C10 | Published-snapshot preservation | PASS | SHA256_MATCH before/after corrupt test |
| C11 | Fresh-policy evaluation | PASS | Age < 3600s → ALLOW_READ |
| C12 | Stale-policy evaluation | PASS | Age > 3600s → REFUSE_READ |
| C13 | Timestamp restoration | PASS | Original timestamp restored after test |
| C14 | Mutation boundary | PASS | mutations=DISABLED throughout |
| C15 | Simulation cleanup | PASS | All artifacts removed |
| C16 | Critical-asset preservation | PASS | All 10 assets preserved |
| C17 | Concurrent-write tolerance | NOT TESTED | Requires separate concurrent experiment |
| C18 | Production SQLite behaviour | NOT TESTED | Simulation only — production DB not connected |
| C19 | Production RPO | NOT TESTED | Requires production backup schedule |
| C20 | Production RTO | NOT TESTED | Requires production restore exercise |
| C21 | Production credential behaviour | NOT TESTED | No production credentials exist |
| C22 | Production data-source availability | NOT TESTED | No production data sources connected |
| C23 | 6-layer read-only enforcement | PARTIAL | 4 layers proven in simulation (credential stub, filesystem, DB, application). Activation level + runtime verification require Level 2 deployment. |
| C24 | 12 fail-closed scenarios | NOT TESTED | Requires production-like Phase B compose deployment |
| C25 | Credential separation (staging vs prod) | NOT TESTED | No production credentials created |
| C26 | Audit logging | NOT TESTED | Requires Hermes-side logging implementation |
| C27 | Rollback test | NOT TESTED | Requires Phase B-like Level 2 deployment |
| C28 | Production readiness gate | NOT APPLICABLE | Phase B not yet activated |

---

## 2. Readiness Score

| Category | Controls | PASS | NOT TESTED | Score |
|---|---|---|---|---|
| Snapshot pipeline | C2-C13, C15-C16 | 14 | 0 | 100% |
| Kill switch | C1 | 1 | 0 | 100% |
| Mutation boundary | C14 | 1 | 0 | 100% |
| Concurrent-write | C17 | 0 | 1 | 0% |
| Production integration | C18-C22 | 0 | 5 | 0% |
| Enforcement layers | C23-C26 | 0 | 4 | 0% |
| Rollback | C27 | 0 | 1 | 0% |

**Overall: 16/28 PASS (57%). 11 NOT TESTED. 1 NOT APPLICABLE.**

---

## 3. Remaining NOT TESTED Controls

| # | Control | Prerequisite |
|---|---|---|
| C17 | Concurrent-write tolerance | Separate concurrent experiment design |
| C18 | Production SQLite behaviour | Production DB access (not yet authorized) |
| C19 | Production RPO | Production backup schedule |
| C20 | Production RTO | Production restore exercise |
| C21 | Production credential behaviour | Production credentials created |
| C22 | Production data-source availability | Production data sources connected |
| C23a | Activation-level enforcement | Level 2 deployment |
| C23b | Runtime verification | Level 2 runtime |
| C24 | 12 fail-closed scenarios | Phase B compose deployment |
| C25 | Credential separation | Production credentials created |
| C26 | Audit logging | Hermes logging implementation |
| C27 | Rollback test | Phase B compose deployment |

---

## 4. Prerequisites Before Production-Read Activation

1. Production B2 backup verification credential (read-only)
2. Production alert destination (Telegram bot token)
3. Production snapshot pipeline timer (root cron/systemd)
4. Phase B docker-compose.prod.yml with production mounts
5. Production snapshot directory with correct permissions
6. 12 fail-closed scenarios tested against production-like compose
7. Rollback test: Level 2 → kill switch → Level 1
8. Audit logging verified
9. Production RPO/RTO baselined

---

## 5. Production Credential Requirements

| # | Credential | Purpose | Permissions |
|---|---|---|---|
| P1 | Production snapshot path | Mount read-only snapshot | host:400, mount:ro |
| P2 | Production B2 reader key | Verify production backups | readFiles, listFiles |
| P3 | Production Telegram bot token | Alert delivery | Send messages only |
| P4 | Docker metrics proxy | Production metrics | Container stats read-only |
| P5 | Production env file | Activation level, feature flags | 440 root:10010 |

**Zero production credentials created. Production credentials = 0.**

---

## 6. Activation Sequence (NOT YET AUTHORIZED)

1. Amjad authorizes Phase B activation
2. Create production credentials (P1-P5)
3. Install snapshot pipeline timer on production VPS
4. Validate snapshot pipeline with production DB
5. Deploy `docker-compose.prod.yml`
6. Run 12 fail-closed tests
7. Run rollback test (Level 2 → kill → Level 1)
8. Verify audit logging
9. Baseline production RPO
10. Measure production RTO
11. Open production read-only monitoring
12. Deliver first production alert

---

## 7. Rollback Sequence

```bash
# Kill switch: stop Phase B container
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml stop hpos

# Verify: container stopped, no production mounts active
docker ps --filter name=hermes-product-os-prod

# Return to Phase A (staging only)
docker compose -f /docker/hermes-product-os/docker-compose.yml up -d
docker exec hermes-product-os python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/api/health').read().decode())"
# Expected: mutations=DISABLED, Level 1
```

---

## 8. Residual Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Snapshot staleness > policy | MEDIUM | Stale detection + REFUSE_READ + alert |
| Snapshot corruption between intervals | LOW | Integrity gate on every publish |
| Production credential leak | HIGH | Read-only credentials, filesystem 440, no network exposure of snapshot |
| Kill switch fails | MEDIUM | Tested in simulation, relies on Docker stop which detaches mounts |
| Concurrent-write interference | UNKNOWN | NOT TESTED — requires separate experiment |

---

## 9. Recommendation

**NOT_READY_FOR_PHASE_B_AUTHORIZATION**

**Reason:** 11 controls remain NOT TESTED. Snapshot pipeline simulation is complete (16/28 PASS), but production integration, enforcement layers, credential behaviour, and rollback have not been exercised against production-like deployment.

**Prerequisites satisfied by simulation:**
- Snapshot creation pipeline (14 controls PASS)
- Kill switch design (PASS)
- Mutation boundary (PASS)

**Prerequisites remaining:**
- Production credential deployment
- Phase B compose deployment
- Fail-closed testing
- Rollback testing
- Audit logging
- RPO/RTO baselining

---

**Phase A: APPROVED_COMPLETE. Phase B: PLANNED_ONLY. Production: 0. Hermes authority: 0.**