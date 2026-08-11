# P2 — Production Compose + Volume Definition

**Plan only. No execution until Amjad authorizes.**

---

## 1. Proposed Production Compose

See: `deploy/docker-compose.prod.yml`

### Key Properties

| Property | Value | Rationale |
|---|---|---|
| Project name | `hermes-product-os-prod` | Separate Docker namespace |
| Container name | `hermes-product-os-prod` | Identifiable |
| Image | `hermes-product-os-hpos:prod-31d7842` | TASK-002 commit; pin digest after build |
| Restart | `unless-stopped` | Survive Docker daemon restart |
| `read_only` | `true` | Immutable root filesystem |
| `cap_drop` | `ALL` | Minimum privilege |
| `cap_add` | `NET_BIND_SERVICE, CHOWN, DAC_OVERRIDE` | Bind port 8080 (NET); chown DB (CHOWN); access data volume (DAC) |
| `no_new_privileges` | `true` | No privilege escalation |
| Environment | `PRODUCTION, MUTATIONS_DISABLED=true, SIMULATION_MODE=false` | Production identity |
| `DATABASE_PATH` | `/opt/hermes/data/production.db` | Persistent DB location |
| Data volume | `hpos-prod-data` → `/opt/hermes/data:rw` | Persistent DB |
| Logs volume | `hpos-prod-logs` → `/opt/hermes/logs:rw` | Persistent logs |
| No secrets mounted | — | No B2 credentials |
| No snapshot mount | — | Added at B2b |
| No backup volume | — | Not needed for read-only |
| Network | `prod-net`, `internal: true` | No outbound, no host port |
| Healthcheck | 30s interval, port 8080 | Readiness signal |
| Start period | 10s | Allow startup time |

---

## 2. Image Strategy

| Phase | Image |
|---|---|
| P2-P4 (initial) | `hermes-product-os-hpos:prod-31d7842` (tag from local build) |
| Pre-B7 (canary) | Digest-pin: `hermes-product-os-hpos@sha256:<digest>` |

Build command (after P2 authorization):

```bash
cd /tmp/hpos-task002 && git checkout 31d7842
docker build -t hermes-product-os-hpos:prod-31d7842 .
```

---

## 3. Volume Ownership Strategy

| Volume | Container path | Container UID | Issue |
|---|---|---|---|
| `hpos-prod-data` | `/opt/hermes/data` | 10010 (hermes) | Volume initially owned by root |

### Resolution

Docker named volumes are initially owned by `root`. On first mount, the directory inherits root ownership. The init script (P3) runs as root, creates `production.db`, and `chown 10010:10010`. After P3, the Hermes container (UID 10010) can read/write the DB.

The container has `CHOWN` capability specifically for this purpose.

---

## 4. P2 Execution Procedure

### COMMAND 1 — Preflight

```bash
whoami
# Expected: root

# Verify P1 directory exists
test -d /docker/hermes-product-os-prod && echo "OK" || echo "MISSING"
```

### COMMAND 2 — Copy compose file

```bash
# Amjad copies deploy/docker-compose.prod.yml to VPS:
# /docker/hermes-product-os-prod/docker-compose.yml

docker compose -f /docker/hermes-product-os-prod/docker-compose.yml config -q && echo "VALID"
```

### COMMAND 3 — Pull/build production image

```bash
# Option A: Build from source
cd /tmp/hpos-task002
docker build -t hermes-product-os-hpos:prod-31d7842 .

# Option B: Retag staging image (temporary for P2-P4)
docker tag hermes-product-os-hpos:latest hermes-product-os-hpos:prod-31d7842
```

### COMMAND 4 — Create volumes + network (no container start)

```bash
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml up --no-start
```

### COMMAND 5 — Verify volumes

```bash
docker volume ls --filter name=hpos-prod-data
# Expected: hermes-product-os-prod_hpos-prod-data

docker volume ls --filter name=hpos-prod-logs
# Expected: hermes-product-os-prod_hpos-prod-logs
```

### COMMAND 6 — Verify network

```bash
docker network ls --filter name=prod-net
# Expected: hermes-product-os-prod_prod-net

docker network inspect hermes-product-os-prod_prod-net --format '{{.Internal}}'
# Expected: true
```

### COMMAND 7 — Verify no container running

```bash
docker ps --filter name=hermes-product-os-prod -q | grep -q . && echo "RUNNING_UNEXPECTED" || echo "NOT_RUNNING_OK"
```

### COMMAND 8 — Prove staging + Test-B healthy

```bash
docker ps --filter name=hermes-product-os --format '{{.Names}} {{.Status}}' | sort
```

---

### STOP CHECKPOINT — P2 complete.

---

## 5. Rollback

```bash
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml down
docker volume rm hermes-product-os-prod_hpos-prod-data hermes-product-os-prod_hpos-prod-logs
docker network rm hermes-product-os-prod_prod-net
docker rmi hermes-product-os-hpos:prod-31d7842  # if built locally
rm /docker/hermes-product-os-prod/docker-compose.yml
```

---

## 6. P2 PASS Criteria

| # | Criterion |
|---|---|
| 1 | Compose file at `/docker/hermes-product-os-prod/docker-compose.yml` |
| 2 | `docker compose config -q` validates |
| 3 | `hpos-prod-data` volume created |
| 4 | `hpos-prod-logs` volume created |
| 5 | `prod-net` network created |
| 6 | Network is `internal: true` |
| 7 | No production container running |
| 8 | No production DB yet |
| 9 | Staging healthy |
| 10 | Test-B healthy |

---

**P2 design complete. Awaiting Amjad authorization.**