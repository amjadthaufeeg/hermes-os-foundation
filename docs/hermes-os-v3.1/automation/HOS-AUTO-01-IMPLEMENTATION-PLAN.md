# HOS-AUTO-01 — Implementation Plan (R1)

**DESIGN ONLY. Do not implement. Await Amjad authorization.**

---

## 1. Scope

Small, auditable R1. Single-node. No distributed system. No message queue. No public API.

---

## 2. Files / Components to Create

### 2.1 Directory Structure

```
/opt/hermes-auto/
├── bin/
│   ├── bridge.py              # Contract validation + dispatch + receipts
│   └── executor.py            # Sandboxed operation executor
├── contracts/
│   └── (submitted contracts, hashed)
├── evidence/
│   └── <execution_id>/
│       ├── stdout.log
│       ├── stderr.log
│       ├── before.json
│       ├── after.json
│       ├── assertions.json
│       └── manifest.json
├── receipts/
│   └── (chained receipt files)
├── tokens/
│   └── (single-use GATED tokens, signed)
├── policy/
│   ├── authority_matrix.yaml  # AUTO/GATED/FORBIDDEN mapping
│   └── operation_allowlist.yaml
├── config/
│   └── bridge.yaml            # paths, timeout, executor identity
└── logs/
    └── bridge.log
```

### 2.2 Source Components

| Component | Language | Purpose |
|---|---|---|
| `bridge.py` | Python | Contract validation, authority classification, preflight, receipt generation |
| `executor.py` | Python | Sandboxed operation execution via allowlist |
| `contract_schema.py` | Python | Strict contract schema validation |
| `authority.py` | Python | Authority classification engine |
| `receipt.py` | Python | Receipt generation + chaining + hashing |
| `preflight.py` | Python | Test environment validation |
| `redact.py` | Python | Secret redaction |

---

## 3. Executor Design

| Property | Value |
|---|---|
| Process UID | Dedicated `hermes-auto` user (non-root) |
| Capabilities | `cap_drop ALL`, `no-new-privileges` |
| Docker socket | NOT mounted by default |
| Network | `--network none` for disposable runs |
| Credentials | None in executor environment |
| Shell | No shell — `execve` argument arrays only |
| Allowlist | Enforced from `operation_allowlist.yaml` |

Executor supports these operation types:
- `docker_ps`, `docker_inspect`, `docker_exec` (read-only targets)
- `docker_run_rm` (disposable, network-isolated)
- `journalctl`, `read_file`, `stat`
- `run_test`, `run_lint`, `run_typecheck`
- GATED: `docker_compose_restart`, `docker_compose_up`

---

## 4. Policy Engine

- `authority_matrix.yaml` maps operation type → authority class.
- `operation_allowlist.yaml` maps authority class → allowed operation types.
- FORBIDDEN operations hardcoded in `authority.py` (not config-editable by agent).

---

## 5. Evidence Storage

- Append-only directory, root-owned, mode 700.
- Receipts SHA256-chained.
- Artifacts hashed at capture, hashes in manifest.
- Redaction pass before storage.

---

## 6. Receipt Format

See `HOS-AUTO-01-EVIDENCE-RECEIPT.md`.

---

## 7. Locking / Concurrency

- Per-task lock (`flock`) to prevent concurrent conflicting executions.
- Execution ID monotonic, collision-free.

---

## 8. Audit Logging

- Bridge logs every contract: `task_id`, `authority_class`, `verdict`, `receipt_sha256`.
- Logs root-owned, append-only, hashed periodically.

---

## 9. Installation Procedure

```bash
# (design only — not executed)
useradd -r -s /sbin/nologin hermes-auto
mkdir -p /opt/hermes-auto/{bin,contracts,evidence,receipts,tokens,policy,config,logs}
chown -R hermes-auto:hermes-auto /opt/hermes-auto/evidence /opt/hermes-auto/logs
chown root:root /opt/hermes-auto/bin /opt/hermes-auto/policy /opt/hermes-auto/config /opt/hermes-auto/receipts /opt/hermes-auto/tokens
chmod 700 /opt/hermes-auto/{receipts,tokens}
# Install source, set up authority matrix, generate executor identity
```

---

## 10. Rollback Procedure

```bash
# Remove the bridge entirely (no production dependency)
userdel hermes-auto
rm -rf /opt/hermes-auto
# Production containers, DB, snapshots untouched
```

---

## 11. Test Strategy

| Test | Coverage |
|---|---|
| Contract schema validation | Malformed, missing fields, unknown ops |
| Authority classification | AUTO/GATED/FORBIDDEN mapping |
| Command injection | Attempt injection via contract fields |
| Path traversal | Attempt `../../` escape |
| Symlink escape | Attempt symlink write |
| Env poisoning | Attempt `MUTATIONS_DISABLED=false` injection |
| Preflight | Missing dependency → TEST_ENVIRONMENT_INVALID |
| Receipt chaining | Tamper detection |
| Redaction | Secret leak prevention |
| STOP semantics | Failed assertion → STOP, no retry |

---

## 12. Acceptance Criteria

- [ ] Hermes can submit a structured contract without Amjad copying commands
- [ ] AUTO operations execute without human approval
- [ ] GATED operations require single-use token
- [ ] FORBIDDEN operations hard-blocked
- [ ] Every execution produces a tamper-evident receipt
- [ ] Expected results machine-checked
- [ ] FAIL → STOP, no auto-retry
- [ ] Preflight detects TEST_ENVIRONMENT_INVALID
- [ ] No Docker socket exposure
- [ ] No credential exposure
- [ ] Rollback tested

---

## 13. Implementation Effort Estimate

| Component | Effort |
|---|---|
| Contract schema + validation | 0.5 day |
| Authority engine | 0.5 day |
| Executor (sandbox + allowlist) | 1 day |
| Preflight | 0.5 day |
| Receipt + chaining | 0.5 day |
| Redaction | 0.25 day |
| Tests | 1 day |
| Installation + hardening | 0.5 day |
| **Total** | **~5 days** |

---

**Implementation plan complete. Awaiting Amjad authorization before any implementation.**