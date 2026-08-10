# TASK-002 — Snapshot Refresh Orchestrator

**Design document. Plan only. Awaiting engineering review.**

---

## 1. Corrected Objective

Build the mechanism that periodically creates, validates, and atomically publishes a fresh read-only snapshot for Hermes, using a Test-B stub source adapter. Production source integration (B2b) follows B3 credential provisioning.

## 2. B2a / B2b Split

| Sub-task | Scope | Dependency |
|---|---|---|
| **B2a** | Refresh engine + timer + stub source adapter | None (this task) |
| **B2b** | Production source adapter (connect to live DB) | B3 (production credentials) |

B2a is testable immediately with Test-B. B2b is a configuration-level change: swap the stub source path for a production source path.

## 3. Scheduler Architecture Comparison

| Option | Pros | Cons | Authority |
|---|---|---|---|
| **A. systemd timer + shell script** | Simple, host-native, well-understood. `OnUnitActiveSec=15min`. Restart: `Restart=on-failure`. | Must install age, sqlite3 on host. Logging via journald. | Root (timer). User=root for snapshot ops. Container user=10010 for read. |
| **B. Docker one-shot service + systemd timer** | Isolated in container. No host dependency beyond Docker. | Container startup overhead per invocation. ~2s cold start penalty. | Root (timer). Container user runs snapshot ops. |
| **C. Sidecar container** | Always running, zero cold start. Can expose health endpoint. | Permanent resource consumption. More complex lifecycle. | Root (compose). Container user. |
| **D. Application-internal scheduler** | Simplest deployment. No external timer. | **REJECTED.** Hermes container would gain source DB access. Violates separation boundary. | Hermes container — too much authority. |

**Recommendation: Option A — systemd timer + shell script.**

Rationale:
- Lowest operational complexity. One timer unit + one script.
- Root-controlled. Hermes never touches the live source.
- Snapshot script is a short-lived process — no resident attack surface.
- systemd provides built-in: restart on failure, rate limiting, logging, dependency ordering.
- Proven pattern: identical to what the earlier simulation exercised.

## 4. Component / Data-Flow Diagram

```
systemd timer (root, every 15 min)
  │
  └── /usr/local/bin/hermes-snapshot-refresh
        │
        ├─ 1. Acquire lock  (flock /var/lock/hermes-snapshot.lock)
        │
        ├─ 2. Read source    SOURCE_DB=/var/lib/hermes/source-test.db (stub)
        │     sqlite3 $SOURCE_DB ".backup $TMP"
        │
        ├─ 3. Integrity      sqlite3 $TMP "PRAGMA integrity_check"
        │     If FAIL → cleanup $TMP → exit 2   (old snapshot preserved)
        │
        ├─ 4. Atomic publish  mv $TMP $PUBLISHED
        │                     /var/lib/hermes/snapshots/snapshot.db
        │
        ├─ 5. Restrict        chown root:10010 $PUBLISHED
        │                     chmod 440 $PUBLISHED
        │
        ├─ 6. Record metadata  echo "{timestamp, sha256, row_count}" > $PUBLISHED.meta
        │
        └─ 7. Remove lock

Test-B container (hermes, UID 10010)
  └── /opt/hermes/data/snapshot.db  (:ro bind mount from host)
       └── Read-only SQL queries
            Mutations: DISABLED
```

## 5. Files / Scripts Created

| Path | Purpose |
|---|---|
| `/usr/local/bin/hermes-snapshot-refresh` | Main snapshot script (bash) |
| `/etc/systemd/system/hermes-snapshot.timer` | systemd timer unit |
| `/etc/systemd/system/hermes-snapshot.service` | systemd service unit (oneshot) |
| `/var/lib/hermes/snapshots/snapshot.db` | Published snapshot (chown root:10010, 440) |
| `/var/lib/hermes/snapshots/snapshot.db.tmp` | Temporary candidate (deleted after publish) |
| `/var/lib/hermes/snapshots/snapshot.db.meta` | Metadata (age, sha256, row count) |
| `/var/lock/hermes-snapshot.lock` | Flock-based concurrency lock |

## 6. Snapshot Lifecycle

```
STARTUP:
  Timer enabled → first fire in 15 min or OnBootSec=1min

EACH CYCLE:
  1. Acquire flock (non-blocking: exit 0 if already running)
  2. Create TMP snapshot from stub source
  3. integrity_check → FAIL: rm TMP, exit 2, old snapshot untouched
  4. mv TMP → PUBLISHED (atomic on same filesystem)
  5. chown root:10010, chmod 440
  6. Write metadata
  7. Release lock, exit 0

FAILURE:
  - Source unavailable → exit 2, old snapshot remains
  - integrity_check fail → exit 2, old snapshot remains
  - Disk full → exit 2, old snapshot remains
  - Lock held > 30s → exit 3 (stale lock detection)

AFTER:
  Test-B container reads published snapshot via :ro bind mount
  Staleness: test -c %Y → age in seconds
```

## 7. Failure / Rollback

| Failure | Behaviour | Recovery |
|---|---|---|
| Source DB missing | Exit 2, old snapshot unchanged | Fix source path |
| Corrupt .tmp | Exit 2, rm .tmp | Next cycle retries |
| Disk full | Exit 2, .tmp write fails | Free disk space |
| Lock held | Exit 0 (already running) | Wait for next cycle |
| Permission error | Exit 2, log to stderr | Fix ownership |

Rollback: `systemctl disable --now hermes-snapshot.timer`. Remove script + units. Old snapshot remains until manually deleted.

## 8. Concurrency Protection

```bash
exec 200>/var/lock/hermes-snapshot.lock
flock -n 200 || { echo "Already running"; exit 0; }
# ... snapshot operations ...
flock -u 200
```

Non-blocking flock. If a previous cycle is still running, the new invocation exits silently. Next timer cycle will retry.

## 9. Test-B Test Plan

| Step | Action | Expected |
|---|---|---|
| 1 | Deploy timer + script with stub source | `systemctl start hermes-snapshot.service` → exit 0 |
| 2 | Verify snapshot published | File exists, 440, root:10010 |
| 3 | Verify snapshot readable from Test-B | `docker exec hpos-test-b sqlite3 ... "SELECT COUNT(*)"` → returns count |
| 4 | Verify muta tions disabled | Health check → DISABLED |
| 5 | Write to source | source now has N rows |
| 6 | Trigger manual refresh | `systemctl start hermes-snapshot.service` |
| 7 | Verify snapshot updated | Test-B sees N rows (new snapshot reflects source) |
| 8 | Corrupt source test | Replace source with non-DB → exit 2 → old snapshot preserved |
| 9 | Timer fires on schedule | Wait 15 min → verify snapshot timestamp updated |
| 10 | Concurrent run safety | Trigger two simultaneous runs → second exits 0 |

## 10. Production Integration Boundary (B2b)

When B3 credentials exist:

```bash
# B2a (stub):
SOURCE_DB=/var/lib/hermes/source-test.db

# B2b (production):
SOURCE_DB=/var/lib/production/hermes.db  # or environment-configured path
```

Only `SOURCE_DB` changes. Script, timer, permissions, and snapshot handling are identical. Production source must be WAL-safe (`.backup` works on WAL databases without checkpoint interference).

## 11. Acceptance Criteria

- [ ] systemd timer runs every 15 minutes
- [ ] Snapshot published atomically (no .tmp visible after completion)
- [ ] Snapshot permissions: 440, root:10010
- [ ] Integrity check runs before publish
- [ ] Failure preserves old snapshot
- [ ] Concurrent run protection works
- [ ] Test-B container reads published snapshot
- [ ] Mutations remain DISABLED
- [ ] Structured metadata written
- [ ] systemd logs capture success/failure

## 12. YAML Contract

Validated. See `.hermes/contracts/TASK-002.yaml`.

---

**TASK-002 design complete. Awaiting engineering review.**