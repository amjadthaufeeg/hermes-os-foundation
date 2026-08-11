# B3 — Production Credential Provisioning Plan

**Design only. No secrets requested. No production activation.**

---

## 1. Required Credentials / Access Items

| Item | Purpose | Required For | Mandatory Now? |
|---|---|---|---|
| Production DB path | Snapshot source | B2b | YES |
| Production DB read access | `sqlite3 .backup` needs read | B2b | YES |
| B2 Application Key ID | Backup verification (future) | B2b backup verify | NO — deferred |
| B2 Application Key | Backup verification (future) | B2b backup verify | NO — deferred |
| B2 Bucket Name | Backup target | B2b backup verify | NO — deferred |
| B2 Endpoint | Bucket endpoint | B2b backup verify | NO — deferred |

**B2 credentials are NOT required for B2b.** B2b only needs the production DB path and read access. B2 object-storage credentials belong to a future backup-verification task beyond Phase B.

## 2. Production Secret Namespace

```
/etc/hermes-product-os/secrets/
```

This namespace already exists and holds staging credentials. The production namespace should be:

```
/etc/hermes-product-os-prod/secrets/
```

| File | Purpose | Required Now? |
|---|---|---|
| `PRODUCTION_DB_PATH` | Absolute path to production SQLite database | YES |
| `B2_WRITER_KEY_ID` | Staging B2 writer (already exists) | Already provisioned |
| `B2_WRITER_APPLICATION_KEY` | Staging B2 writer | Already provisioned |
| `B2_READER_KEY_ID` | Future: production backup | DEFERRED |
| `B2_READER_APPLICATION_KEY` | Future: production backup | DEFERRED |
| `B2_BUCKET_NAME` | Future: bucket name | DEFERRED |
| `B2_ENDPOINT` | Future: endpoint | DEFERRED |

## 3. Permissions Model

| File | Owner | Group | Mode | Read-Only? |
|---|---|---|---|---|
| `PRODUCTION_DB_PATH` | root | root | 400 | Yes — contains a path, not a secret |
| `B2_READER_KEY_ID` (future) | root | root | 400 | Yes |
| `B2_READER_APPLICATION_KEY` (future) | root | root | 400 | Yes |
| `B2_BUCKET_NAME` (future) | root | root | 400 | Yes |
| `B2_ENDPOINT` (future) | root | root | 400 | Yes |
| Existing staging B2 files | root | root | 400 | Yes |

All files: `chown root:root`, `chmod 400`. Hermes UID 10010 has NO access to `/etc/hermes-product-os-prod/`.

## 4. Production Database Access Model

### How the Source is Accessed

The snapshot refresh script (`deploy/hermes-snapshot-refresh`) runs as root via systemd. It reads the production DB path from the config file or environment. The script uses `sqlite3 "$SOURCE_DB" ".backup $CANDIDATE"` — this is a read-only operation (`.backup` reads the source via SQLite's online backup API, which is a consistent reader).

### Source Location Options

| Option | Mechanism | Required Access |
|---|---|---|
| **A. Local filesystem path** (preferred) | Direct file read by root | `chown root:hermes-db-group`, `chmod 440` or similar |
| **B. Docker named volume** | Root accesses via `/var/lib/docker/volumes/...` | Root (already has Docker socket access) |
| **C. Remote/network database** | Not in Phase B scope | DEFERRED |

**Recommendation: Option A — local filesystem path.** Minimal complexity. Root reads the source via `sqlite3 ".backup"`. Hermes never touches the source.

### What the Script Needs

```
SOURCE_DB=<absolute-path-to-production-sqlite-db>
```

That's it. The script only needs read access to this one file. No network. No credentials. No API calls.

### Prohibited Access

- Hermes container must NEVER mount the production source
- Hermes must NEVER have read or write access to production credentials directory
- Snapshot script must NEVER write to the production source
- No PRAGMA wal_checkpoint or any mutating operation on source

## 5. B3 Credential / Access Items Summary

| Item | Mandatory for B2b? | Type | Location |
|---|---|---|---|
| Production DB path | YES | Path string | `/etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH` |
| Production DB read access | YES | File permission | Host filesystem ACL |
| B2 Reader Key ID | NO — deferred | Secret | `/etc/hermes-product-os-prod/secrets/B2_READER_KEY_ID` |
| B2 Reader App Key | NO — deferred | Secret | `/etc/hermes-product-os-prod/secrets/B2_READER_APPLICATION_KEY` |
| B2 Bucket Name | NO — deferred | Config | `/etc/hermes-product-os-prod/secrets/B2_BUCKET_NAME` |
| B2 Endpoint | NO — deferred | Config | `/etc/hermes-product-os-prod/secrets/B2_ENDPOINT` |

## 6. Credential Rotation Model

| Item | Rotation Mechanism |
|---|---|
| Production DB path | Change path → restart timer |
| B2 Reader Key (future) | Create new key in B2 console → replace file → restart timer |
| B2 Writer Key (staging) | Create new key → replace file → restart staging container |

Rotation frequency: not specified in Phase B. Deferred to operational policy.

## 7. Credential Revocation

```bash
# Immediate: remove the credential file
rm /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH

# Snapshot service fails safely: exit 2 (source not readable)
# Old snapshot preserved
# systemd logs: FAILED: source not readable
systemctl stop hermes-snapshot-refresh.timer
```

## 8. Verification Procedure (Without Printing Values)

```bash
# Amjad verifies on VPS:
stat -c '%a %U:%G' /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH
# Expected: 400 root:root

test -r /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH && echo "READABLE" || echo "NOT_READABLE"

cat /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH
# Amjad visually confirms the path is correct

# Path must exist and be readable:
test -r "$(cat /etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH)" && echo "SOURCE_EXISTS_READABLE" || echo "SOURCE_MISSING_OR_UNREADABLE"

# Verify no production credentials in Test-B:
docker exec hermes-product-os-test-b sh -c 'test -d /etc/hermes-product-os-prod && echo "EXPOSED" || echo "NOT_EXPOSED"'
# Expected: NOT_EXPOSED

# Verify no production credentials in staging:
docker exec hermes-product-os sh -c 'test -d /etc/hermes-product-os-prod && echo "EXPOSED" || echo "NOT_EXPOSED"'
# Expected: NOT_EXPOSED
```

## 9. Cross-Access Tests

| Test | Expected |
|---|---|
| Test-B reads production secret dir | Denied (dir doesn't exist in container) |
| Staging reads production secret dir | Denied |
| Production secret dir mounted in any compose | Must be absent from staging/Test-B compose |
| Docker inspect shows production credentials | Must NOT appear in env or mounts |

## 10. Environment / Log Exposure Checks

| Check | Command |
|---|---|
| No production env vars in Test-B | `docker exec hpos-test-b env \| grep -i prod` → empty |
| No production env vars in staging | `docker exec hpos env \| grep -i prod` → empty |
| No secrets in Docker inspect | `docker inspect hpos \| grep -i 'PRODUCTION_DB\|B2_'` → empty |
| No secrets in snapshot service logs | `journalctl -u hermes-snapshot-refresh \| grep -i 'PRODUCTION_DB\|B2_'` — should only show path to SOURCE_DB, not its content |

## 11. Rollback / Removal

```bash
systemctl stop hermes-snapshot-refresh.timer
systemctl disable hermes-snapshot-refresh.timer
rm -rf /etc/hermes-product-os-prod/secrets
```

## 12. B3 PASS Criteria

| # | Criterion |
|---|---|
| 1 | `PRODUCTION_DB_PATH` file exists at approved namespace |
| 2 | File owner root:root, mode 400 |
| 3 | File contains exactly a valid absolute filesystem path |
| 4 | Path points to an existing, readable SQLite database |
| 5 | `sqlite3 "$(cat PRODUCTION_DB_PATH)" "SELECT COUNT(*) FROM decisions"` returns > 0 |
| 6 | No production credential files in staging or Test-B containers |
| 7 | No production credential values in Docker inspect, env, or logs |
| 8 | `chown hermes:hermes PRODUCTION_DB_PATH` → would break snapshot; must NOT be possible for hermes user |
| 9 | Snapshot script can read the path via `cat PRODUCTION_DB_PATH` |
| 10 | B2 credentials deferred (files not required, not present) |

## B3 Scope Clarification

| Scope | Included in B3? |
|---|---|
| Production DB path + read access | **YES** |
| B2 Reader/Writer credentials | **NO — deferred** |
| Production application runtime | **NO — Phase C** |
| Backup verification (B2 upload/verify) | **NO — beyond Phase B** |
| Production Hermes container | **NO — B4** |

---

**B3 design complete. Amjad action: create `/etc/hermes-product-os-prod/secrets/PRODUCTION_DB_PATH` with correct permissions. No secret values needed in chat.**