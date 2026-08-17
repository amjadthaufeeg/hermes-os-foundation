# Phase B — Updated Blocker Register

**Updated:** 2026-08-17  
**Status:** Local non-GATED blockers closed; VPS/GATED certification remains pending.

---

## Blocker Status

| ID | Blocker | Priority | Status |
|---|---|---|---|
| B1 / GAP-001 | Policy cross-validation | P0 | **CLOSED** — ec2d2cd, container proven |
| B2a | Snapshot refresh orchestrator (stub) | P0 | **CLOSED** — a7f9764, VPS runtime proven |
| FC-05 | Snapshot freshness/hash/path enforcement | P0/P1 | **CLOSED LOCALLY** — environment policy requires fresh metadata, SHA binding, approved snapshot prefix, and decision-read gate |
| B2b | Production source integration | P0 | **GATED** — requires VPS/source authorization |
| B3 | Production credentials/access | P0 | **GATED — REQUIRES AMJAD** |
| B4 | Production compose | P0 | **LOCAL CONFIG READY; GATED DEPLOY** — compose uses read-only snapshot and metadata mounts |
| B5 | Production fail-closed tests | P1 | **GATED** — requires B4 deployment |
| B6 | Production RPO baseline | P1 | **GATED** — requires B2b production snapshot runtime |
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

## Remaining GATED Work

Final production certification still requires Amjad approval for VPS/root actions:

- provision or verify production source access;
- run the final deployment helper;
- execute Docker/root/flock-backed fail-closed tests on Linux/VPS;
- measure production RPO/RTO;
- authorize the production read-only canary.
