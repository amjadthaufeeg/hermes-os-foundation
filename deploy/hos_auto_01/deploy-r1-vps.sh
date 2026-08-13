#!/usr/bin/env bash
# HOS-AUTO-01 R1 VPS Deployment
# Source commit: 357a706cb9ba48285f5403df6898fdebc360d8f3
# Run as root on 141.136.44.66
# This script is GATED — requires explicit Amjad authorization to run.
set -euo pipefail

SRC_COMMIT="357a706cb9ba48285f5403df6898fdebc360d8f3"
INSTALL_ROOT="/opt/hermes-auto"
SRC_DIR="/tmp/hos-auto-01-src"

echo "=== STEP 0: Verify no production changes will occur ==="
docker ps --filter "name=hermes-product-os-prod" --format '{{.Names}} {{.Status}}'
docker ps --filter "name=hermes-phase-b-reader" --format '{{.Names}} {{.Status}}'
echo "Production containers listed above must remain untouched."

echo "=== STEP 1: Clone exact source ==="
rm -rf "$SRC_DIR"
git clone -q https://github.com/amjadthaufeeg/hermes-os-foundation.git "$SRC_DIR"
cd "$SRC_DIR"
git checkout -q "$SRC_COMMIT"
echo "HEAD: $(git rev-parse HEAD)"
echo "Expected: $SRC_COMMIT"

echo "=== STEP 2: Create hermes-auto system user ==="
if ! id hermes-auto >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin hermes-auto
  echo "Created hermes-auto user"
else
  echo "hermes-auto already exists"
fi
# Prove no sudo, no docker group
echo "groups: $(id hermes-auto)"
echo "sudo check (should be empty): $(sudo -l -U hermes-auto 2>&1 || true)"

echo "=== STEP 3: Create directory hierarchy ==="
mkdir -p "$INSTALL_ROOT"/{bin,policy,evidence,receipts,deps,logs}
mkdir -p /run/hermes-auto

echo "=== STEP 4: Install artifacts ==="
cp "$SRC_DIR/deploy/hos_auto_01/bin/broker.py" "$INSTALL_ROOT/bin/broker.py"
cp "$SRC_DIR/deploy/hos_auto_01/bin/bridge.py" "$INSTALL_ROOT/bin/bridge.py"
cp "$SRC_DIR/deploy/hos_auto_01/bin/preflight.py" "$INSTALL_ROOT/bin/preflight.py"
cp "$SRC_DIR/deploy/hos_auto_01/policy/authority.py" "$INSTALL_ROOT/policy/authority.py"
cp "$SRC_DIR/deploy/hos_auto_01/deps/requirements.txt" "$INSTALL_ROOT/deps/requirements.txt"

# Also install the package for bridge imports (deploy.hos_auto_01.*)
mkdir -p "$INSTALL_ROOT/deploy/hos_auto_01"/{bin,policy}
cp "$SRC_DIR/deploy/__init__.py" "$INSTALL_ROOT/deploy/__init__.py"
cp "$SRC_DIR/deploy/hos_auto_01/__init__.py" "$INSTALL_ROOT/deploy/hos_auto_01/__init__.py"
cp "$SRC_DIR/deploy/hos_auto_01/bin/"*.py "$INSTALL_ROOT/deploy/hos_auto_01/bin/"
cp "$SRC_DIR/deploy/hos_auto_01/policy/"*.py "$INSTALL_ROOT/deploy/hos_auto_01/policy/"

echo "=== STEP 5: Configure ownership/modes (hardened) ==="
# Broker + policy: root-owned, NOT writable by hermes-auto
chown -R root:root "$INSTALL_ROOT/bin" "$INSTALL_ROOT/policy" "$INSTALL_ROOT/deploy" "$INSTALL_ROOT/deps"
chmod 755 "$INSTALL_ROOT/bin" "$INSTALL_ROOT/policy" "$INSTALL_ROOT/deploy" "$INSTALL_ROOT/deps"
chmod 755 "$INSTALL_ROOT/bin/broker.py" "$INSTALL_ROOT/bin/bridge.py" "$INSTALL_ROOT/bin/preflight.py"
chmod 644 "$INSTALL_ROOT/policy/authority.py" "$INSTALL_ROOT/deps/requirements.txt"
chmod 644 "$INSTALL_ROOT/deploy"/*.py "$INSTALL_ROOT/deploy/hos_auto_01"/*.py
chmod 644 "$INSTALL_ROOT/deploy/hos_auto_01/bin/"*.py "$INSTALL_ROOT/deploy/hos_auto_01/policy/"*.py

# Evidence + logs: hermes-auto writable
chown hermes-auto:hermes-auto "$INSTALL_ROOT/evidence" "$INSTALL_ROOT/logs"
chmod 700 "$INSTALL_ROOT/evidence" "$INSTALL_ROOT/logs"

# Receipts: root-owned, finalized (bridge reads via broker)
chown root:root "$INSTALL_ROOT/receipts"
chmod 700 "$INSTALL_ROOT/receipts"

echo "=== STEP 6: Install dependencies (venv) ==="
python3 -m venv "$INSTALL_ROOT/venv" 2>/dev/null || true
"$INSTALL_ROOT/venv/bin/pip" install -q -r "$INSTALL_ROOT/deps/requirements.txt" 2>&1 | tail -3

echo "=== STEP 7: Install systemd units ==="
cp "$SRC_DIR/deploy/hos_auto_01/systemd/hermes-broker.socket" /etc/systemd/system/hermes-broker.socket
cp "$SRC_DIR/deploy/hos_auto_01/systemd/hermes-broker@.service" /etc/systemd/system/hermes-broker@.service
chown root:root /etc/systemd/system/hermes-broker.socket /etc/systemd/system/hermes-broker@.service
chmod 644 /etc/systemd/system/hermes-broker.socket /etc/systemd/system/hermes-broker@.service

echo "=== STEP 8: daemon-reload + enable/start socket ==="
systemctl daemon-reload
systemctl enable hermes-broker.socket
systemctl start hermes-broker.socket
systemctl status hermes-broker.socket --no-pager | head -10

echo "=== STEP 9: Verify socket ==="
ls -la /run/hermes-auto/broker.sock
stat -c '%U:%G %a' /run/hermes-auto/broker.sock

echo "=== DEPLOYMENT COMPLETE ==="
echo "Verify hermes-auto cannot access docker.sock:"
sudo -u hermes-auto test -r /var/run/docker.sock && echo "FAIL: hermes-auto can read docker.sock" || echo "OK: hermes-auto cannot read docker.sock"
sudo -u hermes-auto docker ps 2>&1 | head -1 || true
