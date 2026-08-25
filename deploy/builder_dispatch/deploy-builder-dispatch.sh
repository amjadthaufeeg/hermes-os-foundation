#!/usr/bin/env bash
# GATED deployment helper for Hermes builder dispatch.
# Installs orchestration runtime only; does not alter HOS authority policy,
# production application code, databases, snapshots, or Docker resources.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: builder dispatch deployment must run as root" >&2
  exit 2
fi

SOURCE_ROOT="$(git rev-parse --show-toplevel)"
SOURCE_SHA="$(git -C "$SOURCE_ROOT" rev-parse HEAD)"
EXPECTED_SHA="${EXPECTED_SHA:-}"
if [[ -z "$EXPECTED_SHA" || "$SOURCE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "ERROR: exact reviewed EXPECTED_SHA is required (got=$SOURCE_SHA expected=${EXPECTED_SHA:-unset})" >&2
  exit 2
fi

PKG_SRC="$SOURCE_ROOT/deploy/builder_dispatch"
SAFE_TRANSPORT_SRC="$SOURCE_ROOT/deploy/hos_auto_02/transport_safe.py"
WATCHER_ENTRY_SRC="$SOURCE_ROOT/deploy/hos_auto_02/watcher_entry.py"
SERVICE_SRC="$PKG_SRC/systemd/hermes-builder-dispatch.service"
RUNTIME_ROOT="/opt/hermes-auto"
PKG_DST="$RUNTIME_ROOT/deploy/builder_dispatch"
HOS02_DST="$RUNTIME_ROOT/deploy/hos_auto_02"
SERVICE_DST="/etc/systemd/system/hermes-builder-dispatch.service"
CONFIG="/etc/hermes-auto/builder-dispatch.json"
STATE="/var/lib/hermes-builder"
BACKUP="/var/lib/hermes-auto/deploy-backups/builder-dispatch-${SOURCE_SHA:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"

for required in "$PKG_SRC/adapter.py" "$PKG_SRC/queue_watcher.py" "$SAFE_TRANSPORT_SRC" "$WATCHER_ENTRY_SRC" "$SERVICE_SRC"; do
  [[ -f "$required" ]] || { echo "ERROR: missing $required" >&2; exit 2; }
done

# Config is host-owned and secret-free. Never synthesize or overwrite it here.
[[ -f "$CONFIG" ]] || {
  echo "ERROR: missing $CONFIG. Configure verified builder executable paths first." >&2
  exit 3
}
[[ "$(stat -c '%a' "$CONFIG")" =~ ^(600|640|400|440)$ ]] || {
  echo "ERROR: $CONFIG permissions must be 0600/0640/0400/0440" >&2
  exit 3
}

# Fail closed unless at least one configured builder executable is absolute,
# executable, and present. Validation uses the adapter's own config loader.
PYTHONPATH="$SOURCE_ROOT" "$RUNTIME_ROOT/venv/bin/python3" - "$CONFIG" <<'PY'
import os, sys
from deploy.builder_dispatch.adapter import load_config
specs = load_config(sys.argv[1])
if not specs:
    raise SystemExit("no approved builders configured")
usable = []
for name, spec in specs.items():
    if os.path.isabs(spec.executable) and os.path.isfile(spec.executable) and os.access(spec.executable, os.X_OK):
        usable.append(name)
if not usable:
    raise SystemExit("no configured builder executable is installed/executable")
print("USABLE_BUILDERS=" + ",".join(sorted(usable)))
PY

mkdir -p "$BACKUP" "$STATE" "$PKG_DST" "$HOS02_DST"
chown hermes-auto:hermes-auto "$STATE"
chmod 0700 "$STATE"

backup_if_exists() {
  local src="$1" name="$2"
  if [[ -e "$src" ]]; then cp -a "$src" "$BACKUP/$name"; fi
}
backup_if_exists "$PKG_DST" builder_dispatch
backup_if_exists "$HOS02_DST/transport_safe.py" transport_safe.py
backup_if_exists "$HOS02_DST/watcher_entry.py" watcher_entry.py
backup_if_exists "$SERVICE_DST" hermes-builder-dispatch.service

rollback() {
  rc=$?
  if [[ $rc -eq 0 ]]; then return; fi
  echo "DEPLOYMENT FAILED (rc=$rc) — restoring builder dispatch runtime" >&2
  rm -rf "$PKG_DST"
  if [[ -e "$BACKUP/builder_dispatch" ]]; then cp -a "$BACKUP/builder_dispatch" "$PKG_DST"; fi
  if [[ -f "$BACKUP/transport_safe.py" ]]; then cp -a "$BACKUP/transport_safe.py" "$HOS02_DST/transport_safe.py"; else rm -f "$HOS02_DST/transport_safe.py"; fi
  if [[ -f "$BACKUP/watcher_entry.py" ]]; then cp -a "$BACKUP/watcher_entry.py" "$HOS02_DST/watcher_entry.py"; fi
  if [[ -f "$BACKUP/hermes-builder-dispatch.service" ]]; then
    cp -a "$BACKUP/hermes-builder-dispatch.service" "$SERVICE_DST"
  else
    rm -f "$SERVICE_DST"
  fi
  systemctl daemon-reload || true
  systemctl restart hermes-r2-watcher || true
  systemctl restart hermes-builder-dispatch || true
  exit "$rc"
}
trap rollback ERR

rm -rf "$PKG_DST"
mkdir -p "$PKG_DST"
cp -a "$PKG_SRC/." "$PKG_DST/"
install -o root -g root -m 0644 "$SAFE_TRANSPORT_SRC" "$HOS02_DST/transport_safe.py"
install -o root -g root -m 0644 "$WATCHER_ENTRY_SRC" "$HOS02_DST/watcher_entry.py"
install -o root -g root -m 0644 "$SERVICE_SRC" "$SERVICE_DST"
chown -R root:root "$PKG_DST"
find "$PKG_DST" -type d -exec chmod 0755 {} +
find "$PKG_DST" -type f -exec chmod 0644 {} +

# Validate source before touching services.
PYTHONPATH="$RUNTIME_ROOT" "$RUNTIME_ROOT/venv/bin/python3" -m py_compile \
  "$PKG_DST/adapter.py" "$PKG_DST/queue_watcher.py" \
  "$HOS02_DST/transport_safe.py" "$HOS02_DST/watcher_entry.py"

systemctl daemon-reload
systemctl restart hermes-r2-watcher
systemctl enable --now hermes-builder-dispatch
systemctl is-active --quiet hermes-r2-watcher
systemctl is-active --quiet hermes-builder-dispatch

# Service remains unprivileged; HOS watcher stays on its established identity.
[[ "$(systemctl show hermes-r2-watcher -p User --value)" == "hermes-auto" ]]
[[ "$(systemctl show hermes-builder-dispatch -p User --value)" == "hermes-auto" ]]
systemctl show hermes-builder-dispatch -p ExecStart --value | grep -q 'deploy.builder_dispatch.queue_watcher'

trap - ERR
echo "BUILDER_DISPATCH_DEPLOYED"
echo "SOURCE_SHA=$SOURCE_SHA"
echo "BACKUP=$BACKUP"
