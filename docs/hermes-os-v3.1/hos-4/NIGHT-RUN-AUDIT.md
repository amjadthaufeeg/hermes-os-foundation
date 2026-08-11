# Workstream 1 — Production Runtime Audit

## Finding 1: SIM_DECISIONS leak in PRODUCTION [CRITICAL]

**Evidence:** `main.py:58` defines `SIM_DECISIONS = [...]` and `main.py:256` returns them unconditionally:
```python
return {"decisions": SIM_DECISIONS, "count": len(SIM_DECISIONS), "mode": "SIMULATION"}
```

**Impact:** In PRODUCTION with `SIMULATION_MODE=false`, the `/api/decisions` endpoint returns hardcoded simulation data (`DEC-HOS-001, DEC-HOS-002, DEC-HOS-019`) instead of querying `production.db`.

**Fix required:** Gate decision endpoints on SIMULATION_MODE. In production, query the database.

## Finding 2: OAuth routes gated [OK]

OAuth login/callback are gated behind `SIMULATION_MODE` (lines 162, 172). In production, these return 503. Correct behavior.

## Finding 3: No filesystem writes beyond DB [OK]

The app only writes to SQLite via `database.py`. No file logging, no temp files, no `/tmp` writes. Logs go to stdout.

## Finding 4: Logs volume optional [INFO]

`observability.py` writes structured logs to stdout. Docker captures stdout. The `hpos-prod-logs` volume is not needed for Phase B but provides future flexibility. Keep it — no security risk.

## Finding 5: Health endpoint correct [OK]

`main.py:117` returns `environment` and `mutations` state from actual runtime checks. No simulation data.

## Finding 6: Mutations_disabled() enforced [OK]

TASK-001 added GAP-001 enforcement. `mutations_disabled()` cross-checks POLICY. In PRODUCTION, always True.

## Finding 7: Database path resolution [OK]

`config.py:15`: `DATABASE_PATH = os.environ.get("AUDIT_DB", ".hermes/audit/audit.db")`  
Compose sets `DATABASE_PATH=/opt/hermes/data/production.db`  
`get_db()` uses `os.environ.get("DATABASE_PATH", DATABASE_PATH)` — production path wins.

## Finding 8: init_db() not called at startup [OK]

`main.py:47` comments out `init_db()`. Only called explicitly (P3 init script). No risk of schema recreation or migration at startup.

## Finding 9: read_only rootfs compatibility [OK]

App writes only to SQLite (via volume mount). Healthcheck uses urllib (no filesystem). Lifespan doesn't touch filesystem. Compatible with `read_only: true`.

## Finding 10: cap_drop ALL compatibility [OK]

Port 8080 is non-privileged. No filesystem capabilities needed (volume is UID 10010 owned, W_OK granted by Unix permissions). Healthcheck uses only network. Compatible.

## Finding 11: Operational writes [INFO]

Under `MUTATIONS_DISABLED=true`, the application gate blocks authoritative decision mutations. However, `sessions` and `idempotency_records` tables may be written for operational login/CSRF/idempotency. These are local operational state, not authoritative decisions. GAP-001 only blocks the authoritative mutation path.

## Finding 12: WAL/SHM creation [OK]

SQLite creates WAL/SHM in the data directory. Directory is 10010:10010/750. Process is UID 10010. Files inherit 10010:10010 ownership. Compatible.

## Finding 13: User explicit [NEEDS FIX]

Compose at d816fbf already has `user: "10010:10010"`. Confirmed correct.

## Finding 14: SIMULATION_MODE doesn't gate decisions [CRITICAL]

`SIMULATION_MODE=false` gates OAuth but NOT the decision listing endpoint. Production would serve hardcoded simulation decisions. This is the priority fix for the night run.