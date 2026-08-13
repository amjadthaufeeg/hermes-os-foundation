# B5 — Read Path Inventory

**All endpoints and code paths capable of reading authoritative/production decision data.**

---

## Endpoint Inventory

| # | Endpoint | Source | Environment Gate | Freshness | Mutation | Auth | Fail-Closed | Bypass Risk |
|---|---|---|---|---|---|---|---|---|
| 1 | `GET /api/health` | `env_get_env()`, `mutations_disabled()` | Always available | N/A | Read-only | None | N/A — doesn't access data | None |
| 2 | `GET /api/health/readiness` | `validate_startup()`, `DATABASE_PATH` check | Always available | N/A | Read-only | None | Returns `ready: false` on errors | None |
| 3 | `GET /api/metrics` | Prometheus metrics | Always available | N/A | Read-only | None | Returns metrics or 404 | None |
| 4 | `GET /api/decisions` | **DB (PRODUCTION) or SIM_DECISIONS (sim)** | `is_simulation_mode()` | **NONE** | Read-only | None | `SIMULATION_MODE` missing → sim | **HIGH** — no freshness, no auth |
| 5 | `GET /api/decisions/{id}` | **DB (PRODUCTION) or SIM_DECISIONS (sim)** | `is_simulation_mode()` | **NONE** | Read-only | None | 404 if not found | **HIGH** — no freshness, no auth |
| 6 | `POST /api/decisions/{id}/actions` | `SIM_DECISIONS` or DB + authoritative adapter | `mutations_disabled()` first | N/A | **BLOCKED** (503) | CSRF + session | 503 "Mutations disabled" | Blocked by GAP-001 |
| 7 | `GET /api/audit/events` | `audit_events` table | Always available | N/A | Read-only | Session optional | Returns events from DB | Low — reads audit, not decisions |
| 8 | `GET /api/audit/verify` | Hash chain verification | Always available | N/A | Read-only | None | Verifies hash chain | None |
| 9 | `GET /api/audit/export` | Export decisions + audit | Always available | N/A | Read-only | Session | Exports data | Medium — reads decisions indirectly |
| 10 | `POST /api/auth/login` | Simulation login | `is_simulation_mode()` gates OAuth, not sim login | N/A | No decision access | None | Returns session + CSRF | None |
| 11 | `GET /api/auth/session` | `sessions` table | Always available | N/A | No decision access | Session | Returns session info | None |
| 12 | `GET /auth/github/login` | OAuth redirect | `is_simulation_mode()` → 400 in sim | N/A | No decision access | None | 400 in simulation | None |
| 13 | `GET /auth/github/callback` | OAuth callback | `is_simulation_mode()` → 400 in sim | N/A | No decision access | OAuth state | 400 in simulation | None |

---

## Decision Read Paths (Critical)

### Path A: `GET /api/decisions`

```
Entry: /api/decisions
→ is_simulation_mode()?
  YES → return SIM_DECISIONS (3 hardcoded records)
  NO  → get_db() → SELECT * FROM decisions
→ Return list + count + mode
```

**Freshness: NONE.**  
**Auth: NONE.**  
**Fail-closed: SIMULATION_MODE missing → sim (safe default for test, dangerous for production with enforcement active).**

### Path B: `GET /api/decisions/{id}`

```
Entry: /api/decisions/{id}
→ is_simulation_mode()?
  YES → search SIM_DECISIONS
  NO  → get_db() → SELECT * FROM decisions WHERE id = ?
→ Return record + mode
```

**Freshness: NONE.**  
**Auth: NONE.**  
**Fail-closed: 404 if not found.**

### Path C: `GET /api/audit/export`

```
Entry: /api/audit/export
→ get_db() → SELECT * FROM decisions (may read decisions as part of export)
→ get_db() → SELECT * FROM audit_events
→ Return export
```

**Freshness: NONE.**  
**Auth: Session check.**  
**Risk: Reads decisions indirectly — freshness check may apply depending on export format.**

---

## Analysis

### Is fixing only `/api/decisions` and `/api/decisions/{id}` sufficient?

**Yes, for Phase B.** The only paths that directly read decision data from the production snapshot are:
1. `GET /api/decisions` — list all decisions
2. `GET /api/decisions/{id}` — get single decision

The audit export may include decision data but this is an operational endpoint, not a primary data access path. Mutation is blocked by GAP-001.

### Freshness enforcement must cover BOTH Path A and Path B.

A centralized freshness helper (similar to `mutations_disabled()`) is the correct pattern:

```python
def is_snapshot_fresh(max_age_s: int = 900) -> bool:
    """Check snapshot metadata freshness. Fail closed."""
    meta_path = DATABASE_PATH + ".meta.json"  # or derived from path
    ...
```

Called in both `list_decisions()` and `get_decision()` before the DB read.

### SIMULATION_MODE false + freshness = double protection

In PRODUCTION:
- `SIMULATION_MODE=false` → enforced by validate_startup()
- Snapshot freshness → enforced by read paths
- `MUTATIONS_DISABLED=true` → enforced by GAP-001

Three independent protections for production data integrity.

---

## Endpoint Not Requiring Freshness

| Endpoint | Why |
|---|---|
| `/api/health` | Operational — reads env/mutation state, not decisions |
| `/api/health/readiness` | Operational — configuration validation |
| `/api/metrics` | Operational — Prometheus metrics |
| `/api/audit/events` | Reads audit_events table (separate from decisions) |
| `/api/audit/verify` | Hash chain verification — no decisions |
| `/api/auth/*` | Authentication — no decisions |

---

**Read path inventory complete. Two primary decision read paths identified. Both require freshness enforcement.**