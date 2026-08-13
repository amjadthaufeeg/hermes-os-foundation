# B6 — Engineering Readiness Plan

**No implementation. Planning only.**

---

## B6 Objective

Prove that the production snapshot refresh pipeline meets Recovery Point Objective (RPO) and Recovery Time Objective (RTO) requirements for Phase B.

---

## RPO/RTO Definitions

| Metric | Target | Source |
|---|---|---|
| RPO | ≤ 24 hours (≤ 15 minutes aspirational) | PHASE-B-PROGRAM.md — "snapshot freshness ≤ 15 min" |
| RTO | Snapshot available within 30s of failure detection | Operational target |

### Contradiction Alert

**PHASE-B-PROGRAM.md specifies ≤ 15-minute snapshot freshness. The documentation also mentions "≤ 24h RPO" but this appears to be a broader Phase B requirement, not the snapshot-specific target.** The snapshot timer runs every 15 minutes (900s). The effective RPO IS 15 minutes — the age of the most recent successful snapshot. The 24-hour RPO may refer to overall disaster recovery, not snapshot-specific freshness. **This should be clarified and reconciled.**

---

## Measurement Design

| Measurement | Method | Evidence |
|---|---|---|
| Snapshot age | `snapshot.meta.json.created_at_utc` vs `now` | Journal output, health endpoint |
| Timer cadence | `systemctl list-timers hermes-snapshot-refresh.timer` | Timer state |
| Refresh success rate | `journalctl -u hermes-snapshot-refresh.service --since '24h ago' | grep SUCCESS` | Journal count |
| Refresh failure rate | `journalctl ... | grep FAILED` | Journal count |
| Snapshot integrity | `sqlite3 snapshot.db "PRAGMA integrity_check"` | ok |
| Metadata SHA match | `sha256sum snapshot.db` vs `metadata.sha256` | Match |

---

## Evidence Collection

### Automated (systemd journal)

```bash
# Snapshot age at query time
AGE_SECONDS=$(($(date +%s) - $(date -d "$(jq -r '.created_at_utc' /var/lib/hermes/snapshots/snapshot.meta.json)" +%s)))
echo "Snapshot age: ${AGE_SECONDS}s"

# Success count in last 24h
SUCCESS_COUNT=$(journalctl -u hermes-snapshot-refresh.service --since '24h ago' --no-pager | grep -c 'SUCCESS')
echo "Successful refreshes: $SUCCESS_COUNT"

# Failure count
FAIL_COUNT=$(journalctl -u hermes-snapshot-refresh.service --since '24h ago' --no-pager | grep -c 'FAILED')
echo "Failed refreshes: $FAIL_COUNT"
```

### Acceptance Thresholds

| Metric | Threshold | Alert |
|---|---|---|
| Snapshot age | ≤ 16.5 min (990s) | If older, investigate timer |
| Success count (24h) | ≥ 95 (= ~99% of expected 96 cycles) | If fewer, check systemd/journal |
| Succession failures | ≤ 2 consecutive | If ≥ 3, immediate investigation |
| Integrity | Always ok | If fail, snapshot corrupt |

---

## RTO Measurement

| Step | Time | Method |
|---|---|---|
| 1. Delete published snapshot | T0 | `rm snapshot.db` |
| 2. Trigger manual refresh | T0+1s | `systemctl start hermes-snapshot-refresh.service` |
| 3. Refresh completes (SUCCESS in journal) | T1 | `journalctl -f` |
| 4. Snapshot available to reader | T2 | `docker exec reader sqlite3 ...` |
| RTO | T2 − T0 | Should be < 30s |

---

## B6 Prerequisites

| Prerequisite | Status |
|---|---|
| B2b production source active | ✅ (per user report) |
| Snapshot timer running | ✅ |
| B4 reader deployed | ✅ |
| Snapshot metadata JSON present | ✅ |
| journalctl accessible | ✅ (root) |
| FC-05 freshness enforcement | ❌ BLOCKED |

**B6 cannot fully complete until FC-05 freshness enforcement is implemented.** Without freshness enforcement, stale snapshots are served and age measurement is less useful.

---

## B6 Readiness

| Aspect | Status |
|---|---|
| Measurement design | ✅ Ready |
| Collection commands | ✅ Ready |
| Threshold definitions | ✅ Ready |
| Dependency on FC-05 | ❌ BLOCKED |
| Production safety (no writes) | ✅ (read-only measurements) |
| Rollback | N/A (measurements only) |

**B6 is technically executable now for baseline measurements but full value requires FC-05 completion.**

---

## Rollback

B6 is measurement-only. No rollback needed. No production changes.

---

**B6 readiness: DESIGN COMPLETE, EXECUTION BLOCKED ON FC-05.**