# B7 — Canary Authorization Readiness Plan

**No activation. Design only. Phase B — pre-canary.**

---

## B7 Objective

Authorize a controlled, time-limited, read-only production canary to validate the Phase B observation pipeline end-to-end.

---

## Authorization Model

**Amjad-only authorization.** No automated or delegated authorization. The canary is activated by explicit Amjad action and must expire automatically if not renewed.

---

## Canary Scope

| Aspect | Scope |
|---|---|
| Environment | PRODUCTION (B4 reader container) |
| Operation | Read-only (GET `/api/decisions`, GET `/api/decisions/{id}`) |
| Duration | 60 minutes (configurable) |
| Renewal | Manual Amjad action required |
| Access | Internal network only (no public route) |
| Mutations | DISABLED (enforced by GAP-001) |
| Data source | Production snapshot (refreshed every 15 min) |

---

## Canary Activation Design

### Option A: Temporary Traefik Route (Recommended)

```bash
# Add Traefik label to production compose (temporary)
# Route: hermes-canary.srv1750847.hstgr.cloud
# Basic auth: separate canary credentials

# After 60 minutes:
# Remove Traefik label, recreate container
```

### Option B: SSH Tunnel Access

```bash
# Amjad creates SSH tunnel to internal production network
ssh -L 8080:hermes-product-os-prod:8080 root@vps

# Access locally: http://localhost:8080/api/decisions
```

**Recommendation: Option B for initial canary** — simpler, no public exposure, full control. Option A for later B7 extended validation.

---

## Canary Credentials

| Credential | Purpose |
|---|---|
| SSH key (Amjad's existing) | Tunnel access |
| Container access | `docker exec` (root) |
| No new B2 credentials | Phase B is snapshot-only |
| No new API credentials | Internal network only |

---

## Canary Duration + Expiration

| Property | Value |
|---|---|
| Initial duration | 60 minutes |
| Expiration mechanism | SSH tunnel closed by Amjad; or Traefik route removed |
| Auto-expiration | Not enforced programmatically — relies on manual termination |
| Renewal | Amjad re-opens tunnel or re-adds route |

---

## Canary Verification (Evidence Required)

| # | Check | Method |
|---|---|---|
| 1 | Environment = PRODUCTION | `GET /api/health` |
| 2 | Mutations = DISABLED | `GET /api/health` |
| 3 | Decisions from production snapshot | `GET /api/decisions` → count matches expected |
| 4 | No SIM_DECISIONS leakage | Verify mode = PRODUCTION |
| 5 | Freshness check active | Verify snapshot age < 990s |
| 6 | Mutation denied (503) | `POST /api/decisions/.../actions` |
| 7 | Staging unaffected | Staging health endpoint |
| 8 | Test-B unaffected | Test-B health endpoint |
| 9 | Production DB untouched | Verify decision count unchanged in production.db |

---

## Abort Conditions

| Condition | Action |
|---|---|
| Mutation succeeds | **IMMEDIATE ABORT** — kill tunnel, investigate |
| SIM_DECISIONS served | **ABORT** — SIMULATION_MODE misconfiguration |
| Health reports mutations=SIMULATION_ONLY | **ABORT** — MUTATIONS_DISABLED not enforced |
| Staging degradation | **ABORT** — unanticipated interference |
| Production DB modified | **IMMEDIATE ABORT** — authority breach |
| Snapshot stale > 30 min | **PAUSE** — investigate timer |

---

## Rollback

```bash
# Option A: Remove Traefik route
docker compose down && docker compose up -d (after removing label)

# Option B: Close SSH tunnel
# Just close the SSH session

# In either case:
# Container remains running. production.db untouched.
# Snapshot pipeline unaffected.
```

---

## Prerequisites for B7 Activation

| Prerequisite | Status |
|---|---|
| B1 (GAP-001) policy enforcement | ✅ CLOSED |
| B2a/B2b snapshot pipeline | ✅ (per user report) |
| B3 (production credentials) | ✅ (per user report) |
| B4 (production compose + reader) | ✅ (per user report) |
| B5 (fail-closed tests) | ❌ BLOCKED on FC-05 |
| B6 (RPO/RTO baseline) | ❌ BLOCKED for full value on FC-05 |
| Canary credentials provisioned | ⬜ Requires Amjad |
| Abort/rollback procedures documented | ✅ This document |

---

## B7 Readiness

| Aspect | Status |
|---|---|
| Authorization model | ✅ Designed |
| Canary scope | ✅ Defined |
| Access mechanism | ✅ Options A and B designed |
| Verification checklist | ✅ 9 checks |
| Abort conditions | ✅ 6 conditions |
| Rollback | ✅ Documented |
| Dependency on B5/B6 | ❌ BLOCKED |

**B7 design is complete. Execution blocked on B5 FC-05 remediation and B6 baseline measurements.**

---

## Canary Authorization Checklist (for Amjad)

```
[ ] Confirm B5 FC05-FC12 all PASS
[ ] Confirm B6 RPO ≤ 990s for 24h
[ ] Confirm snapshot freshness enforcement active
[ ] Confirm MUTATIONS_DISABLED=true
[ ] Confirm SIMULATION_MODE=false
[ ] Establish SSH tunnel (Option B)
[ ] Execute 9-point verification checklist
[ ] Monitor for 60 minutes
[ ] Close tunnel after canary
[ ] Confirm no production data mutated
[ ] Record canary evidence
[ ] Sign off B7 closure
```

---

**B7 readiness: DESIGN COMPLETE, EXECUTION BLOCKED ON B5 + B6 + AMJAD.**