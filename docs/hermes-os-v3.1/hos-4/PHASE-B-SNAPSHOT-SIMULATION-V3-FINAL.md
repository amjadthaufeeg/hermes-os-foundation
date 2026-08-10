# Phase B — Snapshot Simulation v3: Final Execution Procedure

**All commands: VPS TERMINAL. No production resources. No Compose changes.**

---

## COMMAND 1

```bash
# Detect pre-existing simulation artifacts
for path in /var/lib/hermes/source-test.db /var/lib/hermes/snapshots/snapshot-test.db /var/lib/hermes/snapshots/snapshot-test.db.tmp; do
  if test -e "$path"; then echo "EXISTS: $path"; else echo "CLEAR: $path"; fi
done
```

**Expected:** All three show `CLEAR`.

**If EXISTS:** Amjad stops. Reports what exists. Do not overwrite.

---

## STOP CHECKPOINT 0

All paths clear → continue.

---

## COMMAND 2

```bash
mkdir -p /var/lib/hermes/snapshots && chmod 750 /var/lib/hermes/snapshots && ls -ld /var/lib/hermes/snapshots
```

**Expected:** `drwxr-x--- root:root /var/lib/hermes/snapshots`

---

## COMMAND 3

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

## COMMAND 4

```bash
sqlite3 /var/lib/hermes/source-test.db "PRAGMA journal_mode;"
```

**Expected:** `wal`

---

## COMMAND 5

```bash
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM decisions;"
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM audit_events;"
```

**Expected:** `1` and `1`

---

## COMMAND 6

```bash
chown root:root /var/lib/hermes/source-test.db && chmod 600 /var/lib/hermes/source-test.db
```

**Expected:** No output.

---

## COMMAND 7

```bash
ls -la /var/lib/hermes/source-test.db
```

**Expected:** `-rw------- root:root`

---

## STOP CHECKPOINT 1

Source: WAL mode, 1 row, root-only. Ready for snapshot.

---

## COMMAND 8

```bash
sqlite3 /var/lib/hermes/source-test.db ".backup /var/lib/hermes/snapshots/snapshot-test.db.tmp"
```

**Expected:** No output.

---

## COMMAND 9

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "PRAGMA integrity_check;"
```

**Expected:** `ok`

---

## COMMAND 10

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db.tmp "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `1`

---

## STOP CHECKPOINT 2

.tmp is valid. Integrity=ok. Content=1 row. Ready to publish.

---

## COMMAND 11

```bash
mv /var/lib/hermes/snapshots/snapshot-test.db.tmp /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** No output.

---

## COMMAND 12

```bash
chown root:10010 /var/lib/hermes/snapshots/snapshot-test.db && chmod 440 /var/lib/hermes/snapshots/snapshot-test.db && ls -la /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** `-r--r----- root:10010`

---

## STOP CHECKPOINT 3

Snapshot published: root:10010, mode 440.

---

## COMMAND 13

```bash
ls /var/lib/hermes/snapshots/*.tmp 2>&1
```

**Expected:** `No such file or directory`

---

## COMMAND 14

```bash
docker exec hermes-product-os sh -c 'test -r /var/lib/hermes/source-test.db && echo SOURCE_ACCESSIBLE || echo SOURCE_NOT_IN_CONTAINER'
```

**Expected:** `SOURCE_NOT_IN_CONTAINER`

**Claim:** Source path not mounted in container. Not host permission proof.

---

## COMMAND 15

```bash
docker exec hermes-product-os sh -c 'test -r /opt/hermes/data/snapshot-test.db && echo SNAPSHOT_MOUNTED || echo SNAPSHOT_NOT_MOUNTED'
```

**Expected:** `SNAPSHOT_NOT_MOUNTED`

---

## STOP CHECKPOINT 4

Source not in container. Snapshot not mounted. No .tmp visible.

---

## COMMAND 16

```bash
sqlite3 /var/lib/hermes/source-test.db "INSERT INTO decisions VALUES ('DEC-002','APPROVED',2);"
```

**Expected:** No output.

---

## COMMAND 17

```bash
sqlite3 /var/lib/hermes/source-test.db "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `2`

---

## COMMAND 18

```bash
sqlite3 /var/lib/hermes/snapshots/snapshot-test.db "SELECT COUNT(*) FROM decisions;"
```

**Expected:** `1`

---

## STOP CHECKPOINT 5

Point-in-time: source=2, snapshot=1. Snapshot reflects backup moment.

---

## COMMAND 19

```bash
# Record SHA-256 of valid snapshot before corrupt test
sha256sum /var/lib/hermes/snapshots/snapshot-test.db > /tmp/snapshot-sha-before.txt
cat /tmp/snapshot-sha-before.txt
```

**Expected:** SHA-256 hash displayed. Save this value.

---

## COMMAND 20

```bash
# Create corrupt .tmp candidate
echo "NOT_A_VALID_SQLITE_DATABASE_FILE_FOR_TEST" > /var/lib/hermes/snapshots/corrupt-test.db.tmp
```

**Expected:** No output.

---

## COMMAND 21

```bash
# Integrity check on corrupt .tmp (MUST FAIL)
sqlite3 /var/lib/hermes/snapshots/corrupt-test.db.tmp "PRAGMA integrity_check;" 2>&1
```

**Expected:** `Error: file is not a database`

---

## COMMAND 22

```bash
# Pipeline rejects: remove corrupt .tmp
rm /var/lib/hermes/snapshots/corrupt-test.db.tmp
```

**Expected:** No output.

---

## COMMAND 23

```bash
# Verify valid published snapshot SHA-256 unchanged
sha256sum /var/lib/hermes/snapshots/snapshot-test.db > /tmp/snapshot-sha-after.txt
diff /tmp/snapshot-sha-before.txt /tmp/snapshot-sha-after.txt && echo "SHA256_MATCH: valid snapshot preserved" || echo "SHA256_MISMATCH"
```

**Expected:** `SHA256_MATCH: valid snapshot preserved`

---

## STOP CHECKPOINT 6

Corrupt .tmp caught by integrity → removed → published snapshot unchanged.

---

## COMMAND 24

```bash
# Record current snapshot timestamp
stat -c '%Y' /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** Unix timestamp (integer, e.g. `1723228800`).

---

## COMMAND 25

```bash
# FRESH branch: snapshot just created, age < 3600s
SNAPSHOT_TS=$(stat -c '%Y' /var/lib/hermes/snapshots/snapshot-test.db)
CURRENT_TS=$(date +%s)
AGE=$((CURRENT_TS - SNAPSHOT_TS))
POLICY=3600
echo "Age: ${AGE}s  Policy: ${POLICY}s"
if [ "$AGE" -gt "$POLICY" ]; then echo "STALE: REFUSE_READ"; else echo "FRESH: ALLOW_READ"; fi
```

**Expected:** `FRESH: ALLOW_READ` (age ~0-60s, well within 3600).

---

## COMMAND 26

```bash
# STALE branch: manipulate timestamp to simulate old snapshot
touch -t 202001010000 /var/lib/hermes/snapshots/snapshot-test.db
SNAPSHOT_TS=$(stat -c '%Y' /var/lib/hermes/snapshots/snapshot-test.db)
CURRENT_TS=$(date +%s)
AGE=$((CURRENT_TS - SNAPSHOT_TS))
POLICY=3600
echo "Age: ${AGE}s  Policy: ${POLICY}s"
if [ "$AGE" -gt "$POLICY" ]; then echo "STALE: REFUSE_READ"; else echo "FRESH: ALLOW_READ"; fi
```

**Expected:** `STALE: REFUSE_READ` (age several years, far exceeds 3600).

---

## COMMAND 27

```bash
# Restore real timestamp after stale test
touch /var/lib/hermes/snapshots/snapshot-test.db
stat -c '%Y' /var/lib/hermes/snapshots/snapshot-test.db
```

**Expected:** Current timestamp restored (close to `date +%s`).

---

## STOP CHECKPOINT 7

Stale detection: FRESH → ALLOW, STALE → REFUSE. Timestamp restored.

---

## COMMAND 28

```bash
docker exec hermes-product-os python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/api/health').read().decode())"
```

**Expected:** `{"status":"alive","environment":"LOCAL_SIMULATION","mutations":"DISABLED"}`

---

## STOP CHECKPOINT 8

Mutations disabled. No authority introduced.

---

## COMMAND 29

```bash
# Cleanup: remove ONLY simulation artifacts
rm -f /var/lib/hermes/source-test.db /var/lib/hermes/source-test.db-wal /var/lib/hermes/source-test.db-shm
rm -f /var/lib/hermes/snapshots/snapshot-test.db
rm -f /tmp/snapshot-sha-before.txt /tmp/snapshot-sha-after.txt /tmp/snapshot-ts.txt
```

**Expected:** No output.

---

## COMMAND 30

```bash
# Verify cleanup: simulation artifacts removed
for path in /var/lib/hermes/source-test.db /var/lib/hermes/snapshots/snapshot-test.db; do
  test -e "$path" && echo "STILL_EXISTS: $path" || echo "REMOVED: $path"
done
```

**Expected:** `REMOVED` for both.

---

## COMMAND 31

```bash
# Verify unrelated assets NOT removed
for path in /etc/hermes-product-os/keys/staging-recovery-key.txt /etc/hermes-product-os/keys/staging-public-key.txt /etc/hermes-product-os/secrets/B2_WRITER_KEY_ID /docker/hermes-product-os/docker-compose.yml; do
  test -e "$path" && echo "PRESERVED: $path" || echo "MISSING: $path"
done
```

**Expected:** All 4 show `PRESERVED`.

---

## STOP CHECKPOINT 9

Simulation artifacts removed. Unrelated assets preserved.

---

## Observed Results Table

| # | Control | Command(s) | Expected | Observed | PASS/FAIL |
|---|---|---|---|---|---|
| 1 | Artifacts clear before start | 1 | All CLEAR | | |
| 2 | WAL mode active | 3,4 | `wal` | | |
| 3 | Source content | 5 | 1,1 | | |
| 4 | Source restricted | 6,7 | `-rw------- root:root` | | |
| 5 | Snapshot integrity gate | 9 | `ok` on .tmp | | |
| 6 | Snapshot content | 10 | `1` | | |
| 7 | Atomic publish | 11,13 | no .tmp visible | | |
| 8 | Ownership/mode | 12 | `-r--r----- root:10010` | | |
| 9 | Source NOT in container | 14 | `SOURCE_NOT_IN_CONTAINER` | | |
| 10 | Snapshot not mounted | 15 | `SNAPSHOT_NOT_MOUNTED` | | |
| 11 | Point-in-time | 17,18 | source=2, snapshot=1 | | |
| 12 | SHA-256 before corrupt | 19 | Hash recorded | | |
| 13 | Corrupt integrity FAIL | 21 | `Error: file is not a database` | | |
| 14 | Corrupt removed | 22 | No output | | |
| 15 | SHA-256 after corrupt (match) | 23 | `SHA256_MATCH` | | |
| 16 | Fresh snapshot ALLOW | 25 | `FRESH: ALLOW_READ` | | |
| 17 | Stale snapshot REFUSE | 26 | `STALE: REFUSE_READ` | | |
| 18 | Timestamp restored | 27 | Current timestamp | | |
| 19 | Mutations disabled | 28 | `mutations:DISABLED` | | |
| 20 | Artifacts removed | 30 | All REMOVED | | |
| 21 | Unrelated assets preserved | 31 | All PRESERVED | | |

---

**31 commands. 9 checkpoints. 21 results to observe. Phase B: PLANNED_ONLY. Awaiting Amjad execution.**