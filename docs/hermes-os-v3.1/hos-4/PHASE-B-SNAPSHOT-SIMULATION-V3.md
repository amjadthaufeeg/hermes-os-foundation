# Phase B — Snapshot Simulation v3

**Revisions: accurate claims, stale enforcement, corrupt rejection gate, cleanup, file-only mount design.**

---

## Claim Classification

| Claim | Status | What It Actually Proves |
|---|---|---|
| Concurrent-write tolerance | **NOT CLAIMED** | v2 only proved post-backup write, not during-backup |
| Point-in-time consistency | **TO BE TESTED** | Snapshot reflects committed state at backup moment |
| Stale-policy enforcement | **TO BE TESTED** | Consumer rejects snapshot older than policy |
| Corrupt-publication rejection | **TO BE TESTED** | Pipeline never publishes a corrupt .tmp |
| Live-source isolation | **TO BE TESTED** | Source not mounted in Hermes container |
| Partial visibility | **TO BE TESTED** | Only final published FILE mounted, not directory |

---

## Mount Design

**Production:** Only the published snapshot file is mounted:

```
/var/lib/hermes/snapshots/snapshot-test.db → /opt/hermes/data/production-snapshot.db:ro
```

Not the directory. Hermes sees only the final artifact. Never `.tmp` files.

---

## Procedure v3

**All commands: VPS TERMINAL. No production resources.**

---

### COMMAND 1 — Detect existing artifacts (idempotency check)

```bash
for path in /var/lib/hermes/source-test.db /var/lib/hermes/snapshots/snapshot-test.db /var/lib/hermes/snapshots/snapshot-test.db.tmp; do
  test -e "$path" && echo "EXISTS: $path (clean up before rerun)" || echo "CLEAR: $path"
done
```

**Expected:** All three show CLEAR. If any EXISTS, clean up before proceeding.

---

### CHECKPOINT 0 — All paths clear. Ready to create.

---

### COMMAND 2 — Create snapshot working directory

```bash
mkdir -p /var/lib/hermes/snapshots && chmod 750 /var/lib/hermes/snapshots && ls -ld /var/lib/hermes/snapshots
```

**Expected:** `drwxr-x--- root:root /var/lib/hermes/snapshots`

---

### COMMAND 3 — Create simulated production source with WAL mode

```bash
sqlite3 /var/lib/hermes/source-test.db "
CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT, version INTEGER);
CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, action TEXT, created_at TEXT);
PRAGMA journal_mode=WAL;
INSERT INTO decisions VALUES ('DEC-001','AWAITING_AMJAD',1);
INSERT INTO audit_events VALUES ('AUD-001','create',datetime('now'));
"
```

**Expected:** No output (or `wal`).

---

### COMMAND 4 — Verify WAL mode

```bash
sqlite3 /var/lib/hermes/source-test.db "PRAGMA journal_mode;"
```

**Expected:** `wal`

---

### COMMAND 5 — Verify source content

```bash
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM decisions;"
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM audit_events;"
```

**Expected:** `1` / `1`

---

### COMMAND 6 — Restrict source (production-writer only)

```bash
chown root:root /var/lib/hermes/source-test.db && chmod 600 /var/lib/hermes/source-test.db
```

**Expected:** No output.

---

### COMMAND 7 — Verify source ownership

```bash
ls -la /var/lib/hermes/source-test.db
```

**Expected:** `-rw------- root:root`

---

### CHECKPOINT 1 — Source: WAL mode, 1 row, root-only. Ready for snapshot.

---

### COMMAND 8 — Generate snapshot using .backup (no WAL truncate)

```bash
sqlite3 /var/lib/hermes/source-test.db ".backup /var/lib/hermes/snapshots/snapshot-test.db.tmp"
```

**Expected:** No output.

---

### COMMAND 9 — Integrity check on .tmp BEFORE publish

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "PRAGMA integrity_check;"
```

**Expected:** `ok`

---

### COMMAND 10 — Verify .tmp content

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `1`

---

### CHECKPOINT 2 — .tmp is valid and contains expected data. Ready to publish.

---

### COMMAND 11 — Atomic publish (rename, not copy)

```bash
mv /var/lib/hermes/snapshots/snapshot-test.db.tmp /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** No output.

---

### COMMAND 12 — Restrict published snapshot

```bash
chown root:10010 /var/lib/hermes/snapshots/snapshot-test.db && chmod 440 /var/lib/hermes/snapshots/snapshot-test.db && ls -la /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** `-r--r----- root:10010`

---

### CHECKPOINT 3 — Snapshot published, root:10010, mode 440.

---

### COMMAND 13 — Prove no .tmp files visible after atomic publish

```bash
ls /var/lib/hermes/snapshots/*.tmp 2>&1
```

**Expected:** `No such file or directory`

---

### COMMAND 14 — Prove source is NOT mounted in Hermes container

```bash
docker exec hermes-product-os sh -c 'test -r /var/lib/hermes/source-test.db && echo SOURCE_ACCESSIBLE || echo SOURCE_NOT_IN_CONTAINER'
```

**Expected:** `SOURCE_NOT_IN_CONTAINER`

**Claim:** Source path is not present in container. Not proof of host permission isolation — proof that the compose file does not mount the source path.

---

### COMMAND 15 — Prove snapshot file is not yet mounted

```bash
docker exec hermes-product-os sh -c 'test -r /opt/hermes/data/snapshot-test.db && echo SNAPSHOT_MOUNTED || echo SNAPSHOT_NOT_MOUNTED'
```

**Expected:** `SNAPSHOT_NOT_MOUNTED`

---

### CHECKPOINT 4 — Source not in container. Snapshot not yet mounted. No .tmp visible.

---

### COMMAND 16 — Point-in-time proof: Write to source AFTER backup

```bash
sqlite3 /var/lib/hermes/source-test.db "INSERT INTO decisions VALUES ('DEC-002','APPROVED',2);"
```

**Expected:** No output.

---

### COMMAND 17 — Verify source has new row

```bash
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `2`

---

### COMMAND 18 — Verify snapshot is unchanged (point-in-time)

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `1`

---

### CHECKPOINT 5 — Point-in-time: source=2, snapshot=1. Snapshot reflects state at backup moment.

---

### COMMAND 19 — Corrupt-publication rejection: Create corrupt .tmp

```bash
echo "NOT_A_VALID_SQLITE_DATABASE" > /var/lib/hermes/snapshots/corrupt-test.db.tmp
```

**Expected:** No output.

---

### COMMAND 20 — Integrity check on corrupt .tmp (must FAIL)

```bash
sqlite3 /var/lib/hermes/snapshots/corrupt-test.db.tmp "PRAGMA integrity_check;" 2>&1
```

**Expected:** `Error: file is not a database`

---

### COMMAND 21 — Pipeline removes corrupt .tmp (simulates reject-then-quarantine)

```bash
rm /var/lib/hermes/snapshots/corrupt-test.db.tmp
```

**Expected:** No output.

---

### COMMAND 22 — Prove published snapshot is unchanged (not overwritten by corrupt)

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `1` (still the valid snapshot)

---

### CHECKPOINT 6 — Corrupt .tmp caught, removed, valid published snapshot preserved.

---

### COMMAND 23 — Stale-policy: Record snapshot timestamp

```bash
stat -c '%Y' /var/lib/hermes/snapshots/snapshot-test.db > /tmp/snapshot-ts.txt
cat /tmp/snapshot-ts.txt
```

**Expected:** Unix timestamp (integer).

---

### COMMAND 24 — Stale-policy: Compute age and test against policy threshold

```bash
SNAPSHOT_TS=$(cat /tmp/snapshot-ts.txt)
CURRENT_TS=$(date +%s)
AGE=$((CURRENT_TS - SNAPSHOT_TS))
POLICY_SECONDS=3600
echo "Age: ${AGE}s  Policy: ${POLICY_SECONDS}s"
if [ "$AGE" -gt "$POLICY_SECONDS" ]; then
  echo "STALE: REFUSE_READ"
else
  echo "FRESH: ALLOW_READ"
fi
```

**Expected:** `FRESH: ALLOW_READ` (snapshot just created, well within 3600s). The policy evaluation mechanism is demonstrated.

---

### CHECKPOINT 7 — Stale detection mechanism demonstrated. Age vs policy threshold evaluated.

---

### COMMAND 25 — Mutation boundary: Verify mutations remain disabled

```bash
docker exec hermes-product-os python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/api/health').read().decode())"
```

**Expected:** `{"status":"alive","environment":"LOCAL_SIMULATION","mutations":"DISABLED"}`

---

### CHECKPOINT 8 — Mutations disabled. No authority introduced.

---

### COMMAND 26 — Cleanup: Remove simulation artifacts

```bash
rm -f /var/lib/hermes/source-test.db /var/lib/hermes/source-test.db-wal /var/lib/hermes/source-test.db-shm
rm -f /var/lib/hermes/snapshots/snapshot-test.db
rm -f /tmp/snapshot-ts.txt
echo "Simulation artifacts removed"
```

**Expected:** `Simulation artifacts removed`

---

## Results Table

| # | Test | Command(s) | Expected | Observed |
|---|---|---|---|---|
| 1 | WAL mode active | 3-4 | `wal` | |
| 2 | Source restricted | 6-7 | `-rw------- root:root` | |
| 3 | Snapshot integrity | 9 | `ok` | |
| 4 | Atomic publish | 11,13 | no .tmp visible | |
| 5 | Ownership | 12 | `root:10010 440` | |
| 6 | Source NOT in container | 14 | `SOURCE_NOT_IN_CONTAINER` | |
| 7 | Snapshot not yet mounted | 15 | `SNAPSHOT_NOT_MOUNTED` | |
| 8 | Point-in-time | 16-18 | source=2, snapshot=1 | |
| 9 | Corrupt caught + rejected | 19-21 | `Error: file is not a database` | |
| 10 | Valid snapshot preserved | 22 | `1` | |
| 11 | Stale detection | 23-24 | `FRESH: ALLOW_READ` | |
| 12 | Mutations disabled | 25 | `mutations:DISABLED` | |
| 13 | Cleanup | 26 | Artifacts removed | |

---

## Post-Simulation Status

| Control | Status |
|---|---|
| Kill switch | PASS |
| Snapshot creation (.backup, no WAL truncate) | NOT TESTED |
| Snapshot integrity gate | NOT TESTED |
| Atomic publication (mv, no .tmp visible) | NOT TESTED |
| Point-in-time consistency | NOT TESTED |
| Concurrent-write tolerance | **NOT CLAIMED** (requires separate test) |
| Stale-policy enforcement | NOT TESTED |
| Corrupt-publication rejection | NOT TESTED |
| Live-source isolation (not mounted) | NOT TESTED |
| Mutation boundary | NOT TESTED |

**All 9 snapshot controls: NOT TESTED until simulation executes. Phase B: PLANNED_ONLY. Zero production.**