# HOS-4D.4C.3 — Restore and Recovery Verification

**Status:** Planning | **No production restore authorized**

---

## 1. Problem Statement

HOS-4D.4C.1 proved backup creation. HOS-4D.4C.2 proved asymmetric encryption and off-host storage. No production restore has been exercised. HOS-4D.4C.3 completes the backup/recovery chain by proving controlled decryption, database restore, audit/checkpoint reconciliation, session invalidation, and measured RPO/RTO in isolated test mode.

## 2. Recovery Authority

| Role | May | May Not |
|---|---|---|
| Amjad | Approve recovery point, authorize restore, re-enable | — |
| Restore operator | Retrieve, decrypt, restore, produce evidence | Approve own point, enable mutations, delete backups |
| Hermes | List metadata, summarize candidates, report failures | Select point, access private key, decrypt, restore, enable |

## 3. Recovery Workflow (24 steps)

1. Recovery request → 2. Amjad approval → 3. Select recovery point → 4. Verify storage metadata → 5. Verify object version → 6. Verify encrypted checksum → 7. Verify manifest → 8. Download to isolated directory → 9. Make private identity available → 10. Decrypt → 11. Verify decrypted content → 12. Create restore destination → 13. Restore database → 14. SQLite integrity check → 15. Validate schema → 16. Verify data → 17. Reconcile audit chain → 18. Reconcile checkpoint chain → 19. Invalidate sessions → 20. Confirm mutations disabled → 21. Generate evidence → 22. Remove private key → 23. Clean plaintext → 24. Mark VERIFIED_TEST_ONLY

## 4. Recovery States

REQUESTED → AWAITING_APPROVAL → APPROVED → RECOVERY_POINT_SELECTED → DOWNLOAD_PENDING → DOWNLOADED → DOWNLOAD_FAILED → ARCHIVE_VERIFIED → DECRYPTION_PENDING → DECRYPTED → DECRYPTION_FAILED → RESTORE_PENDING → RESTORED → RESTORE_FAILED → DATA_VERIFIED → RECONCILIATION_FAILED → SESSIONS_INVALIDATED → MUTATIONS_CONFIRMED_DISABLED → VERIFIED_TEST_ONLY → ABORTED → CORRUPT → KEY_UNAVAILABLE

## 5. Key Validations

- **Database**: SQLite integrity, schema version, migrations, foreign keys, row counts, expected data
- **Audit**: Chain head match, continuity, no rewritten history
- **Checkpoint**: Reference match, signing key ID, historical public key available
- **Sessions**: All restored sessions invalidated, stale cookies rejected, owner must re-authenticate
- **Mutations**: Confirmed disabled throughout, Hermes=0, no auto-re-enable

## 6. RPO/RTO

| Metric | Target | Status |
|---|---|---|
| RPO | ≤24h | NOT YET PROVEN |
| RTO | ≤2h | NOT YET PROVEN |

Post-4C.3: RTO_ISOLATED_TEST_TARGET_MET / NOT_MET. Production RTO requires HOS-4D.4D.

## 7. Failure Scenarios

Wrong key, missing key, revoked key, corrupted ciphertext, truncated archive, checksum mismatch, manifest mismatch, partial download, insufficient disk, invalid database, schema mismatch, audit mismatch, checkpoint mismatch, session invalidation failure, mutation-disable failure.

## 8. Real Provider Boundary

HOS-4D.4C.3 uses isolated local S3-compatible test storage only. Real provider credentials remain NOT CONFIGURED. HOS-4D.4C.2-FOLLOWUP-002 remains OPEN for HOS-4D.4D.

## 9. Tests

Recovery selection (7), retrieval/decryption (9), database restore (8), reconciliation (7), session invalidation (5), mutation safety (5), timing (5), isolation (7). All 217 existing tests must remain green.

## 10. Reviews

Technical, security, operational, recovery — all required. 0 BLOCKER, 0 HIGH before merge.

---

*Planning only. No production restore, no real keys, no real credentials, no activation.*