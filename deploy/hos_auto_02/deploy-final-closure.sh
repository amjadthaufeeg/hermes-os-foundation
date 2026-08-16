#!/usr/bin/env bash
# Final HOS closure deployment helper.
# GATED: must be run explicitly as root after Amjad approval.
# Scope: HOS watcher runtime only; no production DB/snapshot/Docker mutation.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: this GATED deployment must run as root" >&2
  exit 2
fi

SOURCE_ROOT="$(git rev-parse --show-toplevel)"
SOURCE_SHA="$(git -C "$SOURCE_ROOT" rev-parse HEAD)"
EXPECTED_SHA="${EXPECTED_SHA:-}"

if [[ -z "$EXPECTED_SHA" ]]; then
  echo "ERROR: EXPECTED_SHA is required" >&2
  exit 2
fi
if [[ "$SOURCE_SHA" != "$EXPECTED_SHA" ]]; then
  echo "ERROR: source SHA mismatch: got=$SOURCE_SHA expected=$EXPECTED_SHA" >&2
  exit 2
fi

UNIT_SRC="$SOURCE_ROOT/deploy/hos_auto_02/systemd/hermes-r2-watcher.service"
ENTRY_SRC="$SOURCE_ROOT/deploy/hos_auto_02/watcher_entry.py"
UNIT_DST="/etc/systemd/system/hermes-r2-watcher.service"
ENTRY_DST="/opt/hermes-auto/deploy/hos_auto_02/watcher_entry.py"
CANONICAL="/tmp/hos-auto-01-src"
BACKUP_ROOT="/var/lib/hermes-auto/deploy-backups/final-closure-${SOURCE_SHA:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"

[[ -f "$UNIT_SRC" ]] || { echo "ERROR: missing $UNIT_SRC" >&2; exit 2; }
[[ -f "$ENTRY_SRC" ]] || { echo "ERROR: missing $ENTRY_SRC" >&2; exit 2; }

mkdir -p "$BACKUP_ROOT"
if [[ -f "$UNIT_DST" ]]; then cp -a "$UNIT_DST" "$BACKUP_ROOT/hermes-r2-watcher.service"; fi
if [[ -f "$ENTRY_DST" ]]; then cp -a "$ENTRY_DST" "$BACKUP_ROOT/watcher_entry.py"; fi
if [[ -d "$CANONICAL/.git" ]]; then
  git -C "$CANONICAL" rev-parse HEAD > "$BACKUP_ROOT/previous-canonical-sha"
fi

rollback() {
  rc=$?
  if [[ $rc -eq 0 ]]; then return; fi
  echo "DEPLOYMENT FAILED (rc=$rc) — restoring watcher runtime" >&2
  if [[ -f "$BACKUP_ROOT/hermes-r2-watcher.service" ]]; then
    install -o root -g root -m 0644 "$BACKUP_ROOT/hermes-r2-watcher.service" "$UNIT_DST"
  fi
  if [[ -f "$BACKUP_ROOT/watcher_entry.py" ]]; then
    install -o root -g root -m 0644 "$BACKUP_ROOT/watcher_entry.py" "$ENTRY_DST"
  else
    rm -f "$ENTRY_DST"
  fi
  systemctl daemon-reload || true
  systemctl restart hermes-r2-watcher || true
  exit "$rc"
}
trap rollback ERR

# Install only the two root-owned runtime artifacts changed by closure work.
install -o root -g root -m 0644 "$ENTRY_SRC" "$ENTRY_DST"
install -o root -g root -m 0644 "$UNIT_SRC" "$UNIT_DST"

# Refresh the immutable execution checkout from this exact reviewed source.
NEW_CANONICAL="${CANONICAL}.new"
OLD_CANONICAL="${CANONICAL}.pre-final"
rm -rf "$NEW_CANONICAL"
cp -a "$SOURCE_ROOT" "$NEW_CANONICAL"
rm -rf "$OLD_CANONICAL"
if [[ -e "$CANONICAL" ]]; then mv "$CANONICAL" "$OLD_CANONICAL"; fi
mv "$NEW_CANONICAL" "$CANONICAL"
git config --system --replace-all safe.directory "$CANONICAL"
[[ "$(git -C "$CANONICAL" rev-parse HEAD)" == "$EXPECTED_SHA" ]]

systemctl daemon-reload
systemctl restart hermes-r2-watcher
systemctl is-active --quiet hermes-r2-watcher

# Boundary checks: still unprivileged and still using the closure entrypoint.
[[ "$(systemctl show hermes-r2-watcher -p User --value)" == "hermes-auto" ]]
systemctl show hermes-r2-watcher -p ExecStart --value | grep -q 'deploy.hos_auto_02.watcher_entry'
systemctl show hermes-r2-watcher -p Environment --value | grep -q 'TMPDIR=/var/lib/hermes-auto'

# Verify the watcher identity/preflight as the unprivileged service user.
sudo -u hermes-auto env \
  PATH="/opt/hermes-auto/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONPATH="/opt/hermes-auto" \
  git -C "$CANONICAL" rev-parse HEAD | grep -qx "$EXPECTED_SHA"

trap - ERR

echo "HOS_FINAL_CLOSURE_RUNTIME_DEPLOYED"
echo "SOURCE_SHA=$SOURCE_SHA"
echo "BACKUP_ROOT=$BACKUP_ROOT"
