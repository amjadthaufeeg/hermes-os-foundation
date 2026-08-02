# HOS-4D — Production Authentication and Activation Readiness

**Status:** Planning | **Release:** HOS-4D | **No deployment authorized**

---

## 1. Problem Statement

HOS-4C delivered a simulation-only security foundation. Authentication is SIMULATED, identity is not verified, deployment is not planned, and 12 blockers prevent live decision mutations. HOS-4D plans the production infrastructure needed to transform the simulation foundation into a secure, deployable, auditable system — without activating any mutation.

## 2. Scope

Production authentication architecture, verified identity binding, session security, secrets management, deployment architecture, authoritative source design, external audit checkpoint, monitoring, incident response, backup/recovery, activation gates.

## 3. Non-Scope

Implementation, deployment, mutation activation, OAuth configuration, production database migration, authoritative writes.

---

## 4. Activation Blocker Matrix (12/12 Addressed)

| # | Blocker | Current | Proposed Solution | Release | Dependencies |
|---|---|---|---|---|---|
| 1 | GitHub OAuth | NOT IMPLEMENTED | GitHub OAuth App + PKCE + redirect validation | HOS-4D.1 | GitHub App registration |
| 2 | Verified identity | NOT IMPLEMENTED | Immutable GitHub user ID binding + account-change audit | HOS-4D.1 | OAuth |
| 3 | Production sessions | NOT APPROVED | Server-side sessions, HTTP-only cookies, rotation, revocation | HOS-4D.2 | OAuth |
| 4 | Production deployment | NOT AUTHORIZED | FastAPI on managed VPS, TLS, env-based secrets | HOS-4D.2 | Sessions, secrets |
| 5 | Authoritative adapter | NOT IMPLEMENTED | Narrow mutation interface, version checks, audit consistency | HOS-4D.3 | Deployment, sessions |
| 6 | External audit checkpoint | NOT IMPLEMENTED | Git-committed signed hash checkpoint, daily | HOS-4D.4 | Adapter |
| 7 | Monitoring | NOT IMPLEMENTED | Auth failures, CSRF failures, audit-chain failures, alerts | HOS-4D.4 | Deployment |
| 8 | Incident response | NOT APPROVED | 14 incident definitions, emergency disable, kill switch | HOS-4D.4 | Monitoring |
| 9 | Backup/recovery | NOT APPROVED | Daily SQLite backup, encrypted, separated, restore-tested | HOS-4D.4 | Deployment |
| 10 | Live-mutation review | NOT COMPLETED | 7 independent review gates before activation | HOS-4D.5 | All above |
| 11 | Production secrets | NOT APPROVED | Environment variables, rotation policy, never in Git | HOS-4D.2 | Deployment |
| 12 | Final Amjad activation | NOT GRANTED | Separate explicit authorization after all gates pass | Final | HOS-4D.5 |

---

## 5. Authentication Recommendation

### Recommended: GitHub OAuth + Server Sessions

| Criterion | Assessment |
|---|---|
| Identity provider | GitHub OAuth App (amjadthaufeeg account) |
| Protocol | OAuth 2.0 with PKCE |
| Redirect | Strict allowlist: single production domain |
| Session storage | Server-side (SQLite or PostgreSQL) |
| Session expiry | 12h idle, 24h absolute |
| Cookie | HTTP-only, Secure, SameSite=Lax |
| Rotation | After login and privilege escalation |
| Revocation | Server-side, immediate |
| Re-auth | Required for APPROVE/REJECT (5-min window) |

### Alternatives

| Option | Verdict | Reason |
|---|---|---|
| Passkeys | Future upgrade | More secure, but enrollment complexity for solo operator |
| GitHub App | Overbuilt | Multi-user; single-user OAuth is simpler |
| Static API key | Rejected | No session, no audit, no revocation |

**Recommendation:** GitHub OAuth for HOS-4D. Passkeys as HOS-4D+ upgrade.

## 6. Verified Identity Binding

- **Immutable provider ID:** GitHub numeric user ID (`id` field), not username
- **Approved binding:** `github_user_id: 12345678` → `actor: amjad`
- **Account change:** Requires manual re-binding, audited event, old binding invalidated
- **Recovery:** GitHub account recovery + manual verification if needed
- **Emergency:** Amjad can designate a recovery method via out-of-band verification

Server denies mutations unless `authenticated_github_user_id == approved_owner_id`.

## 7. Session Security

- Storage: Server-side table with session_id, actor_id, role, created, expires, csrf_token
- Encryption: Session ID via `secrets.token_hex(32)`
- Idle timeout: 12 hours
- Absolute timeout: 24 hours
- Concurrent sessions: Allowed (single user), visible
- Suspicious: IP/location change → re-auth required
- Theft response: Revoke all sessions, alert, audit

No client-held JWT role claims. Server re-checks role on every mutation.

## 8. Authorization Model (Preserved from HOS-4C)

| Role | APPROVE | REJECT | DEFER | HOLD | RESUME | RETURN |
|---|---|---|---|---|---|---|
| AMJAD_OWNER | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| REVIEWER | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| CONTRIBUTOR | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| HERMES_ASSISTANT | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SYSTEM_SERVICE | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Hermes approval authority: **0**. Enforced at middleware.

### High-Risk Actions

| Action | Re-auth | Typed Confirm | Rationale | Cooldown |
|---|---|---|---|---|
| APPROVE | Yes | `APPROVE <DEC-ID>` | ≥50 chars | 3s |
| REJECT | Yes | `REJECT <DEC-ID>` | ≥50 chars | 3s |
| DEFER | No | No | ≥20 chars | — |
| HOLD | No | No | ≥20 chars | — |
| RESUME | No | No | ≥20 chars | — |

## 9. Authoritative Source Recommendation

### Recommended: Git-Backed YAML + SQLite Operational Store

- **Canonical:** `.hermes/registers/decisions/DEC-*.yaml` in Git
- **Operational:** SQLite for fast reads, audit chain, concurrency
- **Sync direction:** API writes to SQLite; periodic Git commit snapshots
- **No conflict:** Dashboard reads from API; Git is the archive and backup

### Alternatives

| Option | Verdict |
|---|---|
| SQLite-only | Loses Git history, disaster recovery |
| Git-only | No concurrency, slow reads for dashboard |
| PostgreSQL | Overkill for single-user Stage 1 |

## 10. Authoritative Adapter

Narrow interface:

```
POST /api/v1/decisions/{id}/actions
  → validates auth, role, state, version
  → executes mutation in SQLite transaction
  → records audit event
  → returns new state + audit reference
```

- Fails closed: invalid transition → 400, unauthorized → 403, stale → 409
- Emergency disable: feature flag, server-side, not browser-controllable
- Hermes: ZERO access to mutation endpoints (JWT role check)

## 11. External Audit Checkpoint

- **Frequency:** Daily
- **Method:** SHA-256 hash of last audit event + timestamp → signed → committed to Git
- **Verification:** Compare checkpoint hash with SQLite hash chain tip
- **Missed checkpoint:** Alert within 1 hour
- **Compromise:** Investigate + verify entire chain from last known-good checkpoint

## 12. Secrets Management

| Secret | Storage | Rotation | Backup |
|---|---|---|---|
| GitHub OAuth client ID/secret | Environment variables | 90 days | Encrypted backup |
| Session signing key | Environment variable | 90 days | Encrypted backup |
| CSRF secret | Derived from session key | With session key | — |
| Database credentials | Environment variable | 180 days | Encrypted backup |
| Deployment key | Managed by provider | Provider-managed | — |

**Rule:** No secret in Git. All secrets via environment variables or managed service.

## 13. Deployment Recommendation

### Recommended: Single VPS + FastAPI + SQLite

| Criterion | Assessment |
|---|---|
| Provider | Hetzner, DigitalOcean, or similar |
| OS | Ubuntu LTS |
| Python | 3.11+ |
| TLS | Let's Encrypt via Caddy or nginx |
| Process | systemd service |
| Cost | ~$5-10/month |
| Complexity | Low — single server, single file DB |

### Alternatives

| Option | Verdict |
|---|---|
| Serverless (Vercel) | Cold starts, no persistent SQLite |
| Managed container | Higher cost, operational overhead |
| PaaS (Heroku) | Convenient but vendor lock-in |

## 14. Database Recommendation

### Recommended: SQLite for Stage 1

- Single-user, single-writer — no concurrency contention
- Zero operational overhead
- File-based backups trivial
- Migration to PostgreSQL possible if needed later

**Hard requirement:** WAL mode, foreign keys enforced, daily backups.

## 15. Monitoring and Alerting

| Alert | Trigger | Severity | Channel |
|---|---|---|---|
| Auth failure spike | ≥5 in 5 min | HIGH | In-app + future email |
| CSRF failure spike | ≥10 in 5 min | HIGH | In-app |
| Audit chain failure | verify fails | CRITICAL | Immediate in-app |
| Missed checkpoint | >25h since last | HIGH | In-app |
| Database error | Any write failure | HIGH | In-app |
| Service down | Health check fail | CRITICAL | In-app |
| Hermes approval attempt | Any | CRITICAL | Immediate audit |

## 16. Incident Response (14 Incidents)

Each incident defined with: detection, containment, emergency disable, evidence preservation, recovery, post-incident review.

| # | Incident | Emergency Disable |
|---|---|---|
| 1 | OAuth compromise | Revoke tokens + disable OAuth |
| 2 | GitHub account compromise | Disable all mutations |
| 3 | Session theft | Revoke all sessions |
| 4 | Leaked secrets | Rotate all secrets |
| 5 | Unauthorized action | Disable mutations + audit |
| 6 | Audit chain failure | Disable mutations + verify |
| 7 | Database corruption | Restore from backup |
| 8 | Source conflict | Disable adapter + investigate |
| 9 | Deployment compromise | Disable service + redeploy |
| 10 | Service outage | Deploy standby |
| 11 | Backup failure | Alert + manual backup |
| 12 | False approval/rejection | REOPEN corrective action |
| 13 | Hermes boundary violation | Disable + audit + report |
| 14 | Emergency kill switch | Immediate mutation disable |

**Kill switch:** Server-side env var `MUTATIONS_DISABLED=true`. All mutation endpoints return 503. Read-only dashboard remains operational. Activated by Amjad. Audited.

## 17. Delivery Sequence

| Release | Scope | Depends On |
|---|---|---|
| **HOS-4D.1** | GitHub OAuth, identity binding, sessions | OAuth App registration |
| **HOS-4D.2** | Deployment, secrets, TLS, production config | HOS-4D.1 |
| **HOS-4D.3** | Authoritative adapter, database migration | HOS-4D.2 |
| **HOS-4D.4** | Audit checkpoint, monitoring, backup/recovery | HOS-4D.3 |
| **HOS-4D.5** | Security validation, incident response, activation checklist | HOS-4D.4 |
| **Final** | Amjad activation authorization | HOS-4D.5 all gates green |

## 18. Activation Checklist (24 gates)

- [ ] GitHub OAuth configured and tested
- [ ] Identity binding verified (exact user ID match)
- [ ] Production sessions with rotation and revocation
- [ ] CSRF enforced in production config
- [ ] All 42 tests pass in production configuration
- [ ] Deployment accessible via TLS
- [ ] Secrets loaded from environment (none in Git)
- [ ] Authoritative adapter connected to decision register
- [ ] Optimistic concurrency prevents stale writes
- [ ] Idempotency prevents duplicate mutations
- [ ] Audit hash chain INTACT
- [ ] External checkpoint committed to Git
- [ ] Monitoring alerts configured and tested
- [ ] Incident response reviewed
- [ ] Emergency disable tested
- [ ] Backup restored successfully
- [ ] Rollback tested
- [ ] Independent architecture review: PASS
- [ ] Independent auth review: PASS
- [ ] Independent security review: PASS
- [ ] Independent operational review: PASS
- [ ] Independent visual review: PASS
- [ ] Zero BLOCKER findings
- [ ] Zero HIGH findings

## 19. HOS-4B Follow-Up Disposition

| ID | Disposition |
|---|---|
| HOS-4B-FOLLOWUP-001 (MEDIUM) | HOS-4B.1 maintenance release |
| HOS-4B-FOLLOWUP-002 (LOW) | HOS-4B.1 maintenance release |

---

*Planning only. No deployment, no OAuth, no activation.*