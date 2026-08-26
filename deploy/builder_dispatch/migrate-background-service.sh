#!/usr/bin/env bash
set -euo pipefail

PINNED_HERMES_SHA="${PINNED_HERMES_SHA:-}"
BUILDER_USER="${HERMES_BUILDER_USER:-hermesbuilder}"
WORKER_LABEL="ai.hermes.builder-worker"
REPORTER_LABEL="ai.hermes.builder-reporter"
WORKER_PLIST="/Library/LaunchDaemons/${WORKER_LABEL}.plist"
REPORTER_PLIST="/Library/LaunchDaemons/${REPORTER_LABEL}.plist"
REPORT_ROOT="/Users/Shared/HermesBuilderReports"

say() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS required"
[[ "$PINNED_HERMES_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "PINNED_HERMES_SHA must be an immutable commit SHA"
[[ "$(id -u)" -eq 0 ]] || fail "Run this migration through sudo from the admin/main account"
id "$BUILDER_USER" >/dev/null 2>&1 || fail "builder account not found: $BUILDER_USER"
if id -Gn "$BUILDER_USER" | tr ' ' '\n' | grep -qx admin; then fail "builder account must remain non-admin"; fi

BUILDER_UID="$(id -u "$BUILDER_USER")"
BUILDER_HOME="$(dscl . -read "/Users/$BUILDER_USER" NFSHomeDirectory | awk '{print $2}')"
[[ -d "$BUILDER_HOME" ]] || fail "builder home not found"
APP_ROOT="$BUILDER_HOME/Library/Application Support/HermesBuilder"
FOUNDATION_REPO="$BUILDER_HOME/projects/hermes-os-foundation"
SOURCE_ROOT="$APP_ROOT/source"
CONFIG="$APP_ROOT/config.json"
STATE_ROOT="$APP_ROOT/state"
LOG_ROOT="$APP_ROOT/logs"
CONTROL_KEY="$BUILDER_HOME/.ssh/hermes-control-deploy"
FOUNDATION_KEY="$BUILDER_HOME/.ssh/hermes-foundation-deploy"
KNOWN_HOSTS="$BUILDER_HOME/.ssh/hermes-builder-known_hosts"
KIMI="$(/usr/bin/sudo -u "$BUILDER_USER" /bin/zsh -lc 'command -v kimi' 2>/dev/null || true)"
PYTHON="/usr/bin/python3"

for p in "$CONFIG" "$CONTROL_KEY" "$FOUNDATION_KEY"; do [[ -e "$p" ]] || fail "required builder asset missing: $p"; done
[[ -x "$KIMI" ]] || fail "Kimi executable unavailable for $BUILDER_USER"
[[ -x "$PYTHON" ]] || fail "python3 unavailable at $PYTHON"

mkdir -p "$REPORT_ROOT"
chown "$BUILDER_USER":staff "$REPORT_ROOT"
chmod 755 "$REPORT_ROOT"

say "Verifying Kimi works without an interactive login session"
KIMI_DIR="$(dirname "$KIMI")"
set +e
PROBE="$(/usr/bin/sudo -u "$BUILDER_USER" /usr/bin/env -i HOME="$BUILDER_HOME" PATH="$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=C.UTF-8 LC_ALL=C.UTF-8 "$KIMI" -m kimi-code/k3-256k -p 'Reply with exactly KIMI_BUILDER_READY and do not call tools.' --output-format text 2>&1)"
PROBE_RC=$?
set -e
[[ $PROBE_RC -eq 0 && "$PROBE" == *KIMI_BUILDER_READY* ]] || fail "Kimi background capability probe failed"

say "Refreshing pinned runtime source"
SSH_CMD="ssh -i $FOUNDATION_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KNOWN_HOSTS"
/usr/bin/sudo -u "$BUILDER_USER" /usr/bin/env HOME="$BUILDER_HOME" GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="$SSH_CMD" git -C "$FOUNDATION_REPO" fetch origin "$PINNED_HERMES_SHA"
/usr/bin/sudo -u "$BUILDER_USER" git -C "$FOUNDATION_REPO" cat-file -e "$PINNED_HERMES_SHA^{commit}" || fail "pinned source unavailable"
rm -rf "$SOURCE_ROOT.new"
/usr/bin/sudo -u "$BUILDER_USER" git clone --no-checkout "$FOUNDATION_REPO" "$SOURCE_ROOT.new"
/usr/bin/sudo -u "$BUILDER_USER" git -C "$SOURCE_ROOT.new" checkout --detach "$PINNED_HERMES_SHA"
[[ "$(/usr/bin/sudo -u "$BUILDER_USER" git -C "$SOURCE_ROOT.new" rev-parse HEAD)" == "$PINNED_HERMES_SHA" ]] || fail "runtime source mismatch"
rm -rf "$SOURCE_ROOT.old"
[[ -d "$SOURCE_ROOT" ]] && mv "$SOURCE_ROOT" "$SOURCE_ROOT.old" || true
mv "$SOURCE_ROOT.new" "$SOURCE_ROOT"
chown -R "$BUILDER_USER":staff "$SOURCE_ROOT"

say "Stopping old per-login LaunchAgent if present"
launchctl bootout "gui/$BUILDER_UID/$WORKER_LABEL" >/dev/null 2>&1 || true
rm -f "$BUILDER_HOME/Library/LaunchAgents/${WORKER_LABEL}.plist"

cat > "$WORKER_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$WORKER_LABEL</string>
<key>UserName</key><string>$BUILDER_USER</string>
<key>ProgramArguments</key><array>
<string>$PYTHON</string><string>-m</string><string>deploy.builder_dispatch.mac_worker</string>
<string>--config</string><string>$CONFIG</string>
<string>--state-dir</string><string>$STATE_ROOT</string>
<string>--poll</string><string>30</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$SOURCE_ROOT</string>
<key>HOME</key><string>$BUILDER_HOME</string>
<key>PATH</key><string>$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
<key>HERMES_BUILDER_CONTROL_DIR</key><string>$APP_ROOT/hermes-control</string>
<key>HERMES_CONTROL_SSH_KEY</key><string>$CONTROL_KEY</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
<key>StandardOutPath</key><string>$LOG_ROOT/worker-daemon.out.log</string>
<key>StandardErrorPath</key><string>$LOG_ROOT/worker-daemon.err.log</string>
</dict></plist>
PLIST

cat > "$REPORTER_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$REPORTER_LABEL</string>
<key>UserName</key><string>$BUILDER_USER</string>
<key>ProgramArguments</key><array><string>$PYTHON</string><string>-m</string><string>deploy.builder_dispatch.report_bridge</string></array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$SOURCE_ROOT</string>
<key>HOME</key><string>$BUILDER_HOME</string>
<key>PATH</key><string>/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin</string>
<key>HERMES_BUILDER_CONTROL_DIR</key><string>$APP_ROOT/hermes-control</string>
<key>HERMES_CONTROL_SSH_KEY</key><string>$CONTROL_KEY</string>
<key>HERMES_REPORT_ROOT</key><string>$REPORT_ROOT</string>
</dict>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$LOG_ROOT/reporter-daemon.out.log</string>
<key>StandardErrorPath</key><string>$LOG_ROOT/reporter-daemon.err.log</string>
</dict></plist>
PLIST

chown root:wheel "$WORKER_PLIST" "$REPORTER_PLIST"
chmod 644 "$WORKER_PLIST" "$REPORTER_PLIST"

# Stop any pre-existing system services. The worker intentionally remains paused
# until the sanitized reconciliation report is reviewed and approved.
launchctl bootout "system/$WORKER_LABEL" >/dev/null 2>&1 || true
launchctl bootout "system/$REPORTER_LABEL" >/dev/null 2>&1 || true
launchctl bootstrap system "$REPORTER_PLIST"
launchctl kickstart -k "system/$REPORTER_LABEL"
sleep 3
launchctl print "system/$REPORTER_LABEL" >/dev/null || fail "reporter LaunchDaemon failed to load"
if launchctl print "system/$WORKER_LABEL" >/dev/null 2>&1; then fail "worker should be paused pending reconciliation"; fi

say "Verifying sanitized report bridge"
for _ in 1 2 3 4 5; do
  [[ -f "$REPORT_ROOT/status-and-reconciliation.json" ]] && break
  sleep 2
done
[[ -f "$REPORT_ROOT/status-and-reconciliation.json" ]] || fail "report bridge did not publish"
chmod 644 "$REPORT_ROOT/status-and-reconciliation.json"

printf '\nHERMES_BACKGROUND_REPORTING_READY\nUSER=%s\nSOURCE_SHA=%s\nWORKER_STATE=PAUSED_PENDING_RECONCILIATION\nREPORT=%s\nWORKER_PLIST=%s\n' "$BUILDER_USER" "$PINNED_HERMES_SHA" "$REPORT_ROOT/status-and-reconciliation.json" "$WORKER_PLIST"
