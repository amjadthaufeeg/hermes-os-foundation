#!/usr/bin/env bash
set -euo pipefail

PINNED_HERMES_SHA="${PINNED_HERMES_SHA:-}"
BUILDER_USER="${HERMES_BUILDER_USER:-hermesbuilder}"
RELAY_LABEL="ai.hermes.ingress-relay"
WORKER_LABEL="ai.hermes.builder-worker"
REPORTER_LABEL="ai.hermes.builder-reporter"
RELAY_PLIST="/Library/LaunchDaemons/${RELAY_LABEL}.plist"

fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
say() { printf '\n==> %s\n' "$*"; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS required"
[[ "$(id -u)" -eq 0 ]] || fail "run through sudo from main/admin account"
[[ "$PINNED_HERMES_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "PINNED_HERMES_SHA required"
id "$BUILDER_USER" >/dev/null 2>&1 || fail "builder account missing"
if id -Gn "$BUILDER_USER" | tr ' ' '\n' | grep -qx admin; then fail "builder account must remain non-admin"; fi

BUILDER_HOME="$(dscl . -read "/Users/$BUILDER_USER" NFSHomeDirectory | awk '{print $2}')"
APP_ROOT="$BUILDER_HOME/Library/Application Support/HermesBuilder"
FOUNDATION_REPO="$BUILDER_HOME/projects/hermes-os-foundation"
SOURCE_ROOT="$APP_ROOT/source"
CONTROL_KEY="$BUILDER_HOME/.ssh/hermes-control-deploy"
FOUNDATION_KEY="$BUILDER_HOME/.ssh/hermes-foundation-deploy"
KNOWN_HOSTS="$BUILDER_HOME/.ssh/hermes-builder-known_hosts"
LOG_ROOT="$APP_ROOT/logs"

for p in "$FOUNDATION_REPO/.git" "$CONTROL_KEY" "$FOUNDATION_KEY" "$KNOWN_HOSTS" "$APP_ROOT/config.json"; do [[ -e "$p" ]] || fail "required asset missing: $p"; done
mkdir -p "$LOG_ROOT"

say "Refreshing pinned runtime source"
SSH_CMD="ssh -i $FOUNDATION_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KNOWN_HOSTS"
(
  cd "$BUILDER_HOME"
  /usr/bin/sudo -u "$BUILDER_USER" /usr/bin/env HOME="$BUILDER_HOME" GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="$SSH_CMD" \
    git -C "$FOUNDATION_REPO" fetch origin "$PINNED_HERMES_SHA"
)
/usr/bin/sudo -u "$BUILDER_USER" git -C "$FOUNDATION_REPO" cat-file -e "$PINNED_HERMES_SHA^{commit}" || fail "pinned source unavailable"
rm -rf "$SOURCE_ROOT.new"
/usr/bin/sudo -u "$BUILDER_USER" git clone --no-checkout "$FOUNDATION_REPO" "$SOURCE_ROOT.new"
/usr/bin/sudo -u "$BUILDER_USER" git -C "$SOURCE_ROOT.new" checkout --detach "$PINNED_HERMES_SHA"
[[ "$(/usr/bin/sudo -u "$BUILDER_USER" git -C "$SOURCE_ROOT.new" rev-parse HEAD)" == "$PINNED_HERMES_SHA" ]] || fail "runtime source mismatch"
rm -rf "$SOURCE_ROOT.old"
[[ -d "$SOURCE_ROOT" ]] && mv "$SOURCE_ROOT" "$SOURCE_ROOT.old" || true
mv "$SOURCE_ROOT.new" "$SOURCE_ROOT"
chown -R "$BUILDER_USER":staff "$SOURCE_ROOT"

cat > "$RELAY_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$RELAY_LABEL</string>
<key>UserName</key><string>$BUILDER_USER</string>
<key>WorkingDirectory</key><string>$BUILDER_HOME</string>
<key>ProgramArguments</key><array>
<string>/usr/bin/python3</string><string>-m</string><string>deploy.builder_dispatch.ingress_relay</string><string>--poll</string><string>20</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$SOURCE_ROOT</string>
<key>HOME</key><string>$BUILDER_HOME</string>
<key>PATH</key><string>/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin</string>
<key>HERMES_BUILDER_CONTROL_DIR</key><string>$APP_ROOT/hermes-control</string>
<key>HERMES_CONTROL_SSH_KEY</key><string>$CONTROL_KEY</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
<key>StandardOutPath</key><string>$LOG_ROOT/ingress-relay.out.log</string>
<key>StandardErrorPath</key><string>$LOG_ROOT/ingress-relay.err.log</string>
</dict></plist>
PLIST
chown root:wheel "$RELAY_PLIST"; chmod 644 "$RELAY_PLIST"

say "Restarting background services on pinned runtime"
launchctl bootout "system/$RELAY_LABEL" >/dev/null 2>&1 || true
launchctl bootstrap system "$RELAY_PLIST"
launchctl kickstart -k "system/$RELAY_LABEL"
# Worker/reporter already have system plists from the background migration; restart if present.
if [[ -f "/Library/LaunchDaemons/${WORKER_LABEL}.plist" ]]; then launchctl kickstart -k "system/$WORKER_LABEL" || true; fi
if [[ -f "/Library/LaunchDaemons/${REPORTER_LABEL}.plist" ]]; then launchctl kickstart -k "system/$REPORTER_LABEL" || true; fi
sleep 3
launchctl print "system/$RELAY_LABEL" >/dev/null || fail "ingress relay failed to load"

# One synchronous pass proves the module loads and can access the transport clone.
cd "$BUILDER_HOME"
/usr/bin/sudo -u "$BUILDER_USER" /usr/bin/env -i HOME="$BUILDER_HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" \
  PYTHONPATH="$SOURCE_ROOT" HERMES_BUILDER_CONTROL_DIR="$APP_ROOT/hermes-control" HERMES_CONTROL_SSH_KEY="$CONTROL_KEY" \
  /usr/bin/python3 -m deploy.builder_dispatch.ingress_relay --once

printf '\nHERMES_INGRESS_RELAY_READY\nSOURCE_SHA=%s\nBRANCH=chatgpt-ingress\n' "$PINNED_HERMES_SHA"
