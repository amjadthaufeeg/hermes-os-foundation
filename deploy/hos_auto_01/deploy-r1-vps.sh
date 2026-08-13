#!/usr/bin/env bash
# HOS-AUTO-01 R1 VPS Deployment
# Run as root on 141.136.44.66 from the repo checkout.
# This script uses its OWN checkout directory as the source (no re-clone).
# It must be run from a clean checkout of the authorized commit.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root = deploy/hos_auto_01/ -> ../.. -> ..
SRC_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_ROOT="/opt/hermes-auto"

echo "=== SOURCE IDENTITY ==="
cd "$SRC_DIR"
echo "Source dir: $SRC_DIR"
echo "HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'NOT-A-GIT-REPO')"
echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"

echo ""
echo "=== STEP 0: Verify production containers (must remain untouched) ==="
docker ps --filter "name=hermes-product-os-prod" --format '{{.Names}} {{.Status}}'
docker ps --filter "name=hermes-phase-b-reader" --format '{{.Names}} {{.Status}}'

echo ""
echo "=== STEP 1: Create hermes-auto system user ==="
if ! id hermes-auto >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin hermes-auto
  echo "Created hermes-auto"
else
  echo "hermes-auto already exists"
fi
echo "hermes-auto groups: $(id hermes-auto)"

echo ""
echo "=== STEP 2: Create directory hierarchy ==="
mkdir -p "$INSTALL_ROOT"/{bin,policy,evidence,receipts,deps,logs}
mkdir -p /run/hermes-auto

echo ""
echo "=== STEP 3: Install artifacts ==="
cp "$SRC_DIR/deploy/hos_auto_01/bin/broker.py" "$INSTALL_ROOT/bin/broker.py"
cp "$SRC_DIR/deploy/hos_auto_01/bin/bridge.py" "$INSTALL_ROOT/bin/bridge.py"
cp "$SRC_DIR/deploy/hos_auto_01/bin/preflight.py" "$INSTALL_ROOT/bin/preflight.py"
cp "$SRC_DIR/deploy/hos_auto_01/policy/authority.py" "$INSTALL_ROOT/policy/authority.py"
cp "$SRC_DIR/deploy/hos_auto_01/deps/requirements.txt" "$INSTALL_ROOT/deps/requirements.txt"

# Install the Python package for bridge imports (deploy.hos_auto_01.*)
mkdir -p "$INSTALL_ROOT/deploy/hos_auto_01"/{bin,policy}
cp "$SRC_DIR/deploy/__init__.py" "$INSTALL_ROOT/deploy/__init__.py" 2>/dev/null || true
cp "$SRC_DIR/deploy/hos_auto_01/__init__.py" "$INSTALL_ROOT/deploy/hos_auto_01/__init__.py" 2>/dev/null || true
cp "$SRC_DIR/deploy/hos_auto_01/bin/"*.py "$INSTALL_ROOT/deploy/hos_auto_01/bin/"
cp "$SRC_DIR/deploy/hos_auto_01/policy/"*.py "$INSTALL_ROOT/deploy/hos_auto_01/policy/"

echo ""
echo "=== STEP 4: Configure ownership/modes (hardened) ==="
chown -R root:root "$INSTALL_ROOT/bin" "$INSTALL_ROOT/policy" "$INSTALL_ROOT/deploy" "$INSTALL_ROOT/deps" "$INSTALL_ROOT/receipts"
chmod 755 "$INSTALL_ROOT/bin" "$INSTALL_ROOT/policy" "$INSTALL_ROOT/deploy" "$INSTALL_ROOT/deps" "$INSTALL_ROOT/receipts"
chmod 755 "$INSTALL_ROOT/bin/broker.py" "$INSTALL_ROOT/bin/bridge.py" "$INSTALL_ROOT/bin/preflight.py"
chmod 644 "$INSTALL_ROOT/policy/authority.py" "$INSTALL_ROOT/deps/requirements.txt"
find "$INSTALL_ROOT/deploy" -name '*.py' -exec chmod 644 {} \;

chown hermes-auto:hermes-auto "$INSTALL_ROOT/evidence" "$INSTALL_ROOT/logs"
chmod 700 "$INSTALL_ROOT/evidence" "$INSTALL_ROOT/logs"

echo ""
echo "=== STEP 5: Install dependencies (venv) ==="
python3 -m venv "$INSTALL_ROOT/venv" 2>/dev/null || true
"$INSTALL_ROOT/venv/bin/pip" install -q -r "$INSTALL_ROOT/deps/requirements.txt" 2>&1 | tail -3

echo ""
echo "=== STEP 6: Install systemd units + tmpfiles ==="
cp "$SRC_DIR/deploy/hos_auto_01/systemd/hermes-broker.socket" /etc/systemd/system/hermes-broker.socket
cp "$SRC_DIR/deploy/hos_auto_01/systemd/hermes-broker@.service" /etc/systemd/system/hermes-broker@.service
cp "$SRC_DIR/deploy/hos_auto_01/systemd/hermes-auto.tmpfiles" /etc/tmpfiles.d/hermes-auto.conf
chown root:root /etc/systemd/system/hermes-broker.socket /etc/systemd/system/hermes-broker@.service /etc/tmpfiles.d/hermes-auto.conf
chmod 644 /etc/systemd/system/hermes-broker.socket /etc/systemd/system/hermes-broker@.service /etc/tmpfiles.d/hermes-auto.conf
systemd-tmpfiles --create /etc/tmpfiles.d/hermes-auto.conf

echo ""
echo "=== STEP 7: daemon-reload + enable/start socket ==="
systemctl daemon-reload
systemctl enable hermes-broker.socket
systemctl start hermes-broker.socket
systemctl status hermes-broker.socket --no-pager | head -8

echo ""
echo "=== STEP 8: Verify socket ==="
ls -la /run/hermes-auto/broker.sock
stat -c 'socket owner:mode = %U:%G %a' /run/hermes-auto/broker.sock

echo ""
echo "=== STEP 9: Docker socket denial proof ==="
if sudo -u hermes-auto test -r /var/run/docker.sock 2>/dev/null; then
  echo "FAIL: hermes-auto can read docker.sock"
else
  echo "OK: hermes-auto CANNOT read docker.sock"
fi
echo "hermes-auto docker attempt (should fail):"
sudo -u hermes-auto docker ps 2>&1 | head -1 || echo "(permission denied - expected)"

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "Artifacts installed to $INSTALL_ROOT"
echo "Broker socket: /run/hermes-auto/broker.sock"
