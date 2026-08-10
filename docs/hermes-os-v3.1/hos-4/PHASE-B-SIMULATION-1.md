# Phase B — Simulation Results: Kill Switch + Snapshot Design

## 1. Kill Switch — Evaluation

### Evidence

| Item | Observed |
|---|---|
| hpos stopped | ✅ Container stopped |
| Unrelated containers unaffected | ✅ digital-wave, webui, agent, workspace, traefik all running |
| hpos restarted | ✅ Healthy |
| Mutations after restart | ✅ DISABLED |
| Activation level | LEVEL_1_PRIVATE_VPS_STAGING (unchanged) |

### Classification: **PASS — with design note**

**Rationale:** `docker compose down` has unnecessary blast radius (removes container, not just stops it). `docker compose stop hpos` / `start hpos` achieves the same access-denial outcome with smaller blast radius.

**Production kill switch design:**

```bash
docker compose -f /docker/hermes-product-os/docker-compose.prod.yml stop hpos
```

This is the preferred kill switch because:
1. Stops only the production hpos container
2. All bind mounts (credentials, snapshot) are detached on stop
3. Staging container (separate compose project) is untouched
4. All other VPS services are untouched
5. Container remains (logs preserved), just not running
6. Restart requires explicit `docker compose start` — no auto-recovery

**Restart guard:** Phase B compose file includes `MUTATIONS_DISABLED=true` and `ACTIVATION_LEVEL=LEVEL_2`. If someone restarts, they get Level 2 with mutations disabled — not Level 0 or 1. To fully disable, remove the production compose file or delete the project.

**Safety:** Stopping hpos detaches all bind mounts. The files remain on disk but are inaccessible to any process. Restarting re-mounts them. This means the kill switch needs to be paired with credential/mount removal for permanent disable.

---

## 2. Snapshot Pipeline — Simulation Design

### Starting State

| Item | Actual |
|---|---|
| sqlite3 | ✅ Available on host |
| `/var/lib/hermes/snapshots/` | ❌ Does not exist |
| `test-snapshot.db` | ❌ Does not exist |
| Group `hermes` | ❌ Does not exist on host |

### Simulation Procedure

**VPS TERMINAL — Amjad runs these in order:**

#### Step 1: Create test infrastructure
```bash
# Create group and directories
groupadd --system hermes
useradd --system -g hermes -s /usr/sbin/nologin hermes-snapshot
mkdir -p /var/lib/hermes/snapshots
chown root:hermes /var/lib/hermes/snapshots
chmod 750 /var/lib/hermes/snapshots
```

#### Step 2: Create simulated production source
```bash
# This simulates the live production DB that Hermes must NEVER touch
sqlite3 /var/lib/hermes/source-test.db "CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT, version INTEGER);"
sqlite3 /var/lib/hermes/source-test.db "CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, action TEXT, created_at TEXT);"
sqlite3 /var/lib/hermes/source-test.db "PRAGMA journal_mode=WAL;"
sqlite3 /var/lib/hermes/source-test.db "INSERT INTO decisions VALUES ('DEC-001', 'AWAITING_AMJAD', 1);"
sqlite3 /var/lib/hermes/source-test.db "INSERT INTO audit_events VALUES ('AUD-001', 'create', datetime('now'));"
chown root:root /var/lib/hermes/source-test.db
chmod 600 /var/lib/hermes/source-test.db
ls -la /var/lib/hermes/source-test.db /var/lib/hermes/source-test.db-wal /var/lib/hermes/source-test.db-shm 2>/dev/null
```

#### Step 3: Run snapshot pipeline (as root — simulates timer)
```bash
# Checkpoint (flush WAL)
sqlite3 /var/lib/hermes/source-test.db "PRAGMA wal_checkpoint(TRUNCATE);"

# Atomic backup (SQLite API, not cp)
sqlite3 /var/lib/hermes/source-test.db ".backup /var/lib/hermes/snapshots/snapshot-test.db.tmp"

# Verify
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "PRAGMA integrity_check;"

# Atomic publish
mv /var/lib/hermes/snapshots/snapshot-test.db.tmp /var/lib/hermes/snapshots/snapshot-test.db

# Restrict
chown root:hermes /var/lib/hermes/snapshots/snapshot-test.db
chmod 440 /var/lib/hermes/snapshots/snapshot-test.db
```

#### Step 4: Verify separation
```bash
# Confirm source is NOT readable by hermes
sudo -u hermes-snapshot cat /var/lib/hermes/source-test.db 2>&1
# Expected: Permission denied

# Confirm snapshot IS readable by hermes
sudo -u hermes-snapshot sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
# Expected: 1
```

#### Step 5: Prove Hermes container cannot touch source
```bash
# Mount snapshot (not source) into container
# Source path /var/lib/hermes/source-test.db is deliberately NOT mounted
docker exec hermes-product-os sh -c '[ -r /var/lib/hermes/source-test.db ] && echo ACCESSIBLE || echo NOT_ACCESSIBLE'
# Expected: NOT_ACCESSIBLE
```

---

### After Amjad runs `SIMULATION_COMPLETE`, I will:
1. Verify all output evidence
2. Classify each snapshot control PASS/FAIL
3. Update the 20-control matrix
4. Produce the final activation evidence package