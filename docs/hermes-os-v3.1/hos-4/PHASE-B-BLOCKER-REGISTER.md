# Phase B — Updated Blocker Register

**Updated:** 2026-08-17  
**Status:** HOS foundation closure certified on VPS at `25b67c86051e9df989820a16086fce097ea53861`.

---

## Blocker Status

| ID | Blocker | Priority | Status |
|---|---|---|---|
| B1 / GAP-001 | Policy cross-validation | P0 | **CLOSED** — ec2d2cd, container proven |
| B2a | Snapshot refresh orchestrator (stub) | P0 | **CLOSED** — a7f9764, VPS runtime proven |
| FC-05 | Snapshot freshness/hash/path enforcement | P0/P1 | **CLOSED + VPS CERTIFIED** — environment policy requires fresh metadata, SHA binding, approved snapshot prefix, and decision-read gate |
| B2b | Production source integration | P0 | **FUTURE ACTIVATION GATE** — requires Amjad-controlled production source authorization |
| B3 | Production credentials/access | P0 | **FUTURE ACTIVATION GATE** — requires Amjad-controlled credentials/access |
| B4 | Production compose | P0 | **CONFIG READY; ACTIVATION GATED** — compose uses read-only snapshot and metadata mounts |
| B5 | Production fail-closed tests | P1 | **FOUNDATION CERTIFIED** — VPS combined regression passed |
| B6 | Production RPO baseline | P1 | **FOUNDATION CERTIFIED** — B6 suite passed in final regression |
| B7 | Canary authorization | P0 | **FUTURE ACTIVATION GATE** — requires separate Amjad authorization |

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

## Remaining Activation Work

HOS foundation closure is certified. Future production activation/canary work remains separate and requires explicit Amjad authorization:

- provision or verify production source access;
- measure production RPO/RTO;
- authorize the production read-only canary.

## Final Closure Evidence

- Final certified SHA: `25b67c86051e9df989820a16086fce097ea53861`
- HOS-AUTO backend certification: `GPT-HOS-RC-VPS-CERT-010` — PASS
- HOS-AUTO combined VPS regression: `GPT-HOS-FINAL-COMBINED-VPS-RA-001` — PASS
- VPS totals: `421 passed, 2 skipped, 9 warnings`
