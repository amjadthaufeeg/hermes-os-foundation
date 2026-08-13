# HOS-AUTO-01 — Evidence Receipt Specification

**Design only.**

---

## 1. Receipt Format

```json
{
  "receipt_version": "1.0",
  "task_id": "B5-FC06",
  "execution_id": "exec-20260813-0001",
  "authority_class": "AUTO",
  "contract_sha256": "abc123...",
  "source_sha": "60e47d0ca8798139b7cc3b95f77dfb265fdad4b2",
  "executor_identity": "executor-01",
  "started_at": "2026-08-13T10:30:00Z",
  "finished_at": "2026-08-13T10:31:05Z",
  "duration_seconds": 65,

  "operations": [
    {"type": "docker_exec", "target": "hermes-phase-b-reader", "command": ["python3", "-c", "..."]}
  ],

  "assertions": [
    {"id": "A1", "check": "http_status", "expect": 503, "actual": 503, "passed": true},
    {"id": "A2", "check": "decision_count_unchanged", "expect": true, "actual": true, "passed": true}
  ],

  "state_change": {
    "production_changed": false,
    "production_db_changed": false,
    "b4_reader_changed": false
  },

  "verdict": "PASS",

  "artifacts": {
    "stdout": "artifacts/exec-20260813-0001/stdout.log",
    "stderr": "artifacts/exec-20260813-0001/stderr.log",
    "before": "artifacts/exec-20260813-0001/before.json",
    "after": "artifacts/exec-20260813-0001/after.json",
    "assertions": "artifacts/exec-20260813-0001/assertions.json",
    "manifest": "artifacts/exec-20260813-0001/manifest.json"
  },

  "previous_receipt_sha256": "def456...",
  "receipt_sha256": "xyz789..."
}
```

---

## 2. Receipt Fields

| Field | Purpose |
|---|---|
| `execution_id` | Unique, monotonic |
| `contract_sha256` | Bind receipt to contract |
| `source_sha` | Pin source identity |
| `executor_identity` | Who ran it |
| `assertions[]` | Machine-evaluated results |
| `state_change` | Production/B4 impact flag |
| `verdict` | PASS / FAIL / STOP / TEST_ENVIRONMENT_INVALID |
| `artifacts` | Paths to captured evidence |
| `previous_receipt_sha256` | Chain integrity |
| `receipt_sha256` | Self-hash |

---

## 3. Verdict Values

| Verdict | Meaning |
|---|---|
| `PASS` | All assertions met |
| `FAIL` | ≥1 assertion failed (STOP, no auto-retry) |
| `STOP` | Unexpected anomaly |
| `TEST_ENVIRONMENT_INVALID` | Preflight failed — environment incomplete |

---

## 4. Tamper-Evidence

- Each receipt contains `receipt_sha256` = SHA256 of all fields except itself.
- Each receipt contains `previous_receipt_sha256` = the previous receipt's hash.
- Chain: receipt N references receipt N-1. Tampering with any receipt breaks the chain.
- Evidence artifacts are hashed at capture time; hashes recorded in `manifest.json`.

---

## 5. Redaction Rules

Before storing artifacts, redact:

- `authorization` headers
- `cookie` values
- `x-api-key`, `x-csrf-token`
- `token`, `secret`, `password`, `key`, `credential`
- `private_key`, `signing_key`, `access_token`

Redacted values replaced with `[REDACTED]`.

---

## 6. Storage

- Evidence store: `/opt/hermes-auto/evidence/` (append-only).
- Receipts: `/opt/hermes-auto/receipts/` (chained).
- Artifacts: `/opt/hermes-auto/evidence/<execution_id>/`.
- Root-owned, mode 700. Hermes reads via bridge, not direct filesystem.

---

## 7. Retention

| Artifact | Retention |
|---|---|
| Receipts | Indefinite (audit trail) |
| stdout/stderr logs | 90 days |
| before/after state | 90 days |
| Full evidence | 90 days (then archived/hashed) |

---

**Evidence receipt specification complete.**