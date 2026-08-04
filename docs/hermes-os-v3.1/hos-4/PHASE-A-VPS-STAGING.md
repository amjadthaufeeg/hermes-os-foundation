# Phase A — Private VPS Staging Plan

**Status:** Planning | **No VPS access authorized**

---

## 1. Recommendation

| Component | Recommendation |
|---|---|
| VPS provider | Hetzner CX22 or DigitalOcean Basic Droplet ($5-6/mo) |
| OS | Ubuntu 24.04 LTS (amd64) |
| Minimum spec | 1 vCPU, 2GB RAM, 20GB SSD |
| Private access | SSH key only, no password auth, UFW allow 22/80/443 from approved IPs |
| DNS | NOT required for Phase A (IP-based private access) |
| Public access | NO |

## 2. Deployment Sequence

1. Provision VPS, install Ubuntu 24.04
2. Create `hermes` user (non-root, no sudo)
3. Deploy application code via git clone
4. Create Python venv, install deps
5. Place secrets (env file, 0600, hermes-only)
6. Deploy systemd unit, enable
7. Deploy Caddy, validate private loopback
8. Configure UFW (SSH + Caddy port only)
9. Start service, verify health/readiness
10. Run staging restore exercise
11. Run incident exercises
12. Measure RPO/RTO
13. Produce Phase A evidence

## 3. Secrets Required

| Secret | Location | Permissions |
|---|---|---|
| GitHub OAuth client ID/secret | /opt/hermes/config/env | 0600 |
| Session secret | /opt/hermes/config/env | 0600 |
| CSRF secret | /opt/hermes/config/env | 0600 |
| Age public key (backup encryption) | /opt/hermes/config/age-pub.key | 0644 |
| Age private key (recovery only) | Amjad's offline custody | NOT on VPS |
| Checkpoint signing key | Separate KMS/restricted host | NOT on VPS |

## 4. Production Keys Required

| Key | Phase A Status |
|---|---|
| Age recovery private key | Amjad offline custody — test key for Phase A |
| Checkpoint Ed25519 signing key | Generate on VPS for staging, rotate for production |
| Storage writer credential | Test credential only (no real S3) |
| Storage recovery credential | Amjad controls |

## 5. Monitoring and Alerting

- Structured JSON logs → journald
- Prometheus metrics → local endpoint only
- Alert delivery: test Telegram or email (Amjad configures)
- Real external alert credentials required for Phase A

## 6. Exercise Matrix

| Exercise | Frequency |
|---|---|
| Service restart | Every deployment |
| Database restore | Weekly |
| Full recovery (backup→restore→verify) | Weekly |
| Incident: DB corruption | Monthly |
| Incident: storage unavailable | Monthly |
| Incident: key unavailable | Monthly |
| Rollback exercise | Before each deployment |

## 7. RPO/RTO Targets

| Metric | Target | Phase A Goal |
|---|---|---|
| RPO | ≤24h | Prove ≤24h in staging |
| RTO | ≤2h | Prove ≤2h in staging |

## 8. Amjad Actions Required

1. Provision VPS (or authorize Hermes to provision)
2. Configure DNS if needed (not required for Phase A)
3. Generate/provide age recovery keypair
4. Configure alert delivery destination
5. Authorize staging exercises
6. Review Phase A evidence
7. Authorize Phase B (production read-only)

## 9. Stop Conditions

- Real VPS configured without authorization → STOP
- Public access enabled → STOP
- Production credentials created prematurely → STOP
- Authoritative writes enabled → STOP
- Live mutations enabled → STOP

---

*Planning only. No VPS access, no production keys, no activation.*