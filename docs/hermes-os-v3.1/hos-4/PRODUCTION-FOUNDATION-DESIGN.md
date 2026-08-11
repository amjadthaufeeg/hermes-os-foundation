# Production Deployment Foundation Design

**Design only. No execution. Phase B — pre-canary.**

---

## 1. Production Environment Boundary

| Property | Production | Staging | Test-B |
|---|---|---|---|
| Docker project | `hermes-product-os-prod` | `hermes-product-os` | `hpos-test-b` |
| Container name | `hermes-product-os-prod` | `hermes-product-os` | `hermes-product-os-test-b` |
| Network | `hermes-product-os-prod-net` | `hermes-product-os-net` | `hpos-test-b-net` |
| Data volume | `hpos-prod-data` | `hpos-data` | `hpos-test-b-data` |
| Backup volume | `hpos-prod-backup` | `hpos-backup` | (N/A) |
| Logs volume | `hpos-prod-logs` | `hpos-logs` | (N/A) |
| Secret namespace | `/etc/hermes-product-os-prod/secrets/` | `/etc/hermes-product-os/secrets/` | `/etc/hermes-product-os-test-b/secrets/` |
| Compose file | `/docker/hermes-product-os-prod/docker-compose.yml` | `/docker/hermes-product-os/docker-compose.yml` | `/docker/hermes-product-os/docker-compose.test-b.yml` |
| Image | `hermes-product-os-hpos:prod-<sha>` | `hermes-product-os-hpos@sha256:7bbc4894...` | Task-specific tag |

### Structural Isolation Guarantees

- Separate Docker project — no shared volume/network namespace
- Separate secret directory — no credential leakage
- Distinct image tag — staging promotion requires explicit retag
- No resource overlap with staging or Test-B

---

## 2. Authoritative Database Design

| Property | Value |
|---|---|
| Technology | SQLite 3 |
| Container path | `/opt/hermes/data/production.db` |
| Persistence | Docker named volume: `hpos-prod-data` |
| Host path | `/var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/production.db` |
| Owner:Group | 10010:10010 (hermes runtime) |
| Mode | 640 (rw for owner, r for group) |
| Journal mode | WAL (default for production persistence) |
| Schema init | `init_db()` at container startup |
| Migration | Schema version table: `schema_version` |
| Backup compat | `sqlite3 .backup` — works with WAL |
| Crash recovery | WAL auto-checkpoint on next open |
| Rollback | Volume persisted; compose down → up restores |

### Why SQLite + Named Volume

- Single-file database — trivial to snapshot via `.backup`
- Named volume survives container recreation, image replacement, service restart
- Root access to host mountpoint for snapshot service (read-only)
- Hermes container owns the DB (10010:10010), snapshot service reads from host side (root)
- No network dependency — self-contained

---

## 3. Authority Model

| Question | Answer |
|---|---|
| Who owns authoritative state? | Production container (hermes, 10010) |
| Who may read? | Hermes container, snapshot service (root, host-side) |
| Who may mutate? | **Currently: NO ONE** (MUTATIONS_DISABLED=true, policy=false) |
| Write authorization model | Requires: policy change + env var change + Amjad authorization |
| Accidental write prevention | GAP-001: policy cross-validation prevents MUTATIONS_DISABLED=false from enabling writes in PRODUCTION env |

### Write-Enablement Gate (Future)

```
PRODUCTION writes enabled ONLY when:
  POLICY[PRODUCTION]["mutations"] == True    ← policy change (requires code push + review)
  AND MUTATIONS_DISABLED == false            ← env var (requires compose change)
  AND Amjad authorizes                       ← human gate
```

Currently: POLICY says `mutations: False`. Even `MUTATIONS_DISABLED=false` would be overridden (GAP-001).

---

## 4. Database Initialization

### Procedure

```bash
# P2: Create volume (automatic on first compose up)
# P3: Initialize schema on first container start

# Container startup sequence:
# 1. import backend.hos4c.database
# 2. init_db(path="/opt/hermes/data/production.db")
# 3. Schema created: decisions, audit_events, sessions, idempotency_records
# 4. schema_version table inserted with version=1
# 5. No seed data — starts empty (or seeded from approved migration)
```

### Schema Source

- `backend/hos4c/database.py` SCHEMA constant
- Tables: `decisions`, `audit_events`, `sessions`, `idempotency_records`
- Plus: `schema_version` table for migration tracking

### Seed Data

- **Empty start.** No simulation data. No staging decisions imported.
- First production decisions should be created through the API after write authorization (Phase C)
- If seed data is required: approved decision registry, not staging migration

### Verification

```bash
sqlite3 <production.db> "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
# Expected: audit_events, decisions, idempotency_records, schema_version, sessions

sqlite3 <production.db> "PRAGMA integrity_check;"
# Expected: ok

sqlite3 <production.db> "SELECT COUNT(*) FROM decisions;"
# Expected: 0 (empty, awaiting authorized population)
```

---

## 5. Persistence Guarantees

| Event | Database survives? | How |
|---|---|---|
| Container recreation | YES | Named volume persists |
| Image replacement | YES | Named volume independent of image |
| Service restart | YES | Named volume independent of container lifecycle |
| Host reboot | YES | Volume on persistent storage |
| `docker compose down` | YES | Named volume not pruned by default |
| `docker compose down -v` | **NO** | Guard with backup before prune |
| Snapshot refresh failure | YES | Old snapshot preserved (TASK-002 property) |
| Hermes write attempt | N/A | Mutations disabled, write denied at app layer |

### Snapshot Service Access

```
Root (host) → sqlite3 ".backup" reads production.db
  → writes snapshot.db to SNAPSHOT_DIR
  → chown root:10010, chmod 440
  → Hermes container mounts snapshot.db :ro
```

- Root reads production.db via host path (read-only SQLite API)
- Hermes NEVER directly accesses production.db
- Hermes reads only the published snapshot via :ro bind mount

---

## 6. Production Source Path

### Path Derivation

```
Container path:  /opt/hermes/data/production.db
Volume:          hpos-prod-data
Volume mountpoint: /var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/
                    ↑ Docker project name                    ↑ Volume name

Host path:       /var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/production.db
```

### PRODUCTION_DB_PATH

```
PRODUCTION_DB_PATH=/var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/production.db
```

### Verification After Provisioning

```bash
# After P2-P4:
test -f "$PRODUCTION_DB_PATH" && echo "EXISTS" || echo "MISSING"
stat -c '%a %U:%G' "$PRODUCTION_DB_PATH"
# Expected: 640 10010:10010

sqlite3 "$PRODUCTION_DB_PATH" "PRAGMA integrity_check;"
# Expected: ok

sqlite3 "$PRODUCTION_DB_PATH" ".tables"
# Expected: audit_events  decisions  idempotency_records  schema_version  sessions
```

---

## 7. Network Isolation

| Property | Production |
|---|---|
| Network name | `hermes-product-os-prod-net` |
| Internal-only | YES — no external outbound by default |
| Staging access | NO — separate network |
| Test-B access | NO — separate network |
| Reverse proxy | Traefik (shared instance, separate router rule) |
| Container port | 8080 (internal) |
| Host port | NONE — Traefik reverse proxy only |
| Database exposure | NONE — only via container filesystem |

### Traefik Integration

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.hermes-prod.rule=Host(`hermes-prod.srv1750847.hstgr.cloud`)"
  - "traefik.http.routers.hermes-prod.entrypoints=websecure"
  - "traefik.http.routers.hermes-prod.tls.certresolver=letsencrypt"
  - "traefik.http.routers.hermes-prod.middlewares=hpos-prod-basic-auth"
  - "traefik.http.middlewares.hpos-prod-basic-auth.basicauth.users=<separate-credentials>"
```

Separate Basic Auth credentials from staging.

---

## 8. Secret Model

### Directory Structure

```
/etc/hermes-product-os-prod/secrets/
├── PRODUCTION_DB_PATH          # 400 root:root — deferred until DB exists
├── B2_WRITER_KEY_ID            # 400 root:root — deferred (Phase C)
├── B2_WRITER_APPLICATION_KEY   # 400 root:root — deferred (Phase C)
└── (future expansion)
```

### Required Now

| File | Purpose | Required? |
|---|---|---|
| `PRODUCTION_DB_PATH` | Single line: absolute path to production.db | YES (after P5) |

### Deferred

| File | Purpose | Required For |
|---|---|---|
| `B2_WRITER_KEY_ID` | Production B2 writes | Phase C |
| `B2_WRITER_APPLICATION_KEY` | Production B2 writes | Phase C |
| `B2_READER_KEY_ID` | Backup verification | Post-Phase B |

### Mount Policy

- `PRODUCTION_DB_PATH` is read by the snapshot service (root, host-side)
- NOT mounted into Hermes container
- Staging and Test-B have NO access to `/etc/hermes-product-os-prod/`

---

## 9. Image / Release Model

| Property | Value |
|---|---|
| Source branch | `main` or `release/production-v1` |
| Image name | `hermes-product-os-hpos` |
| Production tag | `prod-<short-sha>` (immutable) |
| Build | `docker build -t hermes-product-os-hpos:prod-<sha> .` |
| Digest pinning | `image: hermes-product-os-hpos@sha256:<digest>` (preferred) |
| Rollback | Pin previous digest in compose |
| Verification | GAP-001 tests on image before production deployment |

### Production vs Staging Image

| Property | Staging | Production |
|---|---|---|
| Image | `hermes-product-os-hpos@sha256:7bbc...` | `hermes-product-os-hpos@sha256:<different>` |
| HERMES_ENVIRONMENT | LOCAL_SIMULATION | PRODUCTION |
| MUTATIONS_DISABLED | true | true |
| Decisions source | Hardcoded SIM_DECISIONS | SQLite production.db |
| Network | `hermes-product-os-net` | `hermes-product-os-prod-net` |

---

## 10. Read-Only Initial Production Mode

```yaml
environment:
  - HERMES_ENVIRONMENT=PRODUCTION
  - MUTATIONS_DISABLED=true
  - DATABASE_PATH=/opt/hermes/data/production.db
```

### GAP-001 Enforcement

```
POLICY[PRODUCTION] = {"mutations": False, ...}

If someone sets MUTATIONS_DISABLED=false:
  → mutations_disabled() cross-checks POLICY
  → Overrides to True (mutations remain disabled)
  → validate_startup() reports FATAL conflict
  → lifespan exits container startup
```

No path to production writes exists without changing POLICY + env var + Amjad authorization.

---

## 11. Health / Readiness

| Check | Endpoint / Command |
|---|---|
| Process alive | `GET /api/health` → `{"status": "alive"}` |
| Environment | Health shows `"environment": "PRODUCTION"` |
| Mutations disabled | Health shows `"mutations": "DISABLED"` |
| DB accessible | `sqlite3 production.db "SELECT 1"` |
| DB integrity | `PRAGMA integrity_check` → ok |
| Schema version | `SELECT version FROM schema_version ORDER BY version DESC LIMIT 1` |
| No staging credentials | No `/etc/hermes-product-os/secrets/` in container |
| No Test-B credentials | No `/etc/hermes-product-os-test-b/secrets/` in container |
| Image identity | `docker inspect --format '{{.Image}}'` |
| Network identity | `docker inspect --format '{{.NetworkSettings.Networks}}'` |

---

## 12. Observability (Phase B Only)

| Item | Mechanism |
|---|---|
| Container logs | Docker → journald |
| Snapshot service logs | systemd journal |
| Health endpoint | `/api/health` |
| Readiness endpoint | `/api/health/readiness` |
| Metrics | Deferred to Phase C |

No external monitoring, alerting, or dashboard integration for Phase B foundation.

---

## 13. Rollback

| Scenario | Rollback |
|---|---|
| Bad image | Revert compose to previous digest, `docker compose up -d` |
| Bad compose | Restore from backup, `docker compose up -d` |
| Bad DB init | `docker compose down`, delete volume, recreate |
| Bad env config | Fix env var, restart |
| Failed startup | Fix issue, restart |
| Snapshot failure | Old snapshot preserved (TASK-002), fix source/path |

### Production DB Preservation

```bash
# Before any volume-destroying operation:
sqlite3 "$PRODUCTION_DB_PATH" ".backup /var/lib/hermes/snapshots/production-pre-rollback.db"
```

---

## 14. Provisioning Order

```
P0 — THIS DESIGN (approved)
P1 — Create production namespace + directories
     mkdir -p /docker/hermes-product-os-prod
     mkdir -p /etc/hermes-product-os-prod/secrets
P2 — Create Docker volumes (auto on first compose up)
     Named volumes: hpos-prod-data, hpos-prod-backup, hpos-prod-logs
P3 — Write production compose file
     docker-compose.yml with correct image, env, volumes, network
P4 — Start production container
     docker compose up -d
P5 — Verify container health + DB initialization
     Decision count = 0, integrity = ok, environment = PRODUCTION
P6 — Establish PRODUCTION_DB_PATH secret
     echo "/var/lib/docker/volumes/hermes-product-os-prod_hpos-prod-data/_data/production.db" \
       > /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH
P7 — Complete B3 (credentials provisioned)
P8 — B2b: activate production source for snapshot service
     SOURCE_DB=$(cat /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH)
P9 — Verify snapshot pipeline with production source
     Snapshot created → integrity ok → published → Hermes reads
P10 — B4: production fail-closed tests
P11 — B5/B6: RPO/RTO baseline
P12 — B7: canary authorization
```

### Dependency Graph

```
P0 → P1 → P2 → P3 → P4 → P5 → P6(B3) → P8(B2b) → P9 → P10(B4) → P11(B5/B6) → P12(B7)
```

---

## 15. Safety Constraints (Reaffirmed)

- No production writes (MUTATIONS_DISABLED=true, POLICY mutations=False)
- No production canary until B7 authorization
- No B2 credentials in production foundation
- No staging data migration
- No Test-B data migration
- No activation without explicit Amjad authorization
- Hermes never accesses production.db directly (only via published snapshot)
- Snapshot service reads source read-only (`.backup` API)

---

## PASS/FAIL Criteria for Production Foundation

| # | Criterion |
|---|---|
| 1 | Production container starts and shows PRODUCTION environment |
| 2 | Mutations show DISABLED |
| 3 | Production DB created with correct schema |
| 4 | Decision count = 0 (empty, not seeded with simulation data) |
| 5 | Integrity check passes |
| 6 | Schema version table present |
| 7 | Network isolated from staging and Test-B |
| 8 | No staging credentials accessible |
| 9 | Container recreation preserves DB |
| 10 | Snapshot service can read production.db from host path |
| 11 | PRODUCTION_DB_PATH file exists with correct content |
| 12 | GAP-001 prevents MUTATIONS_DISABLED=false from enabling writes |

---

**Production Foundation Design complete. Awaiting Amjad review.**