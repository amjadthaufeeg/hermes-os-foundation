# P4 — Execution Plan Audit & Improvements

**Baseline: commit d816fbf. Accepted decisions preserved.**

---

## DEFECT 1 — Host-side sqlite3 verification corrupts WAL/SHM ownership

**Issue:** Running host-side `sqlite3 "$MOUNTPOINT/production.db" "PRAGMA integrity_check"` opens the database as root. On WAL mode databases, this creates `production.db-wal` and `production.db-shm` owned by root. The production API (UID 10010) will fail to open the DB because it can't create WAL/SHM in a directory it owns (750) — the root-owned WAL/SHM files can't be deleted by UID 10010.

**Fix:** All host-side sqlite3 reads must use read-only mode:

```bash
sqlite3 "file:$MOUNTPOINT/production.db?mode=ro" "PRAGMA integrity_check;"
```

Or verify integrity from inside the container after startup (preferred).

**P4 Plan Change:** Remove host-side sqlite3. All DB verification happens inside the container after startup.

---

## DEFECT 2 — GAP-001 test doesn't prove runtime enforcement

**Issue:** The proposed test sets `os.environ['MUTATIONS_DISABLED'] = 'false'` in a Python subprocess and calls `mutations_disabled()`. This tests the function, not the actual FastAPI lifespan. The compose has `MUTATIONS_DISABLED=true`, so the lifespan passes. Setting env to `false` in a subprocess doesn't test the compose-level configuration.

**Fix:** Test GAP-001 via the API endpoint — the canonical path:

```bash
docker exec hermes-product-os-prod python3 -c "
import urllib.request
r = urllib.request.urlopen('http://localhost:8080/api/health')
print(r.read().decode())
"
# Already tests: mutations=DISABLED

# The compose-level enforcement is proven by:
# Compose has MUTATIONS_DISABLED=true
# Health endpoint shows DISABLED
# GAP-001 is proven at source level (277 tests)
```

**P4 Plan Change:** Remove subprocess env mutation. Test health endpoint as the canonical proof that mutations are disabled at the application level. GAP-001 enforcement is independently proven by source tests and TASK-001 container regression.

---

## DEFECT 3 — Ambiguous image build

**Issue:** `docker build -t hermes-product-os-hpos:prod-0c6ba97 .` rebuilds from current working directory. If the checkout directory isn't at commit 0c6ba97, the image won't match.

**Fix:** Instead of rebuilding, retag from the already-built-and-verified P3 image:

```bash
# The P3 init image was already built from commit 0c6ba97
# and verified. Retag it:
docker tag hermes-product-os-hpos:prod-0c6ba97 hermes-product-os-hpos:prod-0c6ba97
```

Or, if rebuilding is needed:

```bash
cd /tmp/hpos-p4 && git checkout 0c6ba97 && git log --oneline -1
docker build -t hermes-product-os-hpos:prod-0c6ba97 .
```

**P4 Plan Change:** Use retag from already-built P3 image (verified at P3). Fallback: build from exact checkout.

---

## DEFECT 4 — Healthcheck compatibility with read_only + cap_drop ALL

**Issue:** Concern that healthcheck Python script might need filesystem access.

**Analysis:** Healthcheck runs `python3 -c "import urllib.request; urllib.request.urlopen(...)"`. This is purely network (localhost) + Python stdlib. No filesystem writes. No capabilities needed. Compatible with `read_only: true` and `cap_drop ALL`.

**Verdict:** No change needed. Healthcheck is compatible.

---

## DEFECT 5 — WAL/SHM ownership after API startup

**Issue:** Concern that UID 10010 can't create WAL/SHM in the data directory.

**Analysis:** Data directory is `10010:10010 / 750`. UID 10010 has W_OK. SQLite creates WAL/SHM on first DB open. Files inherit the creating process's UID/GID (10010:10010). No issue.

**Verdict:** No change needed.

---

## DEFECT 6 — Rollback preserves production.db

**Issue:** Confirm `docker compose down` doesn't destroy volumes.

**Analysis:** `docker compose down` stops and removes containers + networks. Named volumes are NOT removed (requires explicit `-v` flag). `docker compose down` preserves volumes. Confirmed.

**Verdict:** No change needed.

---

## DEFECT 7 — Immutable read-only DB verification before startup

**Issue:** Should verify DB integrity before starting the production API.

**Fix:** Use read-only SQLite URI to avoid creating root-owned WAL/SHM:

```bash
sqlite3 "file:$MOUNTPOINT/production.db?mode=ro" "PRAGMA integrity_check;"
```

**P4 Plan Change:** Add pre-startup verification with `mode=ro` URI.

---

## Corrected P4 Execution Plan

```bash
# VPS TERMINAL

# === CHECKPOINT 0: Preflight ===
# 1 — Source checkout
rm -rf /tmp/hpos-p4 && git clone https://github.com/amjadthaufeeg/hermes-os-foundation.git /tmp/hpos-p4
cd /tmp/hpos-p4 && git checkout d816fbf && git log --oneline -1
# Expected: d816fbf fix: P4 — production compose updated to prod-0c6ba97

# 2 — Copy compose, verify hash
cp deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
sha256sum deploy/docker-compose.prod.yml /docker/hermes-product-os-prod/docker-compose.yml
# Must match

# 3 — Validate compose
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml config -q && echo "VALID"

# 4 — Read-only DB verification (no WAL/SHM creation)
MOUNTPOINT=$(docker volume inspect hermes-product-os-prod_hpos-prod-data --format '{{.Mountpoint}}')
test -f "$MOUNTPOINT/production.db" && echo "DB_OK"
sqlite3 "file:$MOUNTPOINT/production.db?mode=ro" "PRAGMA integrity_check;"
# Expected: ok
sqlite3 "file:$MOUNTPOINT/production.db?mode=ro" "SELECT COUNT(*) FROM decisions;"
# Expected: 0

# 5 — No production container running
docker ps -a --filter name=^hermes-product-os-prod$ -q | grep -q . && echo "STOP" || echo "NO_CONTAINER_OK"

# 6 — Image available (retag from P3 or verify)
docker image inspect hermes-product-os-hpos:prod-0c6ba97 --format '{{.Id}}' || {
    cd /tmp/hpos-p4 && docker build -t hermes-product-os-hpos:prod-0c6ba97 .
}
docker run --rm hermes-product-os-hpos:prod-0c6ba97 id hermes
# Expected: uid=10010(hermes) gid=10010(hermes)

# === CHECKPOINT 1: Start production API ===
# 7 — Start
cd /docker/hermes-product-os-prod
docker compose up -d

# 8 — Wait for healthy
sleep 15
docker ps --filter name=hermes-product-os-prod --format '{{.Names}} {{.Status}}'
# Expected: healthy

# === CHECKPOINT 2: Verify ===
# 9 — Health endpoint (canonical proof)
docker exec hermes-product-os-prod python3 -c "
import urllib.request
r = urllib.request.urlopen('http://localhost:8080/api/health')
print(r.read().decode())
"
# Expected: environment=PRODUCTION, mutations=DISABLED

# 10 — Runtime UID confirmed
docker exec hermes-product-os-prod id
# Expected: uid=10010(hermes) gid=10010(hermes)

# 11 — DB accessible, 0 decisions, integrity ok
docker exec hermes-product-os-prod python3 -c "
from backend.hos4c.database import get_db
with get_db() as db:
    print('Decisions:', db.execute('SELECT COUNT(*) FROM decisions').fetchone()[0])
    print('Tables:', [r[0] for r in db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])
"
# Expected: 0 decisions, 5 tables

# 12 — Compose user in inspect
docker inspect hermes-product-os-prod --format '{{.Config.User}}'
# Expected: 10010:10010

# 13 — No host ports
docker inspect hermes-product-os-prod --format '{{.NetworkSettings.Ports}}'
# Expected: <no value> or {}

# 14 — WAL/SHM ownership (if created by API)
stat -c '%a %U:%G' "$MOUNTPOINT/production.db-wal" 2>/dev/null || echo "WAL_NOT_CREATED_YET"
# If present: expected 10010:10010

# 15 — Staging + Test-B healthy
docker ps --filter name=hermes-product-os --format '{{.Names}} {{.Status}}' | sort
```

## Rollback

```bash
docker compose -f /docker/hermes-product-os-prod/docker-compose.yml down
# Container + network removed. Volume + production.db preserved.
```

## P4 PASS Criteria

| # | Criterion |
|---|---|
| 1 | Container healthy |
| 2 | Health: `PRODUCTION`, `mutations: DISABLED` |
| 3 | Runtime UID: 10010 |
| 4 | DB: 0 decisions, 5 tables, integrity ok |
| 5 | Compose user: `10010:10010` |
| 6 | No host ports |
| 7 | No root-owned WAL/SHM from host-side sqlite3 |
| 8 | No B2 credentials |
| 9 | Staging healthy |
| 10 | Test-B healthy |