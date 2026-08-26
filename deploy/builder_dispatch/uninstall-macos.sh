#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$HOME/Library/Application Support/HermesBuilder"
PLIST="$HOME/Library/LaunchAgents/ai.hermes.builder-worker.plist"
LABEL="ai.hermes.builder-worker"
PURGE=0
[[ "${1:-}" == "--purge-clones" ]] && PURGE=1

launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
rm -f "$PLIST"
rm -rf "$APP_ROOT/source" "$APP_ROOT/state" "$APP_ROOT/logs" "$APP_ROOT/hermes-control" "$APP_ROOT/config.json" "$APP_ROOT/worker-status.json" "$APP_ROOT/known_hosts" "$APP_ROOT/transport.lock"
if [[ "$PURGE" -eq 1 ]]; then
  rm -rf "$APP_ROOT/task-clones"
fi
printf 'Hermes Builder launch agent removed.\n'
printf 'Deploy keys were NOT deleted or revoked automatically. Revoke them in GitHub manually.\n'
printf 'Kimi credentials were NOT removed. Run: kimi logout\n'
if [[ "$PURGE" -eq 0 ]]; then
  printf 'Task clones were preserved. Re-run with --purge-clones to delete them.\n'
fi
