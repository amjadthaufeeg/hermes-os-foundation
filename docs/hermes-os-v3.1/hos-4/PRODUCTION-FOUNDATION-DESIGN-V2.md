# Production Foundation Design V2

**Design only. No execution. Phase B — pre-canary.**

---

## 1. Precise Authority Model

| Dimension | Model | Detail |
|---|---|---|
| **Database authority** | `production.db` is the authoritative persistent datastore | Only persistent source of production decisions |
| **Filesystem read** | UID 10010 (hermes), root (snapshot service) | Hermes reads the published snapshot; root reads the source via `.backup` |
| **Filesystem write** | Root snapshot service only for snapshot publication; Hermes logs only | Hermes does not write the snapshot or authoritative source |
| **Application mutation authority** | **ZERO** during Phase B | `MUTATIONS_DISABLED=true`, `POLICY[PRODUCTION].mutations=false` |
| **Application write scope** | Sessions, idempotency records only (operational) | These are local state, not authoritative decisions |

### Why Hermes Does Not Mount the Snapshot RW

The release-candidate production compose mounts only the published snapshot and `snapshot.meta.json` into the container, both read-only. Snapshot freshness, path-prefix validation, metadata timestamp, and SHA binding are enforced before production decision reads. Operational logs use a separate writable log volume.

### Alternative: Separate Operational DB

**Evaluated:** Use a separate operational DB for sessions/idempotency while reading decisions from the immutable snapshot.

**Deferred:** Adds complexity (two databases, two connections, session cross-referencing). Current Phase B keeps authoritative mutations disabled and protects production reads through read-only mounts plus metadata/SHA validation.

**Future hardening:** Split operational session/idempotency storage from the read-only decisions snapshot connection and open the snapshot with `mode=ro&immutable=1`.

---

## 2. Volume/Path Discovery Process

```text
1. Snapshot service publishes `/var/lib/hermes/snapshots/snapshot.db`
   and `/var/lib/hermes/snapshots/snapshot.meta.json`.

2. Production compose bind-mounts those files into the container as read-only.

3. Runtime uses:
   `DATABASE_PATH=/opt/hermes/data/production.db`

4. Startup validates:
   - `DATABASE_PATH` resolves under `/opt/hermes/data`
   - snapshot file is a regular file
   - `snapshot.meta.json` exists and is parseable
   - metadata timestamp is within 990 seconds
   - metadata SHA matches the mounted snapshot

5. Decision read endpoints re-check freshness before serving data.
```

No direct live database mount is permitted in the Hermes container.

---

## 3. WAL + Snapshot Safety

### Why WAL

| Property | WAL | DELETE |
|---|---|---|
| Concurrent reads during writes | Yes | Blocked |
| `.backup` consistency | Point-in-time snapshot via WAL checkpoint | Works but blocks writers during backup |
| Crash recovery | Auto WAL replay | Simpler but slower |
| Production read pattern | Health checks + occasional reads | Same |
| Future write concurrency (Phase C) | Required | Blocked |

### Snapshot Service Safety

```
sqlite3 "$SOURCE_DB" ".backup $TMP"

.backup uses SQLite's online backup API which:
- Reads the database at a consistent point in time
- Does NOT copy raw .db, .db-wal, or .db-shm files
- Does NOT require checkpoint or truncate
- Works with WAL mode databases
- Is read-only: no writes to source
```

### Runtime Proof Required (after P5)

```bash
# Verify no WAL files copied
test ! -f "$SNAPSHOT_DIR/snapshot.db-wal" && echo "NO_WAL_LEAK"
test ! -f "$SNAPSHOT_DIR/snapshot.db-shm" && echo "NO_SHM_LEAK"

# Verify snapshot integrity independent of source
sqlite3 "$SNAPSHOT_DIR/snapshot.db" "PRAGMA integrity_check;"
# Expected: ok
```

---

## 4. Database Initialization Authority

### Init Mechanism: Dedicated one-shot migration script

```
Image: hermes-product-os-hpos:prod-<sha>
Run as: root (for volume write access)

Script: deploy/init-production-db
Behavior:
  1. Check if /opt/hermes/data/production.db exists
  2. If exists + has schema_version table → verify version, exit 0
  3. If exists + no schema_version → error, exit 2 (requires manual intervention)
  4. If not exists → create, run schema, insert schema_version=1
  5. chown 10010:10010 production.db
  6. chmod 640 production.db
```

### Implementation (conceptual)

```bash
#!/bin/bash
DB=/opt/hermes/data/production.db

if [ -f "$DB" ]; then
    version=$(sqlite3 "$DB" "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1;" 2>/dev/null)
    if [ -n "$version" ]; then
        echo "Database already initialized at version $version"
        exit 0
    else
        echo "ERROR: Database exists without schema_version table. Manual intervention required."
        exit 2
    fi
fi

python3 -c "
from backend.hos4c.database import init_db
init_db('$DB')
# Add schema_version table
import sqlite3
conn = sqlite3.connect('$DB')
conn.execute('CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT)')
conn.execute('INSERT INTO schema_version VALUES (1, datetime(\"now\"))')
conn.commit()
conn.close()
"

chown 10010:10010 "$DB"
chmod 640 "$DB"
echo "Database initialized at version 1"
```

### Docker One-Shot Execution

```bash
docker run --rm \
    -v hpos-prod-data:/opt/hermes/data \
    hermes-product-os-hpos:prod-<sha> \
    python3 /opt/hermes/app/deploy/init-production-db
```

### Idempotency

- Safe to run multiple times — skips if already initialized
- No data loss if DB exists
- Version mismatch → manual intervention

---

## 5. Production Compose Structure

```yaml
# /docker/hermes-product-os-prod/docker-compose.yml
name: hermes-product-os-prod

services:
  hpos:
    container_name: hermes-product-os-prod
    image: hermes-product-os-hpos:prod-<sha>@sha256:<digest>
    restart: unless-stopped
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    no_new_privileges: true
    environment:
      - HERMES_ENVIRONMENT=PRODUCTION
      - MUTATIONS_DISABLED=true
      - DATABASE_PATH=/opt/hermes/data/production.db
      - SIMULATION_MODE=false
    volumes:
      - /var/lib/hermes/snapshots/snapshot.db:/opt/hermes/data/production.db:ro
      - /var/lib/hermes/snapshots/snapshot.meta.json:/opt/hermes/data/snapshot.meta.json:ro
      - hpos-prod-logs:/opt/hermes/logs:rw
    networks:
      - prod-net
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
    # No ports exposed to host
    # Traefik labels added later in B7

volumes:
  hpos-prod-logs:

networks:
  prod-net:
    internal: true
```

### Key Properties

| Property | Value |
|---|---|
| `read_only: true` | Container rootfs is read-only |
| `cap_drop: ALL` | Minimal capabilities |
| `no_new_privileges: true` | No privilege escalation |
| No host ports | Only internal network access |
| `internal: true` | No outbound internet access |
| `restart: unless-stopped` | Survive daemon restart |
| Snapshot mount `:ro` | Hermes cannot write the snapshot |
| Metadata mount `:ro` | Freshness/SHA evidence is read-only in container |
| No Traefik labels yet | Added at B7 |

---

## 6. Network Model

### Phase B Pre-Canary (P1-P6)

```
Network: hermes-product-os-prod_prod-net
Type: internal: true
Public access: NONE
Host port: NONE
Reverse proxy: NOT CONNECTED
Staging access: NO (separate network)
Test-B access: NO (separate network)
Outbound internet: NO (internal only)

Access during provisioning: docker exec only
```

### Post-Canary (B7)

```
Add Traefik labels → reverse proxy route
Basic auth (separate credentials from staging)
HTTPS via Traefik + Let's Encrypt
```

---

## 7. P1-P6 Task Breakdown

### P1 — Production Namespace + Directories

| Item | Action |
|---|---|
| Create project dir | `mkdir -p /docker/hermes-product-os-prod` |
| Create secrets dir | `mkdir -p /etc/hermes-product-os-prod/secrets` |
| Create snapshots dir | `mkdir -p /var/lib/hermes/snapshots/production` |
| Set permissions | `chmod 750 /etc/hermes-product-os-prod/secrets` |

**Files created:** Directories only. No secrets, no compose.  
**Rollback:** `rm -rf /docker/hermes-product-os-prod /etc/hermes-product-os-prod`  
**PASS:** Directories exist, correct permissions.

### P2 — Production Compose + Volume Definition

| Item | Action |
|---|---|
| Write compose | `/docker/hermes-product-os-prod/docker-compose.yml` |
| Image reference | `hermes-product-os-hpos@sha256:7bbc4894b02b...` (staging image digest) |
| Create volumes | `docker compose -f /docker/hermes-product-os-prod/docker-compose.yml up --no-start` |

**Files created:** `docker-compose.yml`  
**Volumes created:** `hpos-prod-data`, `hpos-prod-logs`  
**Rollback:** `docker compose down -v`, remove compose file  
**PASS:** Volumes exist, compose validates.

### P3 — Initialize Production DB Schema

| Item | Action |
|---|---|
| Run one-shot init | `docker run --rm -v hpos-prod-data:/opt/hermes/data <image> python3 deploy/init-production-db` |
| Verify schema | Check tables exist |
| Verify empty | Decision count = 0 |

**Files created:** `production.db` in volume  
**Rollback:** Delete volume, recreate  
**PASS:** Schema correct, 0 decisions, schema_version=1.

### P4 — Verify DB Persistence + Security + Integrity

| Item | Action |
|---|---|
| Start container | `docker compose up -d` |
| Health check | `GET /api/health` → alive, PRODUCTION, DISABLED |
| DB accessible | `docker exec hpos-prod sqlite3 ... "PRAGMA integrity_check"` |
| Read container rootfs | Verify `read_only: true` effective |
| Capabilities | Verify `cap_drop: ALL` effective |
| Network | Verify `internal: true` — no outbound access |
| Container recreate test | `docker compose stop && docker compose up -d` → DB preserved |

**Rollback:** `docker compose down`  
**PASS:** All checks pass. DB survives restart.

### P5 — Discover Actual Docker Volume Mountpoint

| Item | Action |
|---|---|
| Get volume name | `docker volume ls --filter name=hpos-prod-data -q` |
| Get mountpoint | `docker volume inspect <name> --format '{{.Mountpoint}}'` |
| Verify DB exists | `test -f <mountpoint>/production.db` |
| Record path | Save discovered path for P6 |

**Output:** `${MOUNTPOINT}/production.db` (actual, not assumed)  
**PASS:** Path discovered, DB file exists at path.

### P6 — Create B3 PRODUCTION_DB_PATH + Cross-Access Verification

| Item | Action |
|---|---|
| Write secret | `echo "${DISCOVERED_PATH}" > /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH` |
| Set permissions | `chown root:root`, `chmod 400` |
| Verify staging isolation | Staging cannot read `/etc/hermes-product-os-prod/` |
| Verify Test-B isolation | Test-B cannot read `/etc/hermes-product-os-prod/` |
| Verify no env/log exposure | No PRODUCTION_DB_PATH in container env or Docker inspect |

**Files created:** `/etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH`  
**Rollback:** Remove file  
**PASS:** B3 complete — production source path identified, isolated.

---

## 8. P1 Safety

P1 creates empty directories only:

```
/docker/hermes-product-os-prod/     (empty, no compose)
/etc/hermes-product-os-prod/secrets/ (empty, no secrets)
/var/lib/hermes/snapshots/production/ (empty, no snapshots)
```

- No container started
- No database initialized
- No networking
- No credentials
- No staging changes
- No Test-B changes

---

## PASS/FAIL Criteria Summary

| Phase | Criteria |
|---|---|
| P1 | Directories exist, correct permissions |
| P2 | Volumes created, compose validates |
| P3 | DB initialized, schema correct, empty |
| P4 | Container healthy, PRODUCTION/DISABLED, integrity ok, persistent |
| P5 | Mountpoint discovered, DB path verified |
| P6 | Secret created, isolated, B3 closed |

---

**V2 complete. Awaiting Amjad review.**
