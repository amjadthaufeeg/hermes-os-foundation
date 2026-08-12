# P4 VPS Execution — Final Commands
# Commit: cb085b133e4ce75600b5ecd0c652e5af260f5808
# DO NOT EXECUTE WITHOUT AUTHORIZATION

# ═══════════════════════════════════════════
# CHECKPOINT 0 — Source + DB
# ═══════════════════════════════════════════

rm -rf /tmp/hpos-p4
git clone https://github.com/amjadthaufeeg/hermes-os-foundation.git /tmp/hpos-p4
cd /tmp/hpos-p4
git checkout cb085b133e4ce75600b5ecd0c652e5af260f5808
git log --oneline -1
# Expected: cb085b1 docs: P4 VPS execution plan V2

sha256sum /docker/hermes-product-os/Dockerfile
# Record hash

cp deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
sha256sum /tmp/hpos-p4/deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
# Hashes must match

docker compose -f /docker/hermes-product-os-prod/docker-compose.yml config -q && echo "VALID"

# ═══════════════════════════════════════════
# CHECKPOINT 1 — Immutable DB Verification
# ═══════════════════════════════════════════

export MOUNTPOINT
MOUNTPOINT=$(docker volume inspect hermes-product-os-prod_hpos-prod-data --format '{{.Mountpoint}}')

test -f "$MOUNTPOINT/production.db" && test -s "$MOUNTPOINT/production.db" && echo "DB_EXISTS_OK"
stat -c '%a %U:%G' "$MOUNTPOINT"                    # Expected: 750 10010:10010
stat -c '%a %U:%G' "$MOUNTPOINT/production.db"       # Expected: 640 10010:10010

python3 "$MOUNTPOINT" << 'PYEOF'
import sys, sqlite3
db = sys.argv[1] + '/production.db'
uri = f'file:{db}?mode=ro&immutable=1'
conn = sqlite3.connect(uri, uri=True)
integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
assert integrity == 'ok', f'integrity: {integrity}'
version = conn.execute('SELECT version FROM schema_version').fetchone()[0]
assert version == 1, f'version: {version}'
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
assert len(tables) == 5, f'tables: {tables}'
dec_count = conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
assert dec_count == 0, f'decisions: {dec_count}'
audit_count = conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
sessions_count = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
print(f'Decisions: {dec_count}, Audit: {audit_count}, Sessions: {sessions_count}')
conn.close()
print('DB_VERIFICATION_PASS')
PYEOF
# Expected: DB_VERIFICATION_PASS

# ═══════════════════════════════════════════
# CHECKPOINT 2 — Build + Compose Security
# ═══════════════════════════════════════════

cd /tmp/hpos-p4
docker build \
    -t hermes-product-os-hpos:prod-p4-release \
    -f /docker/hermes-product-os/Dockerfile \
    .

IMAGE_ID=$(docker image inspect hermes-product-os-hpos:prod-p4-release --format '{{.Id}}')
echo "IMAGE_ID=$IMAGE_ID"

docker run --rm hermes-product-os-hpos:prod-p4-release id hermes
# Expected: uid=10010(hermes) gid=10010(hermes)

# Normalize compose, then verify security properties
docker compose \
    -f /docker/hermes-product-os-prod/docker-compose.yml \
    config > /tmp/hpos-p4-compose-normalized.yml

python3 /tmp/hpos-p4-compose-normalized.yml << 'PYEOF'
import sys, yaml

with open(sys.argv[1]) as f:
    c = yaml.safe_load(f)
s = c['services']['hpos']

# Environment — handle both list/dict forms
env_raw = s['environment']
if isinstance(env_raw, dict):
    e = {k: str(v) for k, v in env_raw.items()}
elif isinstance(env_raw, list):
    e = {}
    for item in env_raw:
        if '=' in item:
            k, v = item.split('=', 1)
            e[k] = v
else:
    raise RuntimeError(f'Unexpected environment type: {type(env_raw)}')

checks = [
    ('HERMES_ENVIRONMENT', e.get('HERMES_ENVIRONMENT'), 'PRODUCTION'),
    ('MUTATIONS_DISABLED', e.get('MUTATIONS_DISABLED'), 'true'),
    ('SIMULATION_MODE', e.get('SIMULATION_MODE'), 'false'),
    ('DATABASE_PATH',  e.get('DATABASE_PATH'), '/opt/hermes/data/production.db'),
    ('user',           s.get('user'), '10010:10010'),
    ('read_only',      s.get('read_only'), True),
    ('cap_drop_ALL',   'ALL' in s.get('cap_drop', []), True),
    ('no_new_privs',   'no-new-privileges:true' in s.get('security_opt', []), True),
    ('network_internal', c['networks']['prod-net'].get('internal'), True),
]

all_pass = True
for name, actual, expected in checks:
    ok = actual == expected
    if not ok:
        all_pass = False
    print(f'{name}: {"PASS" if ok else "FAIL got=" + repr(actual)}')

# No ports / expose
if 'ports' in s or 'expose' in s:
    print('no_ports: FAIL')
    all_pass = False
else:
    print('no_ports: PASS')

# No B2 secrets in file
compose_text = open('/docker/hermes-product-os-prod/docker-compose.yml').read()
if 'B2_' in compose_text:
    print('no_B2_secrets: FAIL')
    all_pass = False
else:
    print('no_B2_secrets: PASS')

# No staging volumes
vol_str = str(s.get('volumes', []))
if 'hpos-data' in vol_str or 'hpos-backup' in vol_str:
    print('no_staging_volumes: FAIL')
    all_pass = False
else:
    print('no_staging_volumes: PASS')

assert all_pass, 'COMPOSE_SECURITY_FAILED'
print('COMPOSE_SECURITY_PASS')
PYEOF
# Expected: COMPOSE_SECURITY_PASS

# ═══════════════════════════════════════════
# CHECKPOINT 3 — Start + Verify
# ═══════════════════════════════════════════

cd /docker/hermes-product-os-prod
docker compose up -d
sleep 15
docker ps --filter name=hermes-product-os-prod --format '{{.Names}} {{.Status}}'
# Expected: hermes-product-os-prod Up ... (healthy)

# Image identity match
CONTAINER_IMAGE=$(docker inspect hermes-product-os-prod --format '{{.Image}}')
test "$CONTAINER_IMAGE" = "$IMAGE_ID" && echo "IMAGE_MATCH_OK" || echo "IMAGE_MISMATCH"

# Health
docker exec hermes-product-os-prod python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/api/health')
d = json.loads(r.read())
assert d['environment'] == 'PRODUCTION', f'Got {d[\"environment\"]}'
assert d['mutations'] == 'DISABLED', f'Got {d[\"mutations\"]}'
print('HEALTH_OK')
"

# Decisions from DB
docker exec hermes-product-os-prod python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/api/decisions')
d = json.loads(r.read())
assert d['count'] == 0, f'Got {d[\"count\"]}'
assert d['mode'] == 'PRODUCTION', f'Got {d[\"mode\"]}'
print('DECISIONS_OK')
"

# Runtime UID
docker exec hermes-product-os-prod id
# Expected: uid=10010(hermes) gid=10010(hermes)

# ═══════════════════════════════════════════
# CHECKPOINT 4 — Mutation Denial
# ═══════════════════════════════════════════

export MOUNTPOINT
MOUNTPOINT=$(docker volume inspect hermes-product-os-prod_hpos-prod-data --format '{{.Mountpoint}}')

BEFORE_DEC=$(python3 "$MOUNTPOINT" -c "
import sys, sqlite3
db = sys.argv[1] + '/production.db'
conn = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
print(conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0])
")
BEFORE_AUDIT=$(python3 "$MOUNTPOINT" -c "
import sys, sqlite3
db = sys.argv[1] + '/production.db'
conn = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
print(conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])
")

# Real HTTP mutation from inside container
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

AFTER_DEC=$(python3 "$MOUNTPOINT" -c "
import sys, sqlite3
db = sys.argv[1] + '/production.db'
conn = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
print(conn.execute('SELECT COUNT(*) FROM decisions').fetchone()[0])
")
AFTER_AUDIT=$(python3 "$MOUNTPOINT" -c "
import sys, sqlite3
db = sys.argv[1] + '/production.db'
conn = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
print(conn.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])
")

echo "HTTP=$HTTP_CODE DEC=$BEFORE_DEC→$AFTER_DEC AUDIT=$BEFORE_AUDIT→$AFTER_AUDIT"
test "$HTTP_CODE" = "503" && echo "MUTATION_DENIED_OK"
test "$BEFORE_DEC" = "$AFTER_DEC" && echo "DECISIONS_UNCHANGED_OK"
test "$BEFORE_AUDIT" = "$AFTER_AUDIT" && echo "AUDIT_UNCHANGED_OK"

# WAL/SHM ownership
test -f "$MOUNTPOINT/production.db-wal" && stat -c '%U:%G' "$MOUNTPOINT/production.db-wal" || echo "NO_WAL"
test -f "$MOUNTPOINT/production.db-shm" && stat -c '%U:%G' "$MOUNTPOINT/production.db-shm" || echo "NO_SHM"

# ═══════════════════════════════════════════
# CHECKPOINT 5 — Safety
# ═══════════════════════════════════════════

# No host ports
docker inspect hermes-product-os-prod --format '{{json .NetworkSettings.Ports}}'

# Internal network
docker network inspect hermes-product-os-prod_prod-net --format '{{.Internal}}'
# Expected: true

# Staging + Test-B health
docker ps --filter name=hermes-product-os --format '{{.Names}} {{.Status}}' | sort

# ═══════════════════════════════════════════
# ROLLBACK (if needed)
# ═══════════════════════════════════════════
# docker compose -f /docker/hermes-product-os-prod/docker-compose.yml down
# Container removed. production.db + volume preserved.