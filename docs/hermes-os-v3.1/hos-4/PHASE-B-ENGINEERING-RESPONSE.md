# Phase B — Engineering Review Response

**Response to:** Phase B engineering review  
**Status:** Planning only. No production credentials, connections, or reads.

---

## 1. SQLite Production Access — Critical Architecture Revision

### Problem Identified

Research confirms my original proposal (direct read-only mount of live SQLite) is **architecturally unsound**:

| Risk | Details |
|---|---|
| WAL mode conflicts | SQLite in WAL mode requires write access to `-wal`/`-shm` files even for *readers*. A read-only mount will produce `SQLITE_READONLY` errors on WAL checkpoint operations. |
| Stale reads | A reader connecting via mode=ro after a writer has committed may see stale state if WAL has uncheckpointed pages. `PRAGMA query_only` from a read-only mount cannot trigger checkpoint. |
| Shared-memory (`-shm`) | The `-shm` index requires `mmap` with `PROT_WRITE`. Read-only filesystem denies this. SQLite falls back to a non-shm mode with reduced performance/correctness. |
| Lock contention | If the writer holds a RESERVED lock and the reader needs SHARED, the read-only mount may not be able to acquire it cleanly. |
| Journal mode | If journal_mode=WAL (production standard), a read-only opener without `-wal` access produces errors or silently degrades. |

### Revised Architecture Recommendation

**Do NOT mount the live production SQLite file directly.**

Instead:

```
Production SQLite (writer owns)
  → Periodic WAL checkpoint + SQLite `.dump` or `.backup` snapshot
  → Copy to a read-only Hermes staging directory
  → Hermes opens the snapshot (not the live database)
```

Implementation:

```bash
# Run by root cron or systemd timer, NOT Hermes:
sqlite3 /path/to/production.db "PRAGMA wal_checkpoint(TRUNCATE);"
cp /path/to/production.db /var/lib/hermes/snapshots/production-snapshot.db
chmod 400 /var/lib/hermes/snapshots/production-snapshot.db
```

Then mount `/var/lib/hermes/snapshots/` into Hermes as read-only. Hermes opens the snapshot with `mode=ro`. The snapshot is immutable between copy intervals. Hermes cannot affect the live database.

**Snapshots are produced by a non-Hermes process (root cron or systemd timer). Hermes never touches the live database path.**

### Comparison

| Approach | Live DB Risk | Hermes Can Write | Correctness |
|---|---|---|---|
| Direct ro mount | HIGH (WAL conflicts) | No (hardware enforced) | Possible stale/incomplete reads |
| **Snapshot/replica** (recommended) | NONE (separate file) | No | Point-in-time consistent |

**Recommendation:** Snapshot/replica architecture. Reject direct live mount.

---

## 2. Read-Only Enforcement — Six Layers

For every production data source, the following layers apply. A failure of any single layer leaves the others intact.

### Production SQLite Snapshot

| Layer | Enforcement | Failure Mode |
|---|---|---|
| **L1: Credential** | File owner=root, mode=400, group=hermes (read-only) | Cannot open for write at OS level |
| **L2: Filesystem** | Container mount `:ro`, host directory mode 500 | Kernel denies O_RDWR open |
| **L3: Database** | SQLite `?mode=ro` on connection string | SQLite rejects INSERT/UPDATE/DELETE with SQLITE_READONLY |
| **L4: Application** | `MUTATIONS_DISABLED=true` gates all mutation paths | Mutation calls return 403 before touching DB |
| **L5: Activation** | `LEVEL_2_PRODUCTION_READONLY` disables all write code paths | Write functions are no-ops at Level 2 |
| **L6: Runtime verification** | Health endpoint validates `mutations=DISABLED` and `level=2` | Monitoring detects any deviation |

### Production B2 Backups (Reader Key Only)

| Layer | Enforcement |
|---|---|
| L1: Credential | B2 reader key: `readFiles`, `listFiles` only. No write/delete. |
| L2: Network | B2 API auth rejects writes at the B2 service layer |
| L3: Application | No upload/delete code paths at Level 2 |
| L4-L6: Application + Activation + Runtime | Same as SQLite layers |

### Production Metrics (system-level read-only)

| Layer | Enforcement |
|---|---|
| L1: Credential | Docker stats API (read-only), host metrics via `/proc` (ro) |
| L2: Filesystem | `/proc` and `/sys` are kernel-enforced read-only |
| L3: Application | No write paths to system metrics |

---

## 3. Production Credential Matrix

| # | Credential | System | Permissions | Owner | Consumer | Mechanism | Rotate | Revoke | Hermes Write? | Blast Radius |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | Prod DB snapshot path | Host filesystem | Read-only (400) | root | hpos container | Bind mount `:ro` | New snapshot path + compose update | Remove mount + restart | **No** | DB content observation only |
| P2 | Prod B2 reader key | Backblaze B2 | `readFiles`, `listFiles` | Amjad | hpos container | Secret file mount `:ro` | New B2 key + update secret file | Delete key in B2 console | **No** | Backup metadata exposure |
| P3 | Prod alert bot token | Telegram | Send messages only | Amjad | hpos container | Secret file mount `:ro` | New bot token + update | Revoke in BotFather | **No** | Alert channel spam |
| P4 | Prod metrics source | Docker socket or cAdvisor | Read-only query | root | hpos container | Docker stats API (ro) | N/A | Remove socket access | **No** | Container metadata exposure |
| P5 | Proxy/admin token | Hermes Product OS internal | None — disabled at Level 2 | N/A | None | Not generated | N/A | N/A | **No** | N/A |

---

## 4. Revised Blast Radius

| Data Source | Confidentiality Exposure | Integrity Risk | Availability Risk |
|---|---|---|---|
| Production DB snapshot | **HIGH**: All decision/audit/checkpoint data visible if snapshot exfiltrated | **NONE**: Snapshot is a copy, not the live DB | **LOW**: Snapshot stale but DB unaffected |
| Production B2 backups | **MEDIUM**: Backup metadata (filenames, sizes, timestamps) visible | **NONE**: Reader cannot modify | **LOW**: B2 outage unrelated to Hermes |
| Production metrics | **LOW**: Container stats, host metrics (CPU, RAM, disk) | **NONE**: Read-only by kernel | **LOW**: Independent of Hermes |

**Revised blast radius:** Confidentiality of production decision data if snapshot is exfiltrated. No integrity or availability risk to production systems.

---

## 5. Kill Switch — Revised Design

**Single command fail-closed:**

```bash
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml down
```

This:
1. Stops the hpos container (all production DB, B2, metrics access severed)
2. Removes the container (credentials unmounted)
3. Leaves no running Hermes process with production access

**Recovery:**
```bash
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml up -d
# Verify Level 2 restored, mutations disabled
```

**Verification after kill:**
- `docker ps --filter name=hermes-product-os` → empty
- No process accessing production snapshot path
- No process holding B2 reader key
- All other VPS services unaffected

---

## 6. Fail-Closed Behavior — Proof Matrix

| Failure | Behavior | Falls Back? |
|---|---|---|
| Missing P1 (DB snapshot path) | Container fails to start. Health: DOWN | **No** — Container won't start without mount |
| Invalid P2 (B2 key) | B2 auth fails. Backup verification skipped. Alert raised. | **No** — Separate secret file, no staging fallback |
| Bad mount | Docker compose rejects config. Container not recreated. | **No** — Explicit mount paths, no wildcards |
| DB unavailable | Snapshot missing → SQLite open fails → readiness: NOT_READY | **No** — No default/fallback path |
| Metrics unavailable | Docker socket missing → metrics endpoint returns error | **No** — No read of unrelated data |
| B2 unavailable | Backup verification times out → alert raised | **No** — No staging B2 fallback |
| Policy mismatch | Activation level check fails → mutations=DISABLED stays true | **No** — Level enforced at startup |
| Activation mismatch | Level check fails → container exits at startup | **No** — Exit code 1, no recovery loop |

---

## 7. Production vs Staging Separation

| Property | Staging (Phase A) | Production (Phase B) |
|---|---|---|
| Compose file | `docker-compose.yml` | `docker-compose.prod.yml` |
| Project name | `hermes-product-os` | `hermes-product-os-prod` |
| Container name | `hermes-product-os` | `hermes-product-os-prod` |
| B2 secrets path | `/etc/hermes-product-os/secrets/B2_*` | `/etc/hermes-product-os-prod/secrets/B2_*` |
| DB snapshot path | `/opt/hermes/data/staging.db` | `/var/lib/hermes/snapshots/production-snapshot.db` |
| Activation level | `LEVEL_1_PRIVATE_VPS_STAGING` | `LEVEL_2_PRODUCTION_READONLY` |
| Audit label | `environment: staging` | `environment: production` |

No path, credential, or container name reused between environments.

---

## 8. Auditability

Every production read logged with:

| Field | Value |
|---|---|
| initiator | `hermes-product-os-prod`, PID, UID |
| data_source | `production-snapshot.db`, `b2:prod-bucket`, `docker-metrics` |
| query_type | `SELECT`, `B2_LIST`, `METRICS_POLL` |
| timestamp | ISO 8601 UTC |
| activation_level | `LEVEL_2` |
| correlation_id | UUID per read session |
| policy_decision | `ALLOWED_READONLY` or `DENIED_WRITE_ATTEMPT` |

No decision values, backup content, or secret metadata in logs. Redaction enforced at log emission.

---

## 9. Rollback / Disable Exercise (Required Before Activation)

Before production access, run in staging:

1. Start Phase B config with simulated production snapshot
2. Verify Level 2, mutations disabled, read-only enforced
3. Verify snapshot data accessible
4. Invoke kill switch: `docker compose down`
5. Verify container stopped, no mounts active
6. Verify staging Phase A config unaffected
7. Switch back to Phase A: `docker compose up -d`
8. Verify Level 1 restored, mutations disabled

---

## 10. Phase B Authorization Package

### A. Architecture

```
Root cron/systemd timer (runs as root, NOT Hermes)
  ├── sqlite3 production.db "PRAGMA wal_checkpoint(TRUNCATE);"
  ├── cp production.db /var/lib/hermes/snapshots/production-snapshot.db
  └── chmod 400 /var/lib/hermes/snapshots/production-snapshot.db

Hermes Product OS container (Level 2)
  ├── /var/lib/hermes/snapshots/ (ro mount) → SQLite mode=ro
  ├── B2 reader key (ro secret mount) → backup verification
  ├── Docker metrics API (ro) → system health
  └── Telegram bot (alert delivery)

Production database (NOT mounted)
  └── Only the writer touches the live DB
```

### B. Read-Only Enforcement Matrix

See Section 2 above — 6 layers per data source.

### C. Credential Matrix

See Section 3 above — 5 credentials, all read-only.

### D. SQLite Safety Decision

**Snapshot/replica architecture.** Reject direct live mount. See Section 1 above.

### E. Blast Radius

Confidentiality of DB snapshot if exfiltrated. No integrity/availability risk. See Section 4.

### F. Kill Switch

Single `docker compose down`. See Section 5.

### G. Fail-Closed Tests

8 failure scenarios, all fail closed. See Section 6.

### H. Rollback Evidence

Required before activation. See Section 9.

### I. Phase B Permissions

- Read production DB snapshot
- Verify production B2 backup integrity
- Monitor production metrics
- Deliver production alerts
- Generate production reports

### J. Phase B Prohibitions

- NO production writes (INSERT/UPDATE/DELETE/DDL)
- NO decision approval/rejection
- NO production backup creation
- NO production backup deletion
- NO production key generation
- NO production credential modification
- NO live database mount
- NO network exposure of production data

### K. Irreversible Actions

**NONE.** All Phase B actions are read-only. The snapshot can be deleted and regenerated. B2 reader can be revoked. Kill switch is reversible within one compose cycle.

### L. Amjad Authorization Gates

| Gate | Required For |
|---|---|
| Phase B plan approval | Proceed to implementation |
| Snapshot timer installation | Start copying production data |
| Production B2 reader key creation | Access production backups |
| Production alert bot token | Real alert delivery |
| Phase B activation (Level 2) | Go live with production reads |

---

**All production credentials: 0. All production connections: 0. All production reads: 0. Hermes authority: 0.**

*This plan rejects direct live database mounting. Snapshots only. Hermes never touches the live DB path.*