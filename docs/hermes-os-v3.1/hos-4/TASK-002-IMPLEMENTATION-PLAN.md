# TASK-002 B2a — Implementation Plan

**Branch:** `task-002-snapshot-refresh`  
**Status:** Planning. Awaiting authorization to implement.

---

## 1. Files to Create

| File | Purpose |
|---|---|
| `deploy/hermes-snapshot-refresh` | Main refresh script (bash) |
| `deploy/hermes-snapshot.conf` | Configuration file for source path |
| `deploy/hermes-snapshot-refresh.service` | systemd oneshot service unit |
| `deploy/hermes-snapshot-refresh.timer` | systemd timer unit (15 min) |
| `backend/hos4c/test_snapshot_refresh.py` | Test suite (16 tests) |

---

## 2. Refresh Script (`deploy/hermes-snapshot-refresh`)

```bash
#!/bin/bash
set -euo pipefail

# === Configuration ===
LOCK_FILE="/var/lock/hermes-snapshot.lock"
SNAPSHOT_DIR="/var/lib/hermes/snapshots"
PUBLISHED="${SNAPSHOT_DIR}/snapshot.db"
CANDIDATE="${SNAPSHOT_DIR}/snapshot.db.tmp"
METADATA="${SNAPSHOT_DIR}/snapshot.db.meta"

# Source: stub for B2a, production path for B2b
SOURCE_DB="${SOURCE_DB:-/var/lib/hermes/source-test.db}"

# === Locking ===
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SKIPPED: refresh already in progress" >&2
    exit 0
fi

# === Verify source exists ===
if [ ! -r "$SOURCE_DB" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) FATAL: source not readable: $SOURCE_DB" >&2
    exit 2
fi

# === Create candidate ===
START_TS=$(date +%s)
mkdir -p "$SNAPSHOT_DIR"
sqlite3 "$SOURCE_DB" ".backup $CANDIDATE"

# === Integrity check ===
if ! sqlite3 "$CANDIDATE" "PRAGMA integrity_check;" | grep -q '^ok$'; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) FATAL: integrity_check failed" >&2
    rm -f "$CANDIDATE"
    exit 2
fi

# === Basic read check (schema exists) ===
ROW_COUNT=$(sqlite3 "$CANDIDATE" "SELECT COUNT(*) FROM decisions;" 2>/dev/null || echo "0")
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) candidate: ${ROW_COUNT} decisions" >&2

# === Set ownership + permissions ===
chown root:10010 "$CANDIDATE"
chmod 440 "$CANDIDATE"

# === Atomic publish ===
mv "$CANDIDATE" "$PUBLISHED"

# === Metadata ===
END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))
SHA256=$(sha256sum "$PUBLISHED" | cut -d' ' -f1)

cat > "$METADATA" <<METAEOF
{
  "last_success": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "snapshot_created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source": "$SOURCE_DB",
  "sha256": "$SHA256",
  "row_count": "$ROW_COUNT",
  "duration_seconds": "$DURATION",
  "result": "success"
}
METAEOF

chown root:10010 "$METADATA" 2>/dev/null || true
chmod 440 "$METADATA" 2>/dev/null || true

# === Release lock ===
flock -u 200

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SUCCESS: snapshot published (${ROW_COUNT} rows, ${DURATION}s)" >&2
exit 0
```

---

## 3. Configuration (`deploy/hermes-snapshot.conf`)

```bash
# Stub source for B2a — replace with production path for B2b
SOURCE_DB=/var/lib/hermes/source-test.db
```

---

## 4. systemd Service (`deploy/hermes-snapshot-refresh.service`)

```ini
[Unit]
Description=Hermes Snapshot Refresh — One-Shot
After=network.target

[Service]
Type=oneshot
User=root
Group=root
EnvironmentFile=/etc/hermes-snapshot.conf
ExecStart=/usr/local/bin/hermes-snapshot-refresh
StandardOutput=journal
StandardError=journal
TimeoutSec=120
Restart=no

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/hermes/snapshots /var/lock
ReadOnlyPaths=/var/lib/hermes
UMask=077
```

---

## 5. systemd Timer (`deploy/hermes-snapshot-refresh.timer`)

```ini
[Unit]
Description=Hermes Snapshot Refresh Timer
Requires=hermes-snapshot-refresh.service

[Timer]
OnBootSec=60
OnUnitActiveSec=900
RandomizedDelaySec=30
Persistent=true

[Install]
WantedBy=timers.target
```

---

## 6. Timer Cadence

| Setting | Value | Rationale |
|---|---|---|
| `OnBootSec` | 60s | Short delay after boot for services to stabilize |
| `OnUnitActiveSec` | 900s (15 min) | Matches approved Phase B snapshot interval |
| `RandomizedDelaySec` | 30s | Avoids thundering herd (even though only one instance) |
| `Persistent` | true | Catch up missed cycles after boot/systemd restart |

---

## 7. Exit Code Model

| Exit Code | Meaning | Old Snapshot |
|---|---|---|
| 0 | Success — snapshot published | Replaced |
| 0 | Skipped — flock, already running | Preserved |
| 2 | Failure — source missing, bad integrity, etc | **Preserved** |
| 3 | (reserved for stale lock detection) | Preserved |

---

## 8. Logging Model

All output to stderr → systemd journal. Format: `ISO8601 LEVEL: message`. JSON metadata written to `.meta` file alongside snapshot. systemd journal provides structured query: `journalctl -u hermes-snapshot-refresh.service`.

---

## 9. Metadata Model

```json
{
  "last_success": "2026-08-11T10:30:00Z",
  "snapshot_created": "2026-08-11T10:30:00Z",
  "source": "/var/lib/hermes/source-test.db",
  "sha256": "abc123...",
  "row_count": "42",
  "duration_seconds": "2",
  "result": "success"
}
```

JSON format for machine readability. Only written on success. Readable by container group (440).

---

## 10. Test Plan (16 tests)

| # | Test | Expected |
|---|---|---|
| T1 | Normal refresh succeeds | exit 0, snapshot published |
| T2 | Snapshot readable from Test-B | SELECT returns expected rows |
| T3 | Snapshot root:10010, mode 440 | `stat` confirms |
| T4 | Integrity check passes | SQLite `PRAGMA integrity_check` = ok |
| T5 | Point-in-time correct | Write to source → snapshot unchanged |
| T6 | Source write after backup | Snapshot has old count, source has new count |
| T7 | Corrupt candidate rejected | Invalid source → exit 2, old snapshot preserved |
| T8 | Prior good snapshot preserved | After failure, `SELECT` still returns valid data |
| T9 | Concurrent run blocked | Second `flock` invocation exits 0 (skipped) |
| T10 | Candidate .tmp absent after success | `ls *.tmp` yields nothing |
| T11 | Candidate .tmp cleaned after failure | Corrupt .tmp removed before exit |
| T12 | Metadata updated on success only | `.meta` timestamp reflects last success |
| T13 | Timer invokes service | systemd timer fires, journal shows EXEC |
| T14 | Service failure leaves safe state | exit 2, mutations DISABLED, snapshot unchanged |
| T15 | Mutations remain DISABLED | Test-B health endpoint |
| T16 | Staging unaffected | Staging container healthy throughout |

Tests run as root on host, or via `sudo` if non-root. Test-B used for container-side verification.

---

## 11. Rollback

```bash
systemctl disable --now hermes-snapshot-refresh.timer
systemctl stop hermes-snapshot-refresh.service
rm /usr/local/bin/hermes-snapshot-refresh
rm /etc/hermes-snapshot.conf
rm /etc/systemd/system/hermes-snapshot-refresh.{service,timer}
rm /var/lib/hermes/snapshots/snapshot.db*
rm /var/lock/hermes-snapshot.lock
systemctl daemon-reload
```

No container changes. No compose changes.

---

## 12. Branch + Contract

| Item | Value |
|---|---|
| Branch | `task-002-snapshot-refresh` |
| Contract | `.hermes/contracts/TASK-002.yaml` (validated) |
| Risk | R2 |
| Depends on | Nothing (stub source) |

---

**TASK-002 B2a implementation plan complete. Awaiting authorization.**