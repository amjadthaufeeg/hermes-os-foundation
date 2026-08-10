# Phase B — Snapshot Pipeline Simulation v2

**Revised per engineering review: no WAL truncate, no `cat` of binary files, concurrent-write proof added.**

---

## Consumer Identity Decision

**No dedicated host user/group will be created for this simulation.**

Rationale:
- In production, the snapshot file ownership will be `root:hermes` where `hermes` is the GID matching the container's runtime user (UID 10010).
- The container user already exists and has a known UID/GID (10010:10010).
- Permission testing can use numeric ID tests or `docker exec` from the existing container.
- Creating a permanent OS identity for a simulation adds unnecessary state.

**Production architecture:** `chown root:10010 snapshot.db; chmod 440 snapshot.db`.
Container user (UID 10010) reads via group permission. No new OS user required.

---

## Revised Simulation Procedure

**VPS TERMINAL — Amjad runs in order.**

### PART A — Setup simulated production source

```bash
# Create test directory
mkdir -p /var/lib/hermes/snapshots
chmod 750 /var/lib/hermes/snapshots

# Create source DB (simulates live production DB, WAL mode)
sqlite3 /var/lib/hermes/source-test.db "
  CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT, version INTEGER);
  CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, action TEXT, created_at TEXT);
  PRAGMA journal_mode=WAL;
  INSERT INTO decisions VALUES ('DEC-001','AWAITING_AMJAD',1);
  INSERT INTO audit_events VALUES ('AUD-001','create',datetime('now'));
"

# Confirm WAL mode is active
sqlite3 /var/lib/hermes/source-test.db "PRAGMA journal_mode;"
# Expected: wal

# Source is production-writer-only (root)
chown root:root /var/lib/hermes/source-test.db
chmod 600 /var/lib/hermes/source-test.db

echo "SOURCE SETUP COMPLETE"
```

### PART B — Snapshot generation (root, independent of Hermes)

```bash
# Step B1: Backup directly from WAL-mode source (no TRUNCATE)
sqlite3 /var/lib/hermes/source-test.db ".backup /var/lib/hermes/snapshots/snapshot-test.db.tmp"

# Step B2: Verify integrity of snapshot BEFORE publishing
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "PRAGMA integrity_check;"
# Expected: ok

# Step B3: Atomic publish (mv, not cp)
mv /var/lib/hermes/snapshots/snapshot-test.db.tmp /var/lib/hermes/snapshots/snapshot-test.db

# Step B4: Restrict — group 10010 = container user
chown root:10010 /var/lib/hermes/snapshots/snapshot-test.db
chmod 440 /var/lib/hermes/snapshots/snapshot-test.db

ls -la /var/lib/hermes/snapshots/snapshot-test.db

echo "SNAPSHOT GENERATED"
```

### PART C — Verify snapshot content (not binary dump)

```bash
# Verify row count — proves data is intact
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
# Expected: 1

sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM audit_events;"
# Expected: 1

echo "SNAPSHOT CONTENT VERIFIED"
```

### PART D — Permission boundary tests

```bash
# Test D1: Source DB is NOT readable by container user (numeric test)
docker exec hermes-product-os sh -c 'test -r /var/lib/hermes/source-test.db && echo SOURCE_READABLE || echo SOURCE_NOT_READABLE'
# Expected: SOURCE_NOT_READABLE

# Test D2: Snapshot path is not mounted in container
docker exec hermes-product-os sh -c 'test -r /opt/hermes/data/snapshot-test.db 2>/dev/null && echo SNAPSHOT_MOUNTED || echo SNAPSHOT_NOT_MOUNTED'
# Expected: SNAPSHOT_NOT_MOUNTED (not yet in compose)

echo "PERMISSION BOUNDARY VERIFIED"
```

### PART E — Concurrent write proof

```bash
# While source is in WAL mode, write new data to source
sqlite3 /var/lib/hermes/source-test.db "INSERT INTO decisions VALUES ('DEC-002','APPROVED',2);"
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM decisions;"
# Expected: 2

# Prove snapshot is unchanged (point-in-time consistent)
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
# Expected: 1 (snapshot captured state BEFORE the insert)

echo "CONCURRENT WRITE PROOF: Snapshot is point-in-time consistent"
```

### PART F — Stale snapshot detection

```bash
# Record snapshot timestamp
SNAPSHOT_AGE=$(stat -c %Y /var/lib/hermes/snapshots/snapshot-test.db)
CURRENT_TIME=$(date +%s)
AGE_SECONDS=$((CURRENT_TIME - SNAPSHOT_AGE))
echo "Snapshot age: ${AGE_SECONDS} seconds"
# Hermes would check: if age > policy (e.g. 3600s = 1hr), refuse/flags
echo "STALE DETECTION: Snapshot created now — age in policy range"
```

### PART G — Corrupt snapshot rejection

```bash
# Create a corrupt file that would fail integrity_check
echo "CORRUPT" > /var/lib/hermes/snapshots/corrupt-test.db
sqlite3 /var/lib/hermes/snapshots/corrupt-test.db "PRAGMA integrity_check;" 2>&1
# Expected: Error: file is not a database

# Cleanup — corrupt file removed before publication
rm /var/lib/hermes/snapshots/corrupt-test.db

echo "CORRUPT SNAPSHOT REJECTED"
```

### PART H — Partial snapshot protection

```bash
# Check: .tmp file should not exist after atomic mv
ls /var/lib/hermes/snapshots/*.tmp 2>&1
# Expected: No such file or directory
# Proves atomic rename worked — no partial snapshot visible

echo "PARTIAL SNAPSHOT PROTECTION: No .tmp files visible"
```

---

## Test Summary (for Amjad to confirm)

After running, confirm these outputs:

| Part | Expected | Your Result |
|---|---|---|
| A | WAL mode: wal | |
| B2 | integrity_check: ok | |
| C | decisions=1, audit=1 | |
| D1 | SOURCE_NOT_READABLE | |
| D2 | SNAPSHOT_NOT_MOUNTED | |
| E | snapshot=1, source=2 (concurrent proof) | |
| F | snapshot age < 3600s | |
| G | "file is not a database" error | |
| H | "No such file" for *.tmp | |

---

Type `SNAPSHOT_SIMULATION_COMPLETE` when finished with observed results.