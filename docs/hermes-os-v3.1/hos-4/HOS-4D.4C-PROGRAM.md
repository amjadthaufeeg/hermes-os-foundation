# HOS-4D.4C — Backup, Recovery, Off-Host Storage and Key Custody

**Status:** Planning | **Release:** HOS-4D.4C | **No real backups authorized**

---

## 1. Problem Statement

The Hermes system has no disaster recovery. The audit ledger, checkpoint history, and authoritative adapter are all backed by a single SQLite file on a single VPS. A corrupted database, lost VPS, or compromised signing key could result in permanent data loss. HOS-4D.4C designs the complete recovery foundation: consistent backups, encrypted off-host storage, restore procedures, signing-key custody, and recovery authority.

## 2. Scope

SQLite backup consistency, WAL-safe backups, GPG encryption, off-host storage, retention, restore procedures, signing-key custody, key rotation, backup alerts, recovery authority.

## 3. Non-Scope

Real backups, production key configuration, deployment, live mutations, incident exercises (HOS-4D.4D), migration runner (HOS-4D.3.1).

---

## 4. Recommended Release Structure

| Release | Scope |
|---|---|
| **HOS-4D.4C.1** | Backup creation, SQLite consistency, encryption, manifests |
| **HOS-4D.4C.2** | Off-host storage, retention, key custody |
| **HOS-4D.4C.3** | Restore engine, recovery testing, runbooks |

---

## 5. Backup Architecture

### Recommended: SQLite `.backup` → GPG Encrypt → Off-Host Object Storage

```
sqlite3 audit.db ".backup /tmp/backup.db"
  → pragma integrity_check
  → gpg --encrypt --recipient hermes-backup
  → scp/aws s3 cp to off-host
  → verify remote checksum
  → record manifest
  → update metrics/alerts
```

| Option | Verdict |
|---|---|
| Same-VPS file copy | ❌ Insufficient for DR |
| VPS snapshot | ⚠️ Requires provider trust, no application-level verification |
| SQLite .backup + GPG + off-host | ✅ Recommended Stage 1 |

---

## 6. Backup Contents

- `audit.db` (authoritative decisions + audit ledger)
- Checkpoint records directory
- Migration history
- Projection queue/status
- Deployment templates (Caddyfile, hermes.service)
- Configuration metadata (no secrets)
- Public verification keys

**NOT included:** OAuth tokens, session cookies, CSRF tokens, private keys, temp files.

---

## 7. SQLite Backup Method

- Use `sqlite3 .backup` (consistent snapshot, WAL-aware)
- Pre-backup: `PRAGMA integrity_check`
- Post-backup: verify checksum
- Handle: locked DB → retry, WAL cannot checkpoint → alert, disk full → alert + halt

---

## 8. Encryption

- **Method:** GPG (or age) — symmetric or public-key
- **Key:** Separate from OAuth, checkpoint signing, deployment
- **Separation:** Decryption key not on same VPS
- **Rotation:** Annually or on compromise

---

## 9. Off-Host Storage

- **Recommended:** S3-compatible object storage (Backblaze B2, AWS S3, or similar)
- **Features:** Versioning, object lock, lifecycle policies
- **Credential separation:** Storage key cannot modify decisions, sign checkpoints, or deploy

---

## 10. Backup Schedule

| Type | Frequency |
|---|---|
| Database (audit.db) | Daily |
| Pre-migration | Before every migration |
| High-risk action | Triggered |
| Post-deployment | After deploy |
| Incident | Ad-hoc |

---

## 11. Retention

| Tier | Duration |
|---|---|
| Daily | 30 days |
| Weekly | 12 weeks |
| Monthly | 12 months |
| Incident-tagged | 2 years |
| Checkpoint-aligned | Matches checkpoint retention |

**Rule:** Never auto-delete last known valid recovery point.

---

## 12. RPO / RTO

| Metric | Stage 1 Target |
|---|---|
| Database RPO | ≤ 24 hours |
| Audit RPO | ≤ 24 hours |
| RTO | ≤ 2 hours |
| Max audit loss | 24 hours |

---

## 13. Backup Manifest

```json
{
  "backup_id": "BKP-2026-08-02-001",
  "created_at": "...",
  "db_schema_version": 1,
  "audit_chain_head": "sha256:...",
  "checkpoint_head": "CKP-...",
  "files": ["audit.db", "checkpoints/"],
  "checksums": {"audit.db": "sha256:..."},
  "encryption_key_id": "gpg-key-001",
  "storage_ref": "s3://hermes-backups/...",
  "retention_class": "daily",
  "verified": false
}
```

---

## 14. Backup Verification

States: `CREATED → ENCRYPTED → UPLOADED → VERIFIED → RESTORED`

Verify: checksum, decryption, SQLite integrity, schema version, audit chain, checkpoint chain.

Not valid just because upload succeeded.

---

## 15. Restore Procedure (8 steps)

1. Activate `MUTATIONS_DISABLED`
2. Isolate service, preserve evidence
3. Select recovery point + verify manifest
4. Download + decrypt + verify checksum
5. Restore database + verify integrity
6. Verify audit chain + checkpoint chain
7. Invalidate all sessions
8. Start in read-only mode → Amjad authorizes further recovery

**Mutations remain disabled until Amjad re-authorizes.**

---

## 16. Recovery Authority

| Action | Authority |
|---|---|
| Start backup | SYSTEM_SERVICE (automated) |
| Verify backup | SYSTEM_SERVICE |
| Delete backup | Amjad ONLY |
| Start restore | Amjad |
| Choose restore point | Amjad |
| Re-enable after recovery | Amjad ONLY |
| Hermes | **ZERO authority** |

---

## 17. Production Signing-Key Custody

- **Recommended:** Separate restricted host or KMS
- **Private key:** Not committed to Git, not in app config
- **Access:** Application may sign checkpoints only; cannot export key
- **Rotation:** Annually or on compromise
- **Backup:** Split or KMS-managed; lost key must not invalidate historical verification

---

## 18. Key Separation Matrix

| Key | Custody | Rotation |
|---|---|---|
| OAuth client secret | Env var | 90 days |
| Session key | Per restart | Per restart |
| CSRF | Per session | Per session |
| Checkpoint signing | Separate KMS/restricted host | Annual |
| Backup encryption | Offline/separate | Annual |
| Off-host storage | Env var (separate) | 90 days |

---

## 19. Backup Alerts (Integrate with HOS-4D.4B.2)

- Backup failed → HIGH
- Backup overdue → HIGH
- Verification failed → CRITICAL
- Restore test overdue → MEDIUM
- No valid recovery point → CRITICAL
- Storage quota low → MEDIUM

---

## 20. Operational Runbooks

- Backup failed: check WAL, disk, retry
- Backup corrupt: restore from prior, investigate
- Off-host unavailable: retry, alert if >2 failures
- Restore failed: verify manifest + checksum + key
- VPS lost: provision new → restore from latest verified backup
- Signing key compromised: revoke → rotate → re-sign → audit

---

## 21. 3 Sub-Releases, 12 Deliverables

Consolidated to 2 files: contract + program document.

- HOS-4D.4C.1: Backup creation + encryption + manifests
- HOS-4D.4C.2: Off-host storage + key custody + retention
- HOS-4D.4C.3: Restore engine + recovery testing + runbooks

## 22. Activation Blockers Addressed

| Blocker | Status |
|---|---|
| Production key custody | ✅ Architecture designed |
| Off-host checkpoint storage | ✅ Architecture designed |
| Backup and recovery | ✅ Architecture designed |

## Remaining: ~10 (Caddy/systemd staging, migration runner, TOCTOU, live-mutation review, final activation)

---

*Planning only. No real backups. No production keys. No activation.*