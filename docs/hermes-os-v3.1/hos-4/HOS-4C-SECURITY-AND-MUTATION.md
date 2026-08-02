# HOS-4C — Controlled Decision Actions

**Status:** Planning — no implementation authorized | **Risk:** R3 | **Stage:** STAGE_1

---

## 1. Problem Statement

HOS-4A and HOS-4B provide read-only decision browsing and evidence inspection. Decisions are displayed as `DECISION REQUIRED` with `NOT IMPLEMENTED — REQUIRES HOS-4C`. Amjad cannot act on decisions through the interface.

HOS-4C designs the secure, auditable mutation system that will eventually allow Amjad to approve, reject, defer, hold, resume, or return decisions — while ensuring Hermes never acts autonomously.

## 2. Scope

Complete security architecture, state machine, threat model, audit specification, backend recommendation, and UI specification. No code. No activation.

## 3. Non-Scope

Implementation, authentication deployment, backend deployment, mutation activation, autonomous decisions, loop/capability activation.

## 4. Decision Actions

| Action | Source States | Target State | Irreversible | Rationale | Re-auth |
|---|---|---|---|---|---|
| **APPROVE** | AWAITING_AMJAD, IN_REVIEW | APPROVED | Yes | Mandatory | Yes |
| **REJECT** | AWAITING_AMJAD, IN_REVIEW | REJECTED | Yes | Mandatory | Yes |
| **DEFER** | AWAITING_AMJAD, IN_REVIEW, HOLD | DEFERRED | No (can resume) | Mandatory | Recommended |
| **PLACE_ON_HOLD** | AWAITING_AMJAD, IN_REVIEW | HOLD | No | Mandatory | No |
| **RESUME** | HOLD, DEFERRED | AWAITING_AMJAD | No | Mandatory | No |
| **RETURN_FOR_REVISION** | IN_REVIEW | RETURNED | No | Mandatory | No |

**Hermes may recommend but NEVER approve, reject, defer, hold, resume, or return.** This is enforced at the server authorization layer.

## 5. State Machine

```
PROPOSED ──(submit)──→ AWAITING_AMJAD
AWAITING_AMJAD ──(APPROVE)──→ APPROVED ──→ CLOSED
AWAITING_AMJAD ──(REJECT)──→ REJECTED ──→ CLOSED
AWAITING_AMJAD ──(DEFER)──→ DEFERRED
AWAITING_AMJAD ──(PLACE_ON_HOLD)──→ HOLD
IN_REVIEW ──(APPROVE)──→ APPROVED
IN_REVIEW ──(RETURN_FOR_REVISION)──→ RETURNED
HOLD ──(RESUME)──→ AWAITING_AMJAD
DEFERRED ──(RESUME)──→ AWAITING_AMJAD
APPROVED ──(CLOSE)──→ CLOSED
REJECTED ──(CLOSE)──→ CLOSED
BLOCKED ──(RESOLVE)──→ AWAITING_AMJAD

Corrective: APPROVED ──(REOPEN)──→ AWAITING_AMJAD
Corrective: CLOSED ──(REOPEN)──→ AWAITING_AMJAD
```

### Mapping to Frozen HOS-3 Semantic Statuses

| Workflow State | Display Status | Token | Icon |
|---|---|---|---|
| PROPOSED | PROPOSED | Muted | ◌ |
| AWAITING_AMJAD | AWAITING_AMJAD | Gold | ◆ |
| IN_REVIEW | IN_REVIEW | Cyan | ⬡ |
| HOLD | HOLD | Amber | ◇ |
| APPROVED | CLOSED | Green | ✓ |
| REJECTED | CLOSED | Green | ✓ |
| DEFERRED | HOLD | Amber | ◇ |
| RETURNED | IN_REVIEW | Cyan | ⬡ |
| BLOCKED | BLOCKED | Red | ✗ |

No new semantic tokens. Frozen HOS-3 baseline preserved.

## 6. Authentication Recommendation

### Recommended: GitHub OAuth + Session Backend

| Criterion | Assessment |
|---|---|
| Identity source | GitHub account (amjadthaufeeg) — existing, trusted |
| Session model | Server-side session, HTTPS-only cookie |
| Session expiry | 12 hours idle, 24 hours absolute |
| Re-auth for high-risk | APPROVE, REJECT require fresh GitHub OAuth re-confirmation |
| Recovery | Standard GitHub account recovery |
| Lockout | 5 failed attempts → 15-minute cooldown |
| Audit | Login/logout/re-auth events recorded |

**Rationale:** GitHub OAuth leverages existing identity infrastructure. No new credentials to manage. Amjad's GitHub account is already the authoritative source for repository access. Session backend can be a lightweight service (Node.js or Python) with SQLite or in-memory store for MVP.

### Alternatives Considered

| Option | Verdict | Reason |
|---|---|---|
| Passkey (WebAuthn) | Future upgrade | More secure but requires credential enrollment |
| Static API key | Rejected | No session, no expiry, no audit trail |
| GitHub App | Overbuilt for MVP | Better for multi-user; single-user is OAuth |

## 7. Authority and Permission Model

| Role | Approve | Reject | Defer | Hold | Resume | Return | Audit Read |
|---|---|---|---|---|---|---|---|
| **AMJAD_OWNER** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **REVIEWER** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **CONTRIBUTOR** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HERMES_ASSISTANT** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **SYSTEM_SERVICE** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Hermes has NO approval authority.** Enforced at server middleware — JWT claims checked per request. `role` claim must be `AMJAD_OWNER` for mutation endpoints.

## 8. Confirmation Model

### Standard Confirmation

Shows: decision ID, title, current state → resulting state, action label, rationale field, evidence summary.

### High-Risk Confirmation (APPROVE, REJECT)

Additional requirements:
- Re-authentication (fresh GitHub OAuth)
- Type "APPROVE" or "REJECT" to confirm
- Mandatory rationale ≥ 50 characters
- 3-second cooldown before submit activates

### Confirmation Panel UI

```
┌─────────────────────────────────────┐
│ DEC-HOS-001: Hermes sole orchestrator│
│ Current: AWAITING_AMJAD              │
│ Action: APPROVE → CLOSED             │
│                                      │
│ [Evidence summary with freshness]    │
│ ⚠ Stale evidence: None               │
│                                      │
│ Rationale (required):                │
│ ┌─────────────────────────────────┐  │
│ │                                 │  │
│ └─────────────────────────────────┘  │
│                                      │
│ Type "APPROVE" to confirm: [      ] │
│                                      │
│ [Cancel]        [APPROVE (3s)]      │
└─────────────────────────────────────┘
```

## 9. Mandatory Rationale Rules

| Action | Required | Min Length | Reason Codes | Editable | Correction |
|---|---|---|---|---|---|
| APPROVE | Yes | 50 chars | No | No — new event | REOPEN |
| REJECT | Yes | 50 chars | No | No — new event | REOPEN |
| DEFER | Yes | 20 chars | No | No — new event | RESUME |
| HOLD | Yes | 20 chars | No | No — new event | RESUME |
| RESUME | Yes | 20 chars | No | No — new event | RE-HOLD |
| RETURN | Yes | 20 chars | No | No — new event | Re-submit |

Rationale is immutable after recording. Corrections create new audit events referencing the original.

## 10. Audit-Event Schema

```yaml
audit_event:
  event_id: "AUD-20260802-001"         # UUIDv7
  event_type: "decision.approved"
  decision_id: "DEC-HOS-001"
  action: "APPROVE"
  actor_id: "amjadthaufeeg"
  actor_role: "AMJAD_OWNER"
  session_id: "sess-abc123"
  previous_state: "AWAITING_AMJAD"
  resulting_state: "APPROVED"
  rationale: "Verified governance model is correct..."
  reason_code: null
  decision_version: 3
  expected_version: 3
  idempotency_key: "idem-xyz789"
  request_timestamp: "2026-08-02T12:00:00Z"
  confirmation_timestamp: "2026-08-02T12:00:05Z"
  execution_timestamp: "2026-08-02T12:00:06Z"
  result: "success"
  failure_reason: null
  correlation_id: "corr-def456"
  client_context: "Hermes MC v1, Chrome 128, macOS 15"
  integrity_hash: "sha256:abc123..."
```

- **Append-only:** SQLite table with no UPDATE/DELETE permissions for application user
- **Ordering:** Monotonic event_id via UUIDv7 (time-ordered)
- **Tamper detection:** Integrity hash of previous event + current event, verified on read
- **Retention:** Indefinite; export as JSONL backup daily
- **Read:** AMJAD_OWNER, REVIEWER, HERMES_ASSISTANT roles

## 11. Concurrency and Stale-Record Protection

### Optimistic Concurrency

Every decision mutation request includes:
- `decision_id`
- `expected_version` (integer, increments on each write)
- `idempotency_key`

Server:
1. Read current decision version
2. If `current_version != expected_version` → reject with 409 Conflict + current state
3. If `idempotency_key` already processed → return cached result
4. Execute mutation, increment version, write audit
5. Return new version + new state

**Two-browser-tab protection:** Each tab loads the decision independently. First to submit wins. Second gets 409 Conflict → reloads current state → shows "Decision changed since you loaded it. Please review and reconfirm."

## 12. Idempotency

- **Key generation:** Client: `idem-{uuid}` per confirmation attempt
- **Validity:** 24 hours from first submission
- **Duplicate:** Returns 200 with original result (not 409)
- **Conflicting payload:** Same key, different rationale → reject 400 "idempotency key reused with different payload"
- **Audit:** Single event recorded; duplicate marked in `idempotency_key` index

## 13. Failure and Recovery

| Failure | Behaviour | Recovery |
|---|---|---|
| Auth failure | 401, no state change | Retry login |
| Authorization failure | 403, logged as security event | Hermes cannot self-approve |
| Stale version | 409, return current state | Reload, re-confirm |
| Invalid transition | 400, explain valid transitions | UI should not offer invalid paths |
| Missing rationale | 422, specify required fields | Fill rationale, retry |
| Audit write failure | 500, abort mutation | Retry; no partial state |
| Decision write failure | 500, abort mutation | Retry; audit not written |
| Network timeout | Client retry with same idempotency key | Server idempotency handles |
| Backend unavailable | Show error state in UI | Retry with backoff |

**Transactional guarantee:** Mutation + audit write in a single SQLite transaction. Both or neither. No partial state.

## 14. Corrective Actions

| Action | Reverses | New Audit | Preserves Original |
|---|---|---|---|
| **REOPEN** | APPROVED, REJECTED, CLOSED | Yes | Yes |
| **SUPERSEDE** | Any state | Yes (references original) | Yes |
| **REVERSE_WITH_REASON** | APPROVED, REJECTED | Yes (references original) | Yes |

Corrections never erase history. They create new transitions with references to prior events.

## 15. Threat Model (STRIDE)

| Threat | Asset | Attack Path | Impact | Mitigation | Residual |
|---|---|---|---|---|---|
| **Spoofing** | Amjad identity | Stolen GitHub token/OAuth session | Unauthorized approval | HTTPS-only cookies, token binding, audit logging | Low with session timeout |
| **Tampering** | Decision state | Direct SQLite write bypassing API | Silent corruption | File permissions, integrity hash chain, read-after-write verify | Low |
| **Repudiation** | Action traceability | Attacker claims "didn't do it" | Disputable actions | Immutable audit log with actor + session + timestamp | Very low |
| **Info Disclosure** | Decision rationale | SQL injection, error leakage | Sensitive context exposed | Parameterized queries, sanitized errors, HTTPS | Low |
| **DoS** | API availability | Flood idempotency keys | Service unavailable | Rate limiting (10/min per session), idempotency key TTL | Medium |
| **Elevation** | Hermes→Amjad | Hermes process obtains approval credentials | Autonomous decisions | Separate service accounts; Hermes has no approval-JWT signing key | Very low |

## 16. Backend Architecture Recommendation

### Recommended: Lightweight Dedicated API Service

| Criterion | Assessment |
|---|---|
| Language | Python (Flask/FastAPI) or Node.js (Express) |
| Database | SQLite (single-file, zero-config) |
| Auth | GitHub OAuth + signed JWT sessions |
| Deployment | Single process on existing infrastructure |
| Secrets | Environment variables, never in Git |
| Audit storage | SQLite table, append-only |
| Cost | Near-zero (existing infrastructure) |
| Complexity | Low — one service, one database file |

### Alternatives

| Option | Verdict |
|---|---|
| Serverless (Vercel Functions) | Higher latency, cold starts, audit durability concerns |
| GitHub-mediated (PR-based) | Too slow for real-time decisions, conflates code review with governance |
| Deno Deploy | Viable alternative if JavaScript preferred; similar characteristics |

## 17. Source of Truth

**Canonical:** Decision register YAML files in Git + append-only audit log in SQLite.

- Git: long-term record, version history, disaster recovery
- SQLite: current state, fast reads for Dashboard, audit trail
- Sync: API writes to SQLite; periodic Git commit of YAML snapshot (optional Phase 2)

No conflicting sources. Dashboard reads from API → API reads from SQLite. Git is archive, not operational source.

## 18. Human-Gate Enforcement

### Technical Enforcement

1. JWT `role` claim must be `AMJAD_OWNER` — verified at middleware
2. Hermes service account has `HERMES_ASSISTANT` role — cannot call mutation endpoints
3. APPROVE/REJECT require fresh OAuth token (≤ 5 minutes old)
4. Server validates: role, version, state, idempotency
5. Audit log records authenticated actor (not "system" or "Hermes")
6. All denials logged with reason
7. No automated token can possess `AMJAD_OWNER` role

## 19. Notification Model

| Event | Recipient | Channel | Timing |
|---|---|---|---|
| Action completed | Amjad (self) | In-app confirmation | Immediate |
| Action failed | Amjad (self) | In-app error | Immediate |
| Conflict detected | Amjad | In-app reload | Immediate |
| Evidence became stale | Amjad | In-app warning | Before confirmation |
| Unauthorized attempt | Amjad | Audit log + future alert | Immediate |

Phase 1: In-app only. Future: email/webhook.

## 20. UI Specification

### Action Bar (Decision Detail)

Shows eligible actions based on current state. Disabled actions show reason ("REQUIRES REVIEW FIRST").

### Confirmation Panel

Frozen HOS-3 design tokens. Gold for APPROVE, red accent for REJECT. Keyboard accessible. Screen-reader announces state change.

### Prototype Note

All UI specifications are NON-OPERATIONAL PROTOTYPES. No working controls exist.

## 21. HOS-4B Follow-Up Disposition

| ID | Recommendation |
|---|---|
| HOS-4B-FOLLOWUP-001 (MEDIUM) | Include in HOS-4C UI work — filter polish naturally fits action-readiness indicators |
| HOS-4B-FOLLOWUP-002 (LOW) | Handle via HOS-4B.1 maintenance release before HOS-4C implementation |

## 22. Implementation Readiness Checklist

- [ ] Amjad approves HOS-4C planning package
- [ ] Independent security review complete
- [ ] Backend service MVP built (not deployed)
- [ ] Auth flow tested locally
- [ ] Audit schema validated
- [ ] Threat model reviewed
- [ ] HOS-4B.1 maintenance complete
- [ ] Separate Amjad authorization for mutation activation

---

*Planning only. No mutations authorized. Requires separate Amjad activation approval.*