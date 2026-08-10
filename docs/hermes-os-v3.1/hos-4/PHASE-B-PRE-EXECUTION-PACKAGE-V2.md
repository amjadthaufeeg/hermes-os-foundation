# Phase B — Pre-Execution Package v2 (Corrected)

**Corrections:** Network isolation claim, pinned image, restart policy documentation, environment gate, host ports.

---

## 1. Test-B Network Definition

```yaml
networks:
  hpos-test-b-net:
    driver: bridge
    internal: true
```

**`internal: true`** means containers on this network CANNOT reach the internet or host network. They can only communicate with other containers on the same internal network.

### Allowed/Denied Network Matrix

| Target | Allowed? | Reason |
|---|---|---|
| Other containers on `hpos-test-b-net` | YES | Inter-container on same network only |
| Staging containers (`hermes-product-os-net`) | NO | Separate bridge, no routing |
| Traefik (host network) | NO | `internal: true` blocks host access |
| Host services (SSH, Docker socket) | NO | `internal: true` blocks host access |
| Backblaze B2 (internet) | NO | `internal: true` blocks outbound |
| Arbitrary internet | NO | `internal: true` blocks outbound |
| Production endpoints | NO | Same as above |

### Required vs Denied

| Test | Network Requirement |
|---|---|
| G1.1 (read-only enforcement) | None — snapshot is local file mount |
| G1.2 (fail-closed) | None — all scenarios test local resources |
| G1.5 (rollback) | None — compose switching, no network needed |

**All G1 tests can run with zero network access. `internal: true` is appropriate.**

---

## 2. Pinned Image Reference

### Evidence

```bash
$ docker inspect hermes-product-os --format '{{.Image}}'
sha256:7bbc4894b02b081eb52861888d6835a25d9c8899288b1175409e1a2a4003989e

$ docker image inspect hermes-product-os-hpos:latest --format '{{.Id}}'
sha256:7bbc4894b02b081eb52861888d6835a25d9c8899288b1175409e1a2a4003989e
```

**STAGING IMAGE ID = `sha256:7bbc4894b02b...`**
**TEST-B IMAGE ID = `sha256:7bbc4894b02b...` (same digest)**

### Test-B Compose Reference

```yaml
services:
  hpos-test-b:
    image: hermes-product-os-hpos@sha256:7bbc4894b02b081eb52861888d6835a25d9c8899288b1175409e1a2a4003989e
```

Pinned by digest, not tag. Immune to `latest` drift.

---

## 3. Restart Policy — Documented Difference

### Test-B

```yaml
restart: "no"
```

**Classification:** INTENTIONALLY DIFFERENT FOR TEST HARNESS. Reason: failed/stopped Test-B must remain down so failure evidence (F1-F12) can be observed without automatic recovery masking the test result.

### Intended Production Phase B

```yaml
restart: unless-stopped
```

Same as staging. Production Phase B must survive Docker daemon restarts but still fail closed: if activation level or policy is invalid at startup, the container must either exit or refuse to serve reads. The `restart: unless-stopped` policy combined with startup-time policy checks ensures this.

**This is a simulation difference. Do not claim structural identity on this layer.**

---

## 4. Environment Gate — Code Evidence

### Current Environment Enum

From `/opt/hermes/app/backend/hos4c/environment.py`:

```python
class Environment(enum.Enum):
    LOCAL_TEST = "LOCAL_TEST"
    LOCAL_SIMULATION = "LOCAL_SIMULATION"
    AUTH_REVIEW = "AUTH_REVIEW"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
```

`TEST_PHASE_B` is NOT a recognized value. Using it would cause `ValueError` at startup — the container would crash. This is fail-closed but uncontrolled (crash, not graceful exit).

### Correction: Use LOCAL_TEST

| Value | Recognized? | Mutations | Auth Writes | OAuth |
|---|---|---|---|---|
| `LOCAL_SIMULATION` | YES (staging) | false | false | false |
| `LOCAL_TEST` | YES | false | false | false |
| `TEST_PHASE_B` | NO → CRASH | N/A | N/A | N/A |

**Test-B will use `HERMES_ENVIRONMENT=LOCAL_TEST`.**

Policy for `LOCAL_TEST`:
- mutations: false
- auth_writes: false
- oauth: false
- debug: true
- api_docs: true

This matches staging policy and provides the same mutation-disabled guarantees.

### Fail-Closed Proof

Unknown environment → ValueError at import time → container exits before serving any request. Unknown environments cannot silently alias known environments.

---

## 5. No Host Ports — Confirmed

Test-B compose contains no `ports:` directive. Container port 8080 is internal to the `hpos-test-b-net` bridge only. No host port mapping. Confirmed by compose review.

---

## 6. Corrected docker-compose.test-b.yml

```yaml
services:
  hpos-test-b:
    image: hermes-product-os-hpos@sha256:7bbc4894b02b081eb52861888d6835a25d9c8899288b1175409e1a2a4003989e
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
      - hpos-test-b-data:/opt/hermes/data
      - hpos-test-b-logs:/opt/hermes/logs
      - /var/lib/hermes/snapshots/snapshot-test-b.db:/opt/hermes/data/snapshot.db:ro
      - /etc/hermes-product-os-test-b/secrets/B2_READER_KEY_ID:/opt/hermes/secrets/B2_READER_KEY_ID:ro
      - /etc/hermes-product-os-test-b/secrets/B2_READER_APPLICATION_KEY:/opt/hermes/secrets/B2_READER_APPLICATION_KEY:ro
      - /etc/hermes-product-os-test-b/secrets/B2_BUCKET_NAME:/opt/hermes/secrets/B2_BUCKET_NAME:ro
      - /etc/hermes-product-os-test-b/secrets/B2_ENDPOINT:/opt/hermes/secrets/B2_ENDPOINT:ro
      - /etc/hermes-product-os-test-b/env:/opt/hermes/config/env:ro
      - /etc/hermes-product-os/keys/staging-public-key.txt:/opt/hermes/keys/public-key.txt:ro
    environment:
      - PYTHONUNBUFFERED=1
      - HERMES_ENVIRONMENT=LOCAL_TEST
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
    internal: true
```

---

## 7. Pre-Execution Confirmation

| Assertion | Status |
|---|---|
| STAGING IMAGE ID = TEST-B IMAGE ID | ✅ `sha256:7bbc4894b02b...` |
| Image pinned by digest | ✅ `@sha256:...` not `:latest` |
| Network: `internal: true` | ✅ No internet, no host, no staging |
| No host ports published | ✅ No `ports:` directive |
| Environment: recognized value | ✅ `LOCAL_TEST` (enum member) |
| Unknown env fails closed | ✅ `ValueError` → container crash |
| Restart policy difference documented | ✅ `"no"` for test, `unless-stopped` for prod |
| Staging compose unmodified | ✅ |

---

**Pre-execution package v2 complete. Awaiting engineering review. Production=0.**