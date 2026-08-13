# HOS-AUTO-01 — Authority Model

**Design only.**

---

## 1. Authority Classes

Every operation in a task contract maps to exactly one authority class. Classification happens **before** execution. The executor cannot reclassify.

### 1.1 AUTO — Execute without human approval

Read-only, reversible, or disposable operations that cannot affect production.

| Operation | Notes |
|---|---|
| Read-only inspection (`docker ps`, `docker inspect`, `journalctl`, `stat`, `cat` non-secret files) | No mutation |
| Test suite execution | Requires preflight validation first |
| Linting / type checking / compilation | Local or disposable |
| Disposable container runs (`docker run --rm` non-production) | Isolated |
| Local image builds (non-production tags) | No push to production |
| Log collection | Read-only |
| Evidence collection | Read-only |
| B5 lab operations (snapshot freshness tests on disposable reader) | Bounded scope |
| Documentation generation | No side effects |

**Constraints:**
- Must be reversible OR disposable.
- Must not touch `hermes-product-os-prod`, `hermes-phase-b-reader`, production DB, production snapshot, or production secrets.
- Must not consume production credentials.

### 1.2 GATED — Require Amjad authorization token

Production-impacting operations that are safe ONLY with explicit, single-purpose authorization.

| Operation | Notes |
|---|---|
| Production service restart | Token-scoped to a specific service |
| Production Compose/config modification | Token-scoped to a specific change |
| Production deployment (image swap) | Token-scoped + rollback required |
| Timer activation/deactivation | Token-scoped |
| Credential provisioning | Token-scoped, secrets never in contract |
| Persistent infrastructure change | Token-scoped |

**Constraints:**
- Requires a valid, unexpired, single-purpose authorization token.
- Token is bound to a specific `task_id` and `contract_sha256`.
- Token expires after one execution OR a short TTL (whichever first).

### 1.3 FORBIDDEN — Rejected, cannot reach executor

Operations that must never execute, regardless of authorization.

| Operation | Notes |
|---|---|
| Production mutation enablement (`MUTATIONS_DISABLED=false` in production) | GAP-001 violation |
| Production DB deletion | Destructive |
| Production snapshot deletion outside approved rollback | Destructive |
| Destructive migration | Irreversible without rollback |
| Constitution modification | Locked |
| Locked-decision modification | Locked |
| Unauthorized network exposure | Security boundary |
| Unauthorized privilege escalation | Security boundary |
| B7 activation without explicit Amjad authorization | Canary gate |

---

## 2. Authorization Tokens

### 2.1 Token Structure

```yaml
token_id: AUTH-2026-0041
scope: restart hermes-phase-b-reader
task_id: B5-FC06
allowed:
  - operation: docker_compose_restart
    target: hermes-phase-b-reader
    project: hermes-phase-b
forbidden:
  - image_change
  - db_mutation
  - network_change
  - credential_change
expires_at: 2026-08-13T11:00:00Z
approved_by: amjad
contract_sha256: <hash>
signature: <amjad-signature>
```

### 2.2 Token Properties

| Property | Value |
|---|---|
| Single-purpose | Bound to one task, one operation class |
| Expiring | Short TTL (minutes to hours) |
| Non-reusable | Consumed on first execution |
| Tamper-evident | Signed + SHA256 |
| Bound to contract | `contract_sha256` must match |
| Bound to task | `task_id` must match |

### 2.3 Token Lifecycle

```
Amjad creates token (scoped) → token signed → token stored
→ Hermes submits GATED contract with token
→ Bridge validates token (scope, expiry, signature, contract match)
→ Executor performs operation
→ Token consumed (invalidated)
```

---

## 3. Authority Matrix

| Operation | AUTO | GATED | FORBIDDEN |
|---|---|---|---|
| `docker ps`, `docker inspect` | ✅ | | |
| `journalctl` read | ✅ | | |
| Run test suite | ✅ | | |
| Disposable container | ✅ | | |
| Local image build (non-prod) | ✅ | | |
| Restart production service | | ✅ | |
| Modify production compose | | ✅ | |
| Production deployment | | ✅ | |
| Timer activate/deactivate | | ✅ | |
| Provision credentials | | ✅ | |
| Enable production mutations | | | ❌ |
| Delete production DB | | | ❌ |
| Modify Constitution | | | ❌ |
| Modify locked decisions | | | ❌ |
| Unauthorized network exposure | | | ❌ |
| B7 activation | | ✅ (explicit) | |

---

## 4. Authority Enforcement

The bridge enforces authority at **contract validation time**, before the executor runs anything. The executor additionally enforces at **runtime** via an operation allowlist.

**Two-layer enforcement:**
1. Bridge: classifies + validates contract against authority class.
2. Executor: allowlist of permitted commands per contract.

Neither layer can be bypassed by the agent.

---

## 5. Constitution Compatibility

The Hermes OS Constitution remains authoritative. HOS-AUTO-01 is an execution arm of Hermes — it has no independent authority:

- Hermes remains sole orchestrator.
- The bridge cannot create or approve task contracts (that's Hermes' authority).
- The bridge cannot reclassify authority.
- GATED operations require Amjad (or a Constitution-designated authority).
- FORBIDDEN operations are hard-blocked.

---

**Authority model design complete.**