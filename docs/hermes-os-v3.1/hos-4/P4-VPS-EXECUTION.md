# P4 VPS Execution Plan — Final

**Commit:** 336b1de1f650627ddba7a0e91d80e4203d00cf6c
**Image tag:** prod-p4-release
**DO NOT EXECUTE WITHOUT AUTHORIZATION**

---

## CHECKPOINT 0: Source + DB Verification

```bash
# A1 — Source checkout
rm -rf /tmp/hpos-p4
git clone https://github.com/amjadthaufeeg/hermes-os-foundation.git /tmp/hpos-p4
cd /tmp/hpos-p4
git checkout 336b1de1f650627ddba7a0e91d80e4203d00cf6c
git log --oneline -1
# Expected: 336b1de fix: compose uses release tag prod-p4-release

# A2 — Dockerfile provenance
sha256sum /docker/hermes-product-os/Dockerfile
# Record this hash

# A3 — Compose install + hash
cp deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
sha256sum /tmp/hpos-p4/deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
# Hashes must match

# A4 — Compose validation
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml config -q && echo "VALID"
```

## CHECKPOINT 1: Immutable Accepted-DB Verification

```bash
MOUNTPOINT=$(docker volume inspect hermes-product-os-prod_hpos-prod-data --format '{{.Mountpoint}}')

# C1 — File properties
test -f "$MOUNTPOINT/production.db" && test -s "$MOUNTPOINT/production.db" && echo "DB_OK"
stat -c '%a %U:%G' "$MOUNTPOINT"                    # Expected: 750 10010:10010
stat -c '%a %U:%G' "$MOUNTPOINT/production.db"       # Expected: 640 10010:10010

# C2 — Immutable read-only verification
python3 << 'PYEOF'
import sqlite3, os
MOUNTPOINT = os.environ['MOUNTPOINT']
db = os.path.join(MOUNTPOINT, 'production.db')
uri = f'file:{db}?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)

integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
print(f'Integrity: {integrity}')
assert integrity == 'ok'

version = conn.execute('SELECT version FROM schema_version').fetchone()[0]
print(f'Schema version: {version}')
assert version == 1

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(f'Tables: {tables}')
assert len(tables) == 5

dec_count = conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
print(f'Decisions: {dec_count}')
assert dec_count == 0

audit_count = conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
print(f'Audit events: {audit_count}')

session_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
print(f'Sessions: {session_count}')

conn.close()
print('DB_VERIFICATION_PASS')
PYEOF
# Expected: DB_VERIFICATION_PASS
```

## CHECKPOINT 2: Build + Compose Safety

```bash
# D1 — Build image
cd /tmp/hpos-p4
docker build \
    -t hermes-product-os-hpos:prod-p4-release \
    -f /docker/hermes-product-os/Dockerfile \
    .

# D2 — Record image ID
IMAGE_ID=$(docker image inspect hermes-product-os-hpos:prod-p4-release --format '{{.Id}}')
echo "IMAGE_ID=$IMAGE_ID"

# D3 — Verify image user
docker run --rm hermes-product-os-hpos:prod-p4-release id hermes
# Expected: uid=10010(hermes) gid=10010(hermes)

# E1 — Normalized compose security proof
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml config | python3 << 'PYEOF'
import sys, yaml
config = yaml.safe_load(sys.stdin)
svc = config['services']['hpos']
env_list = svc['environment']
env = {e.split('=',1)[0]: e.split('=',1)[1] for e in env_list}

checks = [
    ('HERMES_ENVIRONMENT', env.get('HERMES_ENVIRONMENT'), 'PRODUCTION'),
    ('MUTATIONS_DISABLED', env.get('MUTATIONS_DISABLED'), 'true'),
    ('SIMULATION_MODE', env.get('SIMULATION_MODE'), 'false'),
    ('DATABASE_PATH', env.get('DATABASE_PATH'), '/opt/hermes/data/production.db'),
    ('user', svc.get('user'), '10010:10010'),
    ('read_only', svc.get('read_only'), True),
]

for name, actual, expected in checks:
    status = 'PASS' if actual == expected else f'FAIL (got: {actual})'
    print(f'{name}: {status}')

caps = svc.get('cap_drop', [])
print(f"cap_drop:ALL: {'PASS' if 'ALL' in caps else 'FAIL'}")

sec = svc.get('security_opt', [])
print(f"no-new-privileges: {'PASS' if 'no-new-privileges:true' in sec else 'FAIL'}")

net = config['networks']['prod-net']
print(f"network_internal: {'PASS' if net.get('internal') == True else 'FAIL'}")

# No ports
assert 'ports' not in svc, 'FAIL: ports exposed'
assert 'expose' not in svc, 'FAIL: expose present'
print('no_ports: PASS')

# No B2
compose_text = open('/docker/hermes-product-os-prod/docker-compose.yml').read()
assert 'B2_' not in compose_text, 'FAIL: B2 credentials'
print('no_b2_secrets: PASS')

# No staging volumes
assert 'hpos-data' not in str(svc.get('volumes',[])), 'FAIL: staging data volume'
assert 'hpos-backup' not in str(svc.get('volumes',[])), 'FAIL: staging backup volume'
print('no_staging_volumes: PASS')

print('COMPOSE_SECURITY_PASS')
PYEOF
# Expected: all PASS, COMPOSE_SECURITY_PASS
```

## CHECKPOINT 3: Start Production

```bash
# F1 — Start
cd /docker/hermes-product-os-prod
docker compose up -d

# F2 — Wait for healthy
sleep 15
docker ps --filter name=hermes-product-os-prod --format '{{.Names}} {{.Status}}'
# Expected: hermes-product-os-prod Up ... (healthy)

# F3 — If not healthy, STOP and capture diagnostics
# docker ps -a --filter name=hermes-product-os-prod
# docker logs hermes-product-os-prod --tail 50
# docker compose down

# G — Image identity match
CONTAINER_IMAGE=$(docker inspect hermes-product-os-prod --format '{{.Image}}')
echo "Container image: $CONTAINER_IMAGE"
echo "Build image:     $IMAGE_ID"
test "$CONTAINER_IMAGE" = "$IMAGE_ID" && echo "IMAGE_MATCH_OK" || echo "IMAGE_MISMATCH"
# Expected: IMAGE_MATCH_OK

# H — Health endpoint
docker exec hermes-product-os-prod python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/api/health')
data = json.loads(r.read())
print(data)
assert data['environment'] == 'PRODUCTION', f'Expected PRODUCTION, got {data[\"environment\"]}'
assert data['mutations'] == 'DISABLED', f'Expected DISABLED, got {data[\"mutations\"]}'
print('HEALTH_OK')
"
# Expected: HEALTH_OK

# I — Decisions from DB
docker exec hermes-product-os-prod python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/api/decisions')
data = json.loads(r.read())
print(f'Count: {data[\"count\"]}, Mode: {data[\"mode\"]}')
assert data['count'] == 0, f'Expected 0, got {data[\"count\"]}'
assert data['mode'] == 'PRODUCTION', f'Expected PRODUCTION, got {data[\"mode\"]}'
print('DECISIONS_OK')
"
# Expected: DECISIONS_OK

# J — Runtime UID
docker exec hermes-product-os-prod id
# Expected: uid=10010(hermes) gid=10010(hermes)
```

## CHECKPOINT 4: Mutation Denial + Operational Write

```bash
# K — Capture BEFORE counts (immutable read-only)
BEFORE_DEC=$(python3 -c "
import sqlite3
uri = 'file:$MOUNTPOINT/production.db?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)
print(conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0])
conn.close()
")
BEFORE_AUDIT=$(python3 -c "
import sqlite3
uri = 'file:$MOUNTPOINT/production.db?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)
print(conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])
conn.close()
")
echo "BEFORE decisions=$BEFORE_DEC, audit=$BEFORE_AUDIT"

# K2 — Real HTTP mutation denial (from inside container)
HTTP_CODE=$(docker exec hermes-product-os-prod python3 -c "
import urllib.request, urllib.error
try:
    req = urllib.request.Request(
        'http://localhost:8080/api/decisions/DEC-HOS-001/actions',
        data=b'{\"action\":\"approve\",\"rationale\":\"p4-test\"}',
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print(e.code)
")
echo "HTTP_STATUS=$HTTP_CODE"
# Expected: 503

# L — Verify DB unchanged
AFTER_DEC=$(python3 -c "
import sqlite3
uri = 'file:$MOUNTPOINT/production.db?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)
print(conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0])
conn.close()
")
AFTER_AUDIT=$(python3 -c "
import sqlite3
uri = 'file:$MOUNTPOINT/production.db?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)
print(conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])
conn.close()
")
echo "AFTER decisions=$AFTER_DEC, audit=$AFTER_AUDIT"
test "$HTTP_CODE" = "503" && echo "MUTATION_DENIED_OK"
test "$BEFORE_DEC" = "$AFTER_DEC" && echo "DECISIONS_UNCHANGED_OK"
test "$BEFORE_AUDIT" = "$AFTER_AUDIT" && echo "AUDIT_UNCHANGED_OK"

# M — Simulated login for operational session write
# The app has /api/auth/login endpoint in SIMULATION_MODE.
# In PRODUCTION, SIMULATION_MODE=false — this endpoint is NOT available
# through the simulation gate. However, the login route at /api/auth/login
# is defined separately from the OAuth gate. Let's test it:

docker exec hermes-product-os-prod python3 -c "
import urllib.request, json, urllib.error

# Try the simulated login endpoint
try:
    req = urllib.request.Request(
        'http://localhost:8080/api/auth/login',
        data=b'{\"username\":\"amjadthaufeeg\"}',
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    print(f'Login: status={r.status}, actor={data.get(\"actor\")}, mode={data.get(\"mode\")}')
except urllib.error.HTTPError as e:
    print(f'Login denied: {e.code}')
except Exception as e:
    print(f'Login error: {e}')
"
# Document: in PRODUCTION, simulated login may or may not be available.
# If not available: no operational session writes in current Phase B.
# This is acceptable — sessions only needed when mutations are authorized.

# N — WAL/SHM ownership inspection
test -f "$MOUNTPOINT/production.db-wal" && stat -c '%U:%G' "$MOUNTPOINT/production.db-wal" || echo "NO_WAL"
test -f "$MOUNTPOINT/production.db-shm" && stat -c '%U:%G' "$MOUNTPOINT/production.db-shm" || echo "NO_SHM"
# If WAL/SHM present after app started: expected 10010:10010
```

## CHECKPOINT 5: Safety

```bash
# O — Network isolation
docker inspect hermes-product-os-prod --format '{{.NetworkSettings.Ports}}'
# Expected: <no value> or {}
docker network inspect hermes-product-os-prod_prod-net --format '{{.Internal}}'
# Expected: true

# P — Staging healthy
docker ps --filter name=hermes-product-os --format '{{.Names}} {{.Status}}' | grep -v test

# Q — Test-B healthy
docker ps --filter name=hermes-product-os-test-b --format '{{.Names}} {{.Status}}'
```

## ROLLBACK

```bash
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml down
# Container removed. production.db + volume preserved.
```

---

**P4_EXECUTION_READY_V2. 5 checkpoints. All commands corrected. Awaiting authorization.**