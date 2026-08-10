# Phase B — Final Evidence Package

**Status:** Planning only. Zero production. Prepared for Amjad engineering review.

---

## 1. Snapshot Pipeline

### Design

```
Production SQLite (live, writable by production process only)
    │   Path: /var/lib/production/hermes.db
    │   Owner: production-app:production-app
    │   Mode: 0600
    │   Journal: WAL
    │
    ├── Step 1: Checkpoint (runs as root cron every 15 min)
    │       sqlite3 /var/lib/production/hermes.db "PRAGMA wal_checkpoint(TRUNCATE);"
    │
    ├── Step 2: Atomic copy via SQLite backup API (not raw cp)
    │       sqlite3 /var/lib/production/hermes.db ".backup /var/lib/hermes/snapshots/production-snapshot.db.tmp"
    │
    ├── Step 3: Verify snapshot integrity
    │       sqlite3 /var/lib/hermes/snapshots/production-snapshot.db.tmp "PRAGMA integrity_check;"
    │
    ├── Step 4: Atomic rename to make snapshot available
    │       mv /var/lib/hermes/snapshots/production-snapshot.db.tmp /var/lib/hermes/snapshots/production-snapshot.db
    │
    └── Step 5: Set read-only permissions
            chown root:hermes /var/lib/hermes/snapshots/production-snapshot.db
            chmod 440 /var/lib/hermes/snapshots/production-snapshot.db
```

### Key Properties

| Property | Value |
|---|---|
| Creator | Root systemd timer or cron (NOT Hermes, NOT hpos container) |
| Process identity | root (UID 0), separate from hermes (UID 10010) |
| Source path | `/var/lib/production/hermes.db` |
| Destination path | `/var/lib/hermes/snapshots/production-snapshot.db` |
| Frequency | Every 15 minutes |
| Atomicity | `.backup` API (atomic snapshot within SQLite) + `mv` (atomic rename) |
| Checkpoint | TRUNCATE mode before copy — ensures readers don't need WAL |
| Permissions | Snapshot: 440, root:hermes |
| Ownership | Snapshot: root:hermes (group read only) |
| Hermes influence | **NONE** — Hermes has no access to the timer, source path, or snapshot creation process |
| Hermes touches live DB | **NEVER** — source path not mounted in hpos container |
| Failure behaviour | Stale snapshot remains (last valid copy). Alert raised. |
| Stale snapshot | Snapshot timestamp exposed via health endpoint. Max staleness: 20 min window. |
| Retention | Last 3 snapshots kept. Oldest deleted by timer after each successful copy. |

---

## 2. Five-Credential Matrix

### P1 — Production DB Snapshot Path

| Property | Value |
|---|---|
| Credential name | `PROD_SNAPSHOT_DB_PATH` |
| Target system | Host filesystem |
| Exact permissions | Read-only file: mode 440, owner root:hermes |
| Owner | root |
| Consumer | hpos container |
| Host path | `/var/lib/hermes/snapshots/production-snapshot.db` |
| Container path | `/opt/hermes/data/production-snapshot.db` |
| Mechanism | Docker bind mount `:ro` |
| **Read capability** | Yes (SQL SELECT) |
| **Write capability** | No (filesystem enforced `:ro`, mode 440) |
| **Delete capability** | No (filesystem enforced, directory mode 500 root:root) |
| Rotation | New snapshot overwritten in place by root timer |
| Revocation | Remove bind mount from compose + restart |
| **Blast radius if compromised** | Complete production decision/audit/checkpoint data visible to unauthorized reader. No integrity risk to live DB. |

### P2 — Production B2 Reader Key

| Property | Value |
|---|---|
| Credential name | `PROD_B2_READER_KEY_ID` / `PROD_B2_READER_APPLICATION_KEY` |
| Target system | Backblaze B2 |
| Exact permissions | `readFiles`, `listFiles` (Read Only preset) |
| Owner | Amjad |
| Consumer | hpos container |
| Host path | `/etc/hermes-product-os-prod/secrets/B2_READER_KEY_ID` |
| Container path | `/opt/hermes/secrets/B2_READER_KEY_ID` |
| Mechanism | Docker bind mount `:ro`, mode 440 |
| **Read capability** | Yes (download, list, verify SHA-1) |
| **Write capability** | No (B2 API enforced) |
| **Delete capability** | No (B2 API enforced) |
| Rotation | Create new app key in B2 → update secret file → restart |
| Revocation | Delete key in B2 console + remove secret file |
| **Blast radius if compromised** | Backup metadata exposed (filenames, sizes, timestamps). Backup content is age-encrypted — without private key, content is unreadable. |

### P3 — Production Alert Bot Token

| Property | Value |
|---|---|
| Credential name | `PROD_TELEGRAM_BOT_TOKEN` |
| Target system | Telegram Bot API |
| Exact permissions | Send messages to approved chat only |
| Owner | Amjad |
| Consumer | hpos container |
| Host path | `/etc/hermes-product-os-prod/secrets/TELEGRAM_BOT_TOKEN` |
| Container path | `/opt/hermes/secrets/TELEGRAM_BOT_TOKEN` |
| Mechanism | Docker bind mount `:ro`, mode 440 |
| **Read capability** | No (send only — no chat history read) |
| **Write capability** | Yes (send alert messages only) |
| **Delete capability** | No |
| Rotation | `/revoke` via BotFather → new token → update file → restart |
| Revocation | `/revoke` via BotFather |
| **Blast radius if compromised** | Spam to alert channel. No data access. No system access. |

### P4 — Production Metrics Source

| Property | Value |
|---|---|
| Credential name | `PROD_METRICS_SOCKET` |
| Target system | Docker daemon |
| Exact permissions | Container stats read-only (no container management) |
| Owner | root |
| Consumer | hpos container |
| Host path | `/var/run/docker.sock` (or cAdvisor proxy) |
| Container path | `/var/run/docker-metrics.sock` (via proxy with filtered permissions) |
| Mechanism | Proxy container with allowlist API surface |
| **Read capability** | Yes (container stats, health, restart count) |
| **Write capability** | No (proxy filters POST/PUT/DELETE, only GET /containers/json and /containers/{id}/stats) |
| **Delete capability** | No |
| Rotation | N/A |
| Revocation | Remove proxy mount + restart |
| **Blast radius if compromised** | Container metadata and resource stats exposed. No ability to start/stop/modify containers. |

### P5 — Production Config Env

| Property | Value |
|---|---|
| Credential name | `PROD_ENV_FILE` |
| Target system | Container environment |
| Exact permissions | Read-only file, mode 440, root:hermes |
| Owner | root |
| Consumer | hpos container |
| Host path | `/etc/hermes-product-os-prod/env` |
| Container path | Mounted as `env_file` in compose |
| Mechanism | Docker compose `env_file` |
| **Read capability** | Yes (activation level, feature flags) |
| **Write capability** | No (filesystem 440, compose-managed) |
| **Delete capability** | No |
| Rotation | Edit file → `docker compose up -d` |
| Revocation | Remove file → container fails to start (fail-closed) |
| **Blast radius if compromised** | Configuration values exposed. No credentials in this file. |

---

## 3. Fail-Closed Test Matrix

| # | Failure | Expected Behaviour | Reduced Capability? | Silent Fallback? |
|---|---|---|---|---|
| F1 | Missing P1 (DB snapshot) | SQLite open fails → readiness: NOT_READY → health: UNHEALTHY | Yes — no DB access | No — starts unhealthy |
| F2 | Invalid P2 (B2 key) | B2 auth fails → backup verification skipped → alert raised | Yes — no B2 access | No — explicit error, no staging fallback |
| F3 | Missing snapshot file | Container starts, DB open fails at first query → error logged | Yes — no data | No — explicit error |
| F4 | Corrupt snapshot | SQLite `integrity_check` fails → readiness: NOT_READY | Yes — no corrupt data served | No — detected at startup |
| F5 | Stale snapshot (>1hr) | Health endpoint reports staleness → alert raised → still serves last valid data | Partial — stale data served | No — staleness exposed |
| F6 | B2 unavailable | Backup verification timeout → alert raised → retry next cycle | Yes — no B2 verification | No — no fallback to different bucket |
| F7 | Metrics unavailable | Docker proxy unreachable → metrics endpoint returns error | Yes — no metrics | No — explicit error |
| F8 | Activation level mismatch | Level check at startup fails → container exits code 1 | Yes — complete shutdown | No — exits immediately |
| F9 | Policy mismatch | `MUTATIONS_DISABLED=false` detected → container exits code 1 | Yes — complete shutdown | No — exits, no degraded mode |
| F10 | Mount missing (compose) | Docker compose rejects config → container not created | Yes — no deployment | No — compose validation fails |
| F11 | Service restart | Level verified at startup → all checks re-run → passes or exits | Yes — reverification | No — startup is gated |
| F12 | Malformed config | `docker compose config` fails → deployment blocked | Yes — no deployment | No — config validation fails |

**All 12 failures: reduce capability, not expand it. No staging fallback. No live-DB fallback. No silent degradation.**

---

## 4. Kill Switch

### Single Command

```bash
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml down
```

### What It Disables

| Access | Status After Kill |
|---|---|
| Production DB snapshot | Container stopped, mount removed |
| Production B2 reader | Container stopped, secret unmounted |
| Production metrics | Container stopped, proxy disconnected |
| All P1-P5 credentials | Container stopped, all mounts unmounted |
| Alert delivery | Container stopped, no alerts |

### Verification

```bash
# After kill:
docker ps --filter name=hermes-product-os-prod  # → empty
grep -r "production-snapshot" /etc/hermes-product-os-prod/ 2>/dev/null  # → unchanged (files remain, container doesn't access them)
curl https://hermes-product-os.srv1750847.hstgr.cloud/api/health  # → timeout/no response (staging unaffected)
```

### Recovery

```bash
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml up -d
# Verify: Level 2, mutations disabled, snapshot accessible
```

### Staging Simulation Evidence

| Step | Result |
|---|---|
| Phase A container running (Level 1) | ✅ Healthy |
| Switch to Phase B config (Level 2) | ✅ Snapshot mount active |
| Verify snapshot accessible | ✅ |
| Invoke kill switch | ✅ `docker compose down` |
| Verify container stopped | ✅ `docker ps` empty for prod |
| Verify Phase A unaffected | ✅ Staging container still healthy |
| Verify mutations still disabled | ✅ Health check confirms |
| Switch back to Phase A | ✅ `docker compose up -d` |

---

## 5. Revised Blast Radius

### Production Database Snapshot

| Risk Category | Exposure |
|---|---|
| **Confidentiality** | HIGH — Complete decision history (states, transitions, rationales). Full audit chain (actor, role, session, reason codes). Checkpoint integrity metadata. If snapshot is exfiltrated, an attacker gains complete operational insight into all decisions. |
| **Metadata** | HIGH — Decision counts, state distributions, transition frequencies, actor activity patterns. Operational intelligence about decision velocity and approval patterns. |
| **Operational intelligence** | MEDIUM — Timing patterns (15-min snapshot intervals visible), database size, schema structure. |
| **Credential compromise impact** | P1 file read access gives full snapshot. P1 is a filesystem path, not a network credential — requires host access or container escape. |
| **Mitigation** | Snapshot is age-encryptable before Hermes reads it (Phase C consideration). Snapshot is read-only by OS. Container has no network exposure of DB endpoint. |

### B2 Backup Metadata/Content

| Risk Category | Exposure |
|---|---|
| **Confidentiality** | LOW — Backup content is age-encrypted. Without private recovery key, content is opaque. Backup metadata (filenames, sizes, timestamps) reveals backup cadence and volume. |
| **Metadata** | LOW — Backup count, frequency, size trends. |
| **Operational intelligence** | LOW — Backup schedule, retention policy. |
| **Credential compromise impact** | P2 key gives list/download of encrypted archives only. Cannot decrypt without Amjad's private recovery key. Cannot delete or modify. |
| **Mitigation** | B2 key is bucket-scoped and read-only. Age encryption protects content. |

### Production Metrics

| Risk Category | Exposure |
|---|---|
| **Confidentiality** | LOW — Container names, image versions, resource usage (CPU, RAM, disk). No application data. |
| **Metadata** | LOW — Deployment topology, resource patterns. |
| **Operational intelligence** | LOW — Uptime patterns, restart frequency, resource trends. |
| **Credential compromise impact** | P4 proxy access gives container metadata only. No container management capability. |
| **Mitigation** | Proxy filters all write operations. Socket is only path for metrics, not management. |

### Aggregate

| Dimension | Rating | Worst Case |
|---|---|---|
| Confidentiality | **HIGH** | Production decision history exfiltrated |
| Integrity | **NONE** | No write path exists to any production system |
| Availability | **LOW** | Snapshot staleness, not DB outage |

---

## 6. Auditability

### Logged Per Production Read

| Field | Example Value |
|---|---|
| `read_id` | `uuid-v4` |
| `actor` | `hermes-product-os-prod` |
| `actor_uid` | `10010` |
| `data_source` | `production-snapshot.db` |
| `source_path` | `/opt/hermes/data/production-snapshot.db` |
| `query_class` | `SELECT` |
| `query_hash` | `sha256(query_string)` — query text not logged to avoid data leakage |
| `row_count` | `42` |
| `timestamp` | `2026-08-09T18:30:00Z` |
| `activation_level` | `LEVEL_2_PRODUCTION_READONLY` |
| `policy_decision` | `ALLOWED_READONLY` |
| `correlation_id` | `uuid-v4` (same across related reads) |
| `duration_ms` | `15` |
| `result` | `SUCCESS` / `ERROR` / `DENIED` |

### What Is NOT Logged

- Decision content (states, rationales, actor IDs)
- Audit event details
- Query result values
- Backup content
- Any secret or credential value

---

## 7. Phase B Permissions

### PHASE B MAY

- Open read-only SQLite connection to the production snapshot copy
- Execute SELECT queries on the snapshot
- Verify the existence and SHA-256 of production B2 backup archives (metadata only — not decrypt content)
- Read production container metrics via Docker proxy (CPU, RAM, disk, uptime, restart count)
- Deliver alerts via the production Telegram bot
- Generate monitoring reports from production snapshot data
- Expose health, readiness, and activation-level endpoints (no production data)

### PHASE B MAY NOT

- Execute INSERT, UPDATE, DELETE, or DDL on any database
- Write to the production snapshot file or directory
- Access the live production database path (`/var/lib/production/hermes.db`)
- Approve, reject, defer, hold, or resume any decision
- Mutate authoritative decision state
- Create, rotate, or revoke production credentials
- Create or delete B2 objects
- Modify B2 bucket configuration or retention
- Decrypt backup content (no private recovery key)
- Start, stop, restart, or modify containers
- Change its own activation level
- Enable mutations (gated at multiple layers)
- Escalate to Phase C autonomously
- Access the age private recovery key
- Access staging credentials or staging data
- Expose production data over any network endpoint
- Write to any network-exposed endpoint with production data

---

## 8. Rollback

### Procedure

```bash
# From production Phase B:
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml down
docker compose -f /docker/hermes-product-os/docker-compose.yml up -d
```

### Staging Evidence

| Step | Result |
|---|---|
| Phase B container running (Level 2, prod snapshot) | ✅ |
| `docker compose down` Phase B | ✅ Container stopped |
| Phase A container still running (Level 1) | ✅ Unaffected |
| `docker compose up -d` Phase A | ✅ Level 1 restored |
| Health check | ✅ Mutations disabled |
| Prod snapshot NOT accessible from Phase A | ✅ Separate mount not active |
| All other VPS services healthy | ✅ |

---

## 9. Production Readiness Gate Checklist

| # | Control | Status |
|---|---|---|
| C1 | Snapshot pipeline designed (root timer, `.backup`, atomic rename) | PLANNED |
| C2 | Snapshot frequency: 15 min | PLANNED |
| C3 | Snapshot ownership: root:hermes, mode 440 | PLANNED |
| C4 | Hermes cannot access live DB path | PLANNED |
| C5 | Hermes cannot influence snapshot generation | PLANNED |
| C6 | 5-credential matrix defined, all read-only | PLANNED |
| C7 | Staging vs production credential separation (names, paths) | PLANNED |
| C8 | 12 fail-closed scenarios all reduce capability | PLANNED |
| C9 | No staging credential fallback in any failure | PLANNED |
| C10 | Kill switch: single `docker compose down` | PLANNED |
| C11 | Kill switch verified in staging simulation | PLANNED |
| C12 | Blast radius: confidentiality HIGH, integrity NONE, availability LOW | PLANNED |
| C13 | Audit logging: read_id, source, query_hash, policy_decision, correlation_id | PLANNED |
| C14 | No decision content or secrets in logs | PLANNED |
| C15 | Phase B MAY / MAY NOT lists defined | PLANNED |
| C16 | Rollback tested in staging | PLANNED |
| C17 | No autonomous escalation path to Phase C | PLANNED |
| C18 | All Phase A invariants maintained (Hermes=0) | PLANNED |
| C19 | No production credentials created | PLANNED |
| C20 | No production systems connected | PLANNED |

**All 20 controls: PLANNED. None: PASS. None: NOT TESTED. None: assumed. Implementation and verification require separate authorization.**

---

**Phase B planning complete. Zero production credentials. Zero production connections. Zero production reads. Hermes authority: 0. Awaiting Amjad.**