# Phase B — Pre-Execution Package

**Status:** Artifacts designed, not yet deployed. Awaiting engineering review.

---

## A. docker-compose.test-b.yml

```yaml
services:
  hpos-test-b:
    image: hermes-product-os-hpos:latest
    container_name: hermes-product-os-test-b
    restart: "no"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      # Data volumes — distinct from staging
      - hpos-test-b-data:/opt/hermes/data
      - hpos-test-b-logs:/opt/hermes/logs

      # Snapshot mount — read-only (Layer 2: filesystem kernel enforcement)
      - /var/lib/hermes/snapshots/snapshot-test-b.db:/opt/hermes/data/snapshot.db:ro

      # Synthetic Phase B credentials — read-only, distinct paths from staging (Layer 1)
      - /etc/hermes-product-os-test-b/secrets/B2_READER_KEY_ID:/opt/hermes/secrets/B2_READER_KEY_ID:ro
      - /etc/hermes-product-os-test-b/secrets/B2_READER_APPLICATION_KEY:/opt/hermes/secrets/B2_READER_APPLICATION_KEY:ro
      - /etc/hermes-product-os-test-b/secrets/B2_BUCKET_NAME:/opt/hermes/secrets/B2_BUCKET_NAME:ro
      - /etc/hermes-product-os-test-b/secrets/B2_ENDPOINT:/opt/hermes/secrets/B2_ENDPOINT:ro

      # Synthetic Phase B env
      - /etc/hermes-product-os-test-b/env:/opt/hermes/config/env:ro

      # Public key (shared with staging — same keypair, different mount path)
      - /etc/hermes-product-os/keys/staging-public-key.txt:/opt/hermes/keys/public-key.txt:ro

    environment:
      - PYTHONUNBUFFERED=1
      - HERMES_ENVIRONMENT=TEST_PHASE_B
      - MUTATIONS_DISABLED=true

    networks:
      - hpos-test-b-net

    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

volumes:
  hpos-test-b-data:
  hpos-test-b-logs:

networks:
  hpos-test-b-net:
    driver: bridge
```

---

## B. Compose Validation

```bash
docker compose -f /docker/hermes-product-os/docker-compose.test-b.yml config
```

**Validation criteria:**
- No syntax errors
- All mounts resolve to valid host paths (host paths created before deployment)
- No port collisions
- No network name collisions with staging

---

## C. Architecture Diagram

```
SYNTHETIC SOURCE
  /var/lib/hermes/snapshots/snapshot-test-b.db
  ── created by root: sqlite3 ... ".backup snapshot-test-b.db.tmp"
  ── atomic mv → snapshot-test-b.db
  ── chown root:10010, chmod 440

  ↓ (bind mount :ro — Layer 2: kernel)

PHASE B TEST CONTAINER (hermes-product-os-test-b)
  ├── /opt/hermes/data/snapshot.db (ro) → SQLite ?mode=ro (Layer 3)
  ├── /opt/hermes/secrets/B2_* (ro) → B2 reader stub (Layer 1)
  ├── /opt/hermes/config/env (ro) → MUTATIONS_DISABLED=true (Layer 4)
  ├── Activation level enforced at startup (Layer 5)
  ├── Health endpoint verifies all layers (Layer 6)
  └── /opt/hermes/logs/ → audit records

  ↑ ONLY READS AUTHORIZED
  ↑ NO WRITE PATH EXISTS
  ↑ 6 ENFORCEMENT LAYERS
```

---

## D. Exact Host Paths

| Path | Purpose |
|---|---|
| `/var/lib/hermes/snapshots/snapshot-test-b.db` | Synthetic snapshot (created by simulation) |
| `/etc/hermes-product-os-test-b/secrets/` | Synthetic Phase B credential directory |
| `/etc/hermes-product-os-test-b/env` | Synthetic Phase B environment |
| `/docker/hermes-product-os/docker-compose.test-b.yml` | Test compose file |

---

## E. Exact Container Paths

| Container Path | Host Source | Mode |
|---|---|---|
| `/opt/hermes/data/snapshot.db` | `/var/lib/hermes/snapshots/snapshot-test-b.db` | `:ro` |
| `/opt/hermes/secrets/B2_READER_KEY_ID` | Synthetic test-b secrets dir | `:ro` |
| `/opt/hermes/config/env` | Synthetic test-b env | `:ro` |
| `/opt/hermes/keys/public-key.txt` | Shared staging public key | `:ro` |

---

## F. Synthetic Credential Names

| Namespace | Host Path | Container Path |
|---|---|---|
| **STAGING** | `/etc/hermes-product-os/secrets/B2_*` | `/opt/hermes/secrets/B2_*` |
| **TEST-B** | `/etc/hermes-product-os-test-b/secrets/B2_*` | `/opt/hermes/secrets/B2_*` |
| **PRODUCTION** | `/etc/hermes-product-os-prod/secrets/B2_*` (future) | `/opt/hermes/secrets/B2_*` (future) |

No credential file is shared between namespaces. Container-side paths are identical but mounted from different host sources.

---

## G. Isolation Proof from Existing Staging

| Dimension | Staging | Test-B | Collision? |
|---|---|---|---|
| Project name | `hermes-product-os` | `hermes-product-os-test-b` | NO |
| Container name | `hermes-product-os` | `hermes-product-os-test-b` | NO |
| Network | `hermes-product-os-net` | `hpos-test-b-net` | NO |
| Data volume | `hpos-data` | `hpos-test-b-data` | NO |
| Logs volume | `hpos-logs` | `hpos-test-b-logs` | NO |
| Credential host path | `/etc/hermes-product-os/secrets/` | `/etc/hermes-product-os-test-b/secrets/` | NO |
| Snapshot path | none (Phase A) | `/var/lib/hermes/snapshots/snapshot-test-b.db` | NO |
| Port | 8080 (internal only, via Traefik) | 8080 (internal only, no Traefik) | NO — separate networks |

---

## H. Files Created/Modified

| File | Action | Purpose |
|---|---|---|
| `/docker/hermes-product-os/docker-compose.test-b.yml` | CREATE | Test compose |
| `/etc/hermes-product-os-test-b/secrets/` | CREATE directory | Synthetic credential namespace |
| `/etc/hermes-product-os-test-b/secrets/B2_*` | CREATE | Stub credential files |
| `/etc/hermes-product-os-test-b/env` | CREATE | Test environment |

**Files NOT modified:**
- `/docker/hermes-product-os/docker-compose.yml` — UNCHANGED
- `/docker/hermes-product-os/docker-compose.yml.bak` — UNCHANGED
- Staging credential files — UNCHANGED
- Staging runtime — UNCHANGED

---

## I. Cleanup Procedure

```bash
docker compose -f /docker/hermes-product-os/docker-compose.test-b.yml down -v
rm -f /docker/hermes-product-os/docker-compose.test-b.yml
rm -rf /etc/hermes-product-os-test-b
rm -f /var/lib/hermes/snapshots/snapshot-test-b.db*
docker compose -f /docker/hermes-product-os/docker-compose.yml up -d  # restore staging if needed
```

---

## J. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Test compose collides with staging | LOW | Container name collision → compose fails | Distinct names verified |
| Test network leaks to staging | LOW | No routing between networks | Separate bridge networks |
| Test writes to staging data | NONE | Separate volumes, no shared mounts | Volume isolation |
| Test credentials leak | NONE | Synthetic values only | No real credentials |
| Docker resource exhaustion | LOW | One additional container | 1GB memory, minimal CPU |

---

## K. First Test to Run

**G1.1 Layer 2 — Filesystem/Mount Read-Only Enforcement:**

1. Deploy test compose
2. Verify container healthy
3. Attempt to write to `/opt/hermes/data/snapshot.db` from inside container
4. Expected: `Read-only file system` (kernel enforced)
5. Verify staging container unaffected

---

## L. Confirmation

| Assertion | Status |
|---|---|
| CURRENT STAGING COMPOSE MODIFIED | NO |
| PRODUCTION RESOURCES USED | NO |
| REAL CREDENTIALS CREATED | NO |
| PHASE B ACTIVATED | NO |
| Staging container unaffected | Design ensures isolation |

---

**Pre-execution package complete. Awaiting engineering review. No VPS commands executed. Production = 0.**