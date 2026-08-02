# HOS-4D.4C.1 Operational Review — Commit 64b3c6d

**Date:** 2026-08-02  
**Branch:** `feature/HOS-4D.4C.1-backup-encryption` (not yet merged to main)  
**Reviewer:** Hermes Agent (subagent)  
**Status:** Foundation solid — significant gaps remain for production readiness

---

## 1. What Was Assessed

- **backup.py** (108 lines): SQLite backup foundation module  
- **test_backup.py** (16 tests, all passing): Comprehensive unit test suite  
- **HOS-4D.4C-PROGRAM.md**: Full architecture plan (254 lines)  
- **TASK-HOS-4D-4C.yaml**: Contract (R3 risk level)  
- **Existing Hermes CLI backup**: `hermes backup` zip-archive tool  
- **Live backup state**: 3 `.hermes.backup.*` directories present on-disk  

---

## 2. Backup Procedure Assessment

### What's implemented (4C.1):
| Component | Status | Notes |
|---|---|---|
| SQLite `.backup` API | ✅ | WAL-aware, atomic, uses `sqlite3.connect().backup()` |
| Pre-backup integrity check | ✅ | `PRAGMA integrity_check` on source |
| Post-backup integrity verify | ✅ | Re-checks backup before returning path |
| SHA-256 checksums | ✅ | Streaming 64KB chunk hashing |
| Deterministic manifest | ✅ | 13 fields, schema versioned |
| Backup state machine | ✅ | 10 states: PENDING → RESTORED |
| Retention calculator | ✅ | 6 classes: DAILY(30d) through POST_MIGRATION(365d) |
| Test isolation | ✅ | tmpdir fixtures, no real state touched |

### Strengths:
- The `.backup` API guarantees a consistent snapshot even with active WAL — no `cp`-style race conditions
- Integrity checks are performed on BOTH source and backup — catches corruption in either direction
- Filenames include UTC timestamp + UUID to prevent collisions
- The destroyed-on-integrity-fail pattern (`os.remove(dest)` + `return None`) is clean fail-closed behavior

### Weaknesses:
- **No retry logic.** If `PRAGMA integrity_check` fails due to a transient WAL checkpoint issue, the backup silently returns None. The plan mentions "locked DB → retry" but none is implemented.
- **No WAL checkpoint.** The backup uses `.backup()` which IS WAL-aware, but there's no explicit `PRAGMA wal_checkpoint` before backup. WAL files accumulate; stale WAL can inflate without affecting integrity — but recovery from WAL-only is impossible without the WAL file.
- **No backup verification pipeline.** After creation, the manifest records `SNAPSHOT_CREATED` but the state machine's later states (INTEGRITY_VERIFIED, ENCRYPTED, ARCHIVE_VERIFIED) are defined but never transitioned to. These are aspirational states with no code path to reach them.

---

## 3. Failure Handling Assessment

### What's handled:
| Failure Mode | Behavior | Grade |
|---|---|---|
| Missing source DB | `check_integrity` returns False, `create_backup` returns None | ✅ Clean |
| Corrupt source DB | `PRAGMA integrity_check` fails, returns None | ✅ Clean |
| Corrupt backup DB (post-write) | `os.remove(dest)`, returns None | ✅ Clean |
| Integrity check exception | Caught, returns False | ✅ Clean |

### What's NOT handled:
| Failure Mode | Risk | Severity |
|---|---|---|
| Disk full during backup | `sqlite3.backup()` raises exception — **uncaught** | HIGH |
| Permission denied on destination | Uncaught OSError | HIGH |
| WAL file present, source.db corrupted, WAL healthy | `.backup()` may produce a clean backup, but `check_integrity` on source fails first and backs out unnecessarily | MEDIUM |
| Concurrent access to source during backup | SQLite handles this at the engine level, but no application-level locking | LOW |
| Partial backup on process kill | No atomic write — backup file is written directly, no rename-from-temp pattern | MEDIUM |

### Critical gap: The `create_backup` function has no try/except around the actual backup operation. If `src.backup(dst)` throws (disk full, I/O error), the exception propagates unhandled. The plan document specifies "disk full → alert + halt" but this is not implemented.

---

## 4. Manifest Usefulness Assessment

### Current manifest fields (13):
```
backup_id, created_at, source_environment, service_version,
source_database_id, database_schema_version, audit_chain_head,
checkpoint_head, migration_history_head, files (with checksums),
encryption_key_id, archive_format, backup_state, retention_class,
manifest_schema_version
```

### What's good:
- The schema is versioned (`manifest_schema_version: 1`) — forward compatibility
- Checksums are embedded in the manifest (single source of truth for integrity)
- `source_environment` disambiguates production vs. dev vs. simulation backups
- `retention_class` enables automated cleanup policies

### What's missing for operational usefulness:
- **No manifest persisted to disk.** `build_manifest()` returns a dict but nothing writes it. The manifest exists only in-memory during test execution. For the manifest to serve as a recovery artifact, it must be serialized alongside the backup (or to a manifest store).
- **Anchor fields are stubs.** `audit_chain_head`, `checkpoint_head`, and `migration_history_head` are hardcoded to `"NOT_RECORDED"`. These should be populated from the live system to make the manifest a true recovery anchor.
- **No manifest verification on restore.** The plan's 8-step restore mentions "verify manifest" but no `verify_manifest()` function exists.

---

## 5. Limitations of Unencrypted Local-Only Backups

### Current state at 4C.1:
The backup module stores files as plain SQLite databases in a local directory. There is:

- ❌ **No encryption.** GPG is mentioned throughout the plan and module docstring but zero encryption code exists. The `encryption_key_id` in the manifest is parameterized but unused beyond being hardcoded to `"test-key-001"`.
- ❌ **No off-host storage.** Everything writes to local `tempfile.mkdtemp()` directories. The plan recommends S3-compatible object storage with versioning and object lock — none is implemented.
- ❌ **No key custody.** The plan defines 6-domain key separation but no key management code exists.
- ❌ **No access control on backup files.** Backup `.db` files are created with default permissions — no `chmod 600`.
- ❌ **No backup deletion or rotation.** Retention is calculated but no cleanup code runs.

### Risk severity:
| Risk | Impact | Mitigation at 4C.1 |
|---|---|---|
| Local disk failure | Total data loss | None |
| Ransomware / malicious process | Backup deletion or encryption | None |
| Unauthorized read | Credential/token exposure | None (auth.json has tokens) |
| Accidental deletion | Loss of recovery point | None |
| Single point of failure (VPS) | All backups on same machine | None |

### What the existing `hermes backup` CLI does differently:
The `hermes backup` command (separate from HOS-4D.4C.1) creates a **zip archive** of the Hermes home directory. It's a different system — broader scope (entire config, not just SQLite), but shares the same fundamental limitation: **local-only, unencrypted, no off-host replication**. The 3 `.hermes.backup.*` directories on this machine are zip extractions — not SQLite `.backup` dumps.

### The gap for real recovery:
If the machine hosting this Hermes instance dies today:
1. The 4C.1 backup module cannot help — it's test-only
2. The `hermes backup` zip archives are on the same machine
3. There is no automated, encrypted, off-host backup of any kind

---

## 6. Readiness for 4C.2

### What 4C.2 requires (from the plan):
> Off-host storage, retention, key custody

### Assessment: **NOT READY**

| 4C.2 Prerequisite | 4C.1 Status | Gap |
|---|---|---|
| Working backup creation pipeline | ✅ Foundation code exists, test-only | Integration needed |
| Encryption (GPG) | ❌ Not implemented | Full implementation required |
| Manifest serialization | ❌ dict-only, no persistence | Must be written to disk/S3 |
| Manifest anchor population | ❌ Stubs (NOT_RECORDED) | Need integration with audit/checkpoint/migration systems |
| Retry/error handling | ❌ Bare try/finally only | Proper error taxonomy + retry needed |
| Backup alerts integration | ❌ Not connected to HOS-4D.4B.2 alert engine | Integration required |
| Key generation/storage | ❌ Not implemented | Full GPG key management needed |
| S3 client | ❌ Not implemented | boto3 or equivalent needed |

### Recommended pre-4C.2 blockers to resolve in 4C.1:
1. **Add retry logic** for transient failures (locked DB, WAL checkpoint)
2. **Persist manifests** beside backup files (JSON)
3. **Populate manifest anchors** from live audit/checkpoint/migration state
4. **Add error taxonomy** (disk full, permission denied, etc.) instead of bare exceptions
5. **Add atomic write** (write to temp + rename) for backup files
6. **Connection to alert engine** — emit backup-failed/backup-overdue alerts

---

## 7. Test Discrepancy

| Claimed | Actual | Gap |
|---|---|---|
| 200 total (182 + 18) | 198 total | -2 |

The `test_backup.py` commit message claims 18 tests, but only 16 are collected:
- 15 functional tests + 1 count test = 16
- The `test_backup_count` test asserts `total >= 15` (passes for 16)

The "200" claim on main branch is wrong — the actual count with 4C.1 merged is 198 (not 200). The discrepancy is due to the count test only asserting a minimum, not an exact value. This should be corrected before merging.

---

## 8. Summary

| Dimension | Rating | Notes |
|---|---|---|
| Code quality | 🟢 Good | Clean, well-structured, good test isolation |
| Failure handling | 🟡 Partial | Fail-closed on integrity, but bare exceptions for I/O |
| Manifest design | 🟢 Good schema | But not persisted, anchors are stubs |
| Encryption | 🔴 Missing | Zero implementation despite being in scope for 4C.1 |
| Production readiness | 🔴 Not ready | Test-only mode, no integration with live system |
| 4C.2 readiness | 🔴 Blocked | ~8 prerequisites unmet |

### Bottom line:
The 4C.1 foundation is architecturally sound — the SQLite `.backup` approach, integrity pipeline, and manifest schema are well-designed. But it's a **test-only stub**, not a working backup system. The biggest gap is the absence of encryption code (which the plan explicitly assigns to 4C.1) and the lack of any manifest persistence. For 4C.2 (off-host storage) to proceed, 4C.1 needs: encryption implementation, manifest persistence, error taxonomy, alert integration, and population of manifest anchors from the live system.