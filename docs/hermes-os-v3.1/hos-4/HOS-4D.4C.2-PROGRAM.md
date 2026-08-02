# HOS-4D.4C.2 — Encryption, Off-Host Storage, Key Custody

**Status:** Planning | **No real keys, no real uploads**

---

## 1. Scope

Backup encryption (GPG), off-host S3-compatible storage, signing-key custody, credential separation matrix, object versioning/lock, upload/download contracts, encryption-key lifecycle, key rotation/revocation, backup catalog, retention enforcement.

## 2. Encryption Recommendation

**GPG asymmetric** — encrypt to dedicated recovery key. Private key held separately (offline or KMS). Simple, battle-tested, Stage 1 appropriate.

## 3. Off-Host Provider

**S3-compatible** (Backblaze B2 recommended) — object versioning, object lock, lifecycle rules, separate credentials. Cost ~$5/TB/month.

## 4. Signing-Key Custody

**Separate restricted host or KMS** — private key not on app VPS. Application can sign checkpoints via approved interface but cannot export key. Rotation: annual or on compromise.

## 5. Credential Separation Matrix

| Boundary | Writer | Delete | Restore | Sign | Decision Mutate |
|---|---|---|---|---|---|
| Backup writer | ✅ | ❌ | ❌ | ❌ | ❌ |
| Recovery operator | ❌ | ❌ | ✅ (Amjad) | ❌ | ❌ |
| Signing service | ❌ | ❌ | ❌ | ✅ | ❌ |
| Amjad | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hermes | ❌ | ❌ | ❌ | ❌ | ❌ |

## 6. Upload Contract

1. Verified local snapshot
2. Manifest verified
3. GPG encrypt
4. Checksum encrypted archive
5. Upload to S3
6. Verify remote checksum
7. Record object version
8. Verify object lock
9. Mark OFFHOST_VERIFIED
10. Remove plaintext temp

## 7. Backup States

ENCRYPTION_PENDING → ENCRYPTED → UPLOAD_PENDING → UPLOADED → OFFHOST_VERIFIED → RETENTION_LOCKED. Failure states: ENCRYPTION_FAILED, UPLOAD_FAILED, OFFHOST_VERIFICATION_FAILED.

## 8. Retention

Daily 30d, Weekly 12w, Monthly 12mo, Incident protected. Object lock via S3 governance mode. Last valid backup never auto-deleted.

## 9. Key Lifecycle

Generation → custody → rotation (annual) → revocation → historical verification. Compromised keys: inventory affected, re-encrypt if feasible, never rewrite history.

## 10. Alert Integration

CRITICAL: no valid off-host recovery point, signing key compromised. HIGH: upload failed, encryption failed, key unavailable.

---

*Planning only. No implementation, no real keys, no real uploads.*