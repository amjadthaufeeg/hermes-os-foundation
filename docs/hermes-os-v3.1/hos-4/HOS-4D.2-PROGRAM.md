# HOS-4D.2 — Production Sessions, Secrets and Deployment Foundation

**Status:** Planning | **Release:** HOS-4D.2 | **No deployment authorized**

---

## 1. Problem Statement

HOS-4D.1 delivered production-intent GitHub OAuth and verified owner identity. The service runs locally with simulation-mode defaults, temporary SQLite, and no deployment architecture. HOS-4D.2 plans the secure runtime foundation needed for protected deployment — sessions, secrets, TLS, hardening, and staging. No activation.

## 2. Scope

Production session policy, cookie security, secrets management, TLS/network, deployment topology, database persistence, migrations, service hardening, staging environment, deployment runbook.

## 3. Non-Scope

Deployment, authoritative adapter, live mutations, monitoring implementation, backup activation, final activation.

---

## 4. Environment Model (5 environments)

| Environment | Auth Mode | OAuth | Sim Login | DB | TLS | Mutations | Exposure |
|---|---|---|---|---|---|---|---|
| LOCAL_TEST | Test | No | ✅ | Temp | No | SIMULATION | localhost only |
| LOCAL_SIMULATION | Simulation | No | ✅ | Temp | No | SIMULATION | localhost only |
| AUTH_REVIEW | Review | Yes (local) | No | Temp | No | SIMULATION | localhost + OAuth callback |
| STAGING | Protected | Yes | No | Persistent | Yes | SIMULATION | Private network |
| PRODUCTION | Protected | Yes | No | Persistent | Yes | SIMULATION (HOS-4D.5) | Public (restricted) |

**Boundaries:** Simulated login unavailable in STAGING/PRODUCTION. Authoritative writes=0 in all environments. Browser cannot select environment. Missing config fails closed. PRODUCTION requires all configuration present.

---

## 5. Deployment Recommendation

### Recommended: Single VPS + Caddy + FastAPI + SQLite (WAL)

| Criterion | Assessment |
|---|---|
| Provider | Hetzner CX22 (2 vCPU, 4GB, €4/month) or DigitalOcean ($6/month) |
| OS | Ubuntu 24.04 LTS |
| TLS | Caddy (automatic Let's Encrypt) |
| Proxy | Caddy reverse proxy → Uvicorn |
| Process | systemd service |
| Database | SQLite WAL mode, single writer |
| Cost | ~$5-7/month |
| Complexity | Low — single server, zero orchestration |

### Alternatives — Rejected

| Option | Reason |
|---|---|
| Docker/containers | Adds complexity without Stage 1 benefit |
| Managed PaaS (Heroku) | Vendor lock-in, higher cost at scale |
| Serverless (Vercel/Functions) | No persistent SQLite, cold starts |
| Multi-server | Unnecessary for single-user Stage 1 |

---

## 6. Production Session Policy

| Parameter | Recommended | Rationale |
|---|---|---|
| Idle timeout | 12 hours | Workday + buffer |
| Absolute timeout | 24 hours | Daily re-auth cycle |
| Re-auth window | 5 minutes | High-risk actions need fresh auth |
| Session rotation | On login + re-auth | Prevent fixation |
| Concurrent sessions | Unlimited (single user) | Practical; audit if needed |
| Session store | SQLite `sessions` table | Co-located, zero latency |
| Cleanup interval | Hourly | Remove expired sessions |
| Cookie: HTTP-only | True | No JS access |
| Cookie: Secure | True (production) | TLS only |
| Cookie: SameSite | Lax | CSRF protection + usability |
| Cookie prefix | `__Host-` where feasible | Additional binding |

---

## 7. Session Storage: SQLite — Acceptable for Stage 1

**Reasons:** Single writer, no concurrency contention, zero operational overhead, co-located with audit DB, backups trivial.

**Migration threshold to PostgreSQL:** Multiple service instances, sustained concurrent writes, replication requirement, >100 req/s sustained, availability >99.9%.

---

## 8. Secrets Management

| Secret | Source (Production) | Rotation | Backup |
|---|---|---|---|
| GITHUB_CLIENT_ID | Environment variable | 90 days | Encrypted backup |
| GITHUB_CLIENT_SECRET | Environment variable | 90 days | Encrypted backup |
| APPROVED_OWNER_GITHUB_ID | Environment variable | On identity change | Encrypted backup |
| Session key | `secrets.token_hex()` at startup | Per restart | N/A (ephemeral) |
| CSRF secret | Derived per session | Per session | N/A |
| Database credentials | N/A (SQLite, no password) | — | — |
| TLS cert | Caddy-managed | Automatic (90d) | N/A |

**Rule:** No secret in Git. All via environment variables. `.env` files in `.gitignore`. Production `.env` outside web root.

---

## 9. Key Rotation

| Key | Frequency | Impact | Rollback |
|---|---|---|---|
| OAuth client secret | 90 days | None (active tokens valid) | Revert env var |
| Session key | Per restart | Invalidates all sessions | N/A (new key on next restart) |
| TLS cert | Auto (Caddy) | None | Auto-renew |

---

## 10. TLS and Network

- **Termination:** Caddy (Let's Encrypt)
- **Redirect:** HTTP → HTTPS (permanent)
- **HSTS:** `max-age=63072000; includeSubDomains; preload`
- **TLS:** 1.2 minimum, 1.3 preferred
- **Proxy:** Caddy → `127.0.0.1:8420` (Uvicorn)
- **Firewall:** UFW — allow 22, 80, 443; deny all else
- **SSH:** Key-only, no root login, non-standard port (optional)

---

## 11. Caddy Configuration (Template)

```
hermes.example.com {
    reverse_proxy 127.0.0.1:8420
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        -Server
    }
}
```

---

## 12. Process Management

- **systemd service:** `/etc/systemd/system/hermes.service`
- **User:** `hermes` (non-root, system user)
- **Working directory:** `/opt/hermes`
- **Exec:** `uvicorn backend.hos4c.main:app --host 127.0.0.1 --port 8420`
- **Restart:** `on-failure`, 5s delay
- **Environment:** loaded from `/opt/hermes/.env` (chmod 600)

---

## 13. Database Persistence

- **Path:** `/opt/hermes/data/audit.db`
- **Owner:** `hermes:hermes`
- **Permissions:** `600`
- **WAL:** Enabled (`PRAGMA journal_mode=WAL`)
- **Foreign keys:** Enforced (`PRAGMA foreign_keys=ON`)
- **Backup:** Daily `sqlite3 .backup` → `/opt/hermes/backups/`

---

## 14. Migrations

| Version | Migration | Rollback |
|---|---|---|
| V1 | Current schema | N/A (baseline) |
| V2+ | Forward SQL in `migrations/` | Reverse SQL, rollback tested |

**Process:** Backup → migration → verify → commit migration record. Failed migration → rollback + restore backup.

---

## 15. Configuration Validation (Startup)

Startup must verify: environment name valid, OAuth client configured, owner ID configured, DB accessible, WAL mode, foreign keys ON, no open debug mode, no open API docs.

**Fail closed:** Missing production config → refuse startup.

---

## 16. Mutation-Disable Enforcement

`MUTATIONS_DISABLED=true` (default). All `/api/decisions/{id}/actions` return 503. Read-only dashboard remains operational. Browser cannot toggle. Toggle audited.

---

## 17. Service Hardening

- Non-root `hermes` user
- Application files: read-only (`chmod 500`, owner root)
- DB directory: `chmod 700`, owner hermes
- `.env`: `chmod 600`, owner hermes
- `systemd` hardening: `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`
- Dependencies pinned: `fastapi`, `uvicorn`, `requests` with exact versions
- OS: unattended-upgrades for security patches

---

## 18. API Hardening

- Debug: disabled in STAGING/PRODUCTION
- /docs: disabled in STAGING/PRODUCTION
- Request size limit: 1MB
- Timeout: 30s per request
- Rate limit: 60 req/min per IP (future; HOS-4D.4)
- CORS: `127.0.0.1` only
- Trusted host: configured domain

---

## 19. Logging

- Startup, shutdown, OAuth failures, session create/revoke, CSRF deny, auth deny, error, DB error, mutation-disable enforcement
- **Never log:** tokens, secrets, cookies, CSRF tokens, verifiers

---

## 20. Health Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness — always returns 200 if process alive |
| `GET /api/health/ready` | Readiness — DB connectivity, schema version, config valid, mutation-disabled confirmed |

---

## 21. Staging Environment

- Separate VPS or local VM
- Separate GitHub OAuth App (staging callback URI)
- Separate DB (`/opt/hermes-staging/data/`)
- Mutations: DISABLED
- Network: IP-restricted
- Reset: `rm audit.db && restart`

---

## 22. Deployment Runbook (8 steps)

1. Pre-deployment backup (`sqlite3 .backup`)
2. Validate config (startup check)
3. Install secrets (`.env`)
4. Install dependencies (`pip install -r requirements.txt`)
5. Run migrations
6. Start service (`systemctl start hermes`)
7. Health check (liveness + readiness)
8. Verify (OAuth login → session → simulation action → logout)

---

## 23. Rollback

```bash
systemctl stop hermes
git checkout <previous-commit>
# Restore database backup if schema changed
systemctl start hermes
# Verify health
```

Audit events preserved. Sessions invalidated on restart.

---

## 24. Validation Plan

Startup valid/invalid config, TLS, cookie security, session persist/revoke, OAuth callback, CSRF, restart, DB lock, rollback, simulation action, zero writes, zero Hermes authority.

---

## 25. Activation Blockers Affected

| Blocker | Status |
|---|---|
| Production session config | ✅ Planned (not approved) |
| Production secrets config | ✅ Planned (not approved) |
| Production deployment | ✅ Architecture designed (not authorized) |

## Blocker Remaining: 7

Authoritative adapter, audit checkpoint, monitoring, IR, backup/recovery, live-mutation review, final activation.

---

## 26. Deliverables (12 → 2 files consolidated)

1. TASK-HOS-4D-2.yaml ✅
2. HOS-4D.2-PROGRAM.md (this document — sections 3-12 of planning) ✅

---

*Planning only. No deployment. No activation.*