# Phase B — Updated Blocker Register

**Updated:** 2026-08-11  
**Status:** 2/7 blockers resolved

---

## Blocker Status

| ID | Blocker | Priority | Status |
|---|---|---|---|
| B1 / GAP-001 | Policy cross-validation | P0 | **CLOSED** — ec2d2cd, container proven |
| B2a | Snapshot refresh orchestrator (stub) | P0 | **CLOSED** — a7f9764, VPS runtime proven |
| B2b | Production source integration | P0 | NOT STARTED — requires B3 |
| B3 | Production credentials (5) | P0 | **REQUIRES AMJAD** |
| B4 | Production compose | P0 | DEPENDS ON B2b, B3 |
| B5 | Production fail-closed tests | P1 | DEPENDS ON B4 |
| B6 | Production RPO baseline | P1 | DEPENDS ON B2b |
| B7 | Canary authorization | P0 | DEPENDS ON B2b-B6 |

## B2 Split Clarification

| Sub-task | Scope | Source |
|---|---|---|
| B2a (CLOSED) | Refresh engine + timer + snapshot lifecycle | Stub source (/var/lib/hermes/b2a-test/) |
| B2b (pending) | Swap SOURCE_DB to production path | Production DB (requires B3 credentials) |

B2a is operational. B2b is configuration-only (same script, systemd, permissions) but requires B3 production credentials and separate authorization.

## Verified Properties (B2a)

- SQLite .backup → integrity_check → schema validation
- Atomic publish (.tmp → mv) + atomic metadata (.tmp → mv)
- Published snapshot: uid=0, gid=10010, mode=440
- Metadata SHA-256 matches actual snapshot SHA-256
- Hermes reads via SQLite mode=ro&immutable=1
- Hermes write denied (filesystem + SQLite)
- flock -n concurrency (exit 10 = genuine contention only)
- lock-open failure → exit 2 (infrastructure failure, not SKIPPED)
- Failed refresh preserves old snapshot + old metadata
- systemd oneshot service + 15min timer
- SuccessExitStatus=10 correctly classifies lock contention as success
- Protected by ProtectSystem=strict with minimal ReadWritePaths

## Source Test Status

294 passed, 5 skipped, 0 failed — 298 collected

## Next Task

**B3 — Production Credentials**, pending Amjad action. Cannot proceed without production source access.