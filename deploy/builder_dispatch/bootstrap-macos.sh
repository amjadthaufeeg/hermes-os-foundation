#!/usr/bin/env bash
set -euo pipefail

PINNED_HERMES_SHA="${PINNED_HERMES_SHA:-}"
EXPECTED_USER="${HERMES_BUILDER_EXPECTED_USER:-hermes-builder}"
FOUNDATION_REPO="${HERMES_FOUNDATION_REPO:-$HOME/projects/hermes-os-foundation}"
APP_ROOT="$HOME/Library/Application Support/HermesBuilder"
SOURCE_ROOT="$APP_ROOT/source"
STATE_ROOT="$APP_ROOT/state"
LOG_ROOT="$APP_ROOT/logs"
CLONE_ROOT="$APP_ROOT/task-clones"
CONFIG="$APP_ROOT/config.json"
PLIST="$HOME/Library/LaunchAgents/ai.hermes.builder-worker.plist"
LABEL="ai.hermes.builder-worker"
CONTROL_KEY="${HERMES_CONTROL_SSH_KEY:-$HOME/.ssh/hermes-control-deploy}"
FOUNDATION_KEY="${HERMES_FOUNDATION_SSH_KEY:-$HOME/.ssh/hermes-foundation-deploy}"
AVOA_KEY="${AVOA_SSH_KEY:-$HOME/.ssh/avoa-quote-engine-deploy}"

say() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required"
[[ "$PINNED_HERMES_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "PINNED_HERMES_SHA must be an immutable commit SHA"
[[ "$(id -u)" -ne 0 ]] || fail "Never run the builder as root"
[[ "$(id -un)" == "$EXPECTED_USER" ]] || fail "Run this only from the dedicated '$EXPECTED_USER' macOS account"
if id -Gn | tr ' ' '\n' | grep -qx admin; then
  fail "The builder account must be NON-ADMIN. Remove '$EXPECTED_USER' from the admin group first."
fi

for cmd in git python3 ssh launchctl; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done

check_key() {
  local key="$1" name="$2"
  [[ -f "$key" ]] || fail "$name deploy key missing: $key"
  local mode
  mode="$(stat -f '%Lp' "$key")"
  [[ "$mode" == "600" || "$mode" == "400" ]] || fail "$name deploy key must be chmod 600 (or 400), got $mode"
}
check_key "$CONTROL_KEY" "hermes-control"
check_key "$FOUNDATION_KEY" "hermes-os-foundation"
# AVOA may not yet be cloned, but the key is required before production AVOA building.
[[ -f "$AVOA_KEY" ]] && check_key "$AVOA_KEY" "avoa-quote-engine"

mkdir -p "$APP_ROOT" "$STATE_ROOT" "$LOG_ROOT" "$CLONE_ROOT" "$HOME/Library/LaunchAgents"
chmod 700 "$APP_ROOT" "$STATE_ROOT" "$LOG_ROOT" "$CLONE_ROOT"

ssh_env() {
  local key="$1"
  printf '%s' "ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$APP_ROOT/known_hosts"
}

verify_repo_key() {
  local repo="$1" key="$2"
  GIT_SSH_COMMAND="$(ssh_env "$key")" GIT_TERMINAL_PROMPT=0 \
    git ls-remote "git@github.com:$repo.git" HEAD >/dev/null 2>&1 || fail "Dedicated key cannot access $repo"
}
verify_repo_key "amjadthaufeeg/hermes-control" "$CONTROL_KEY"
verify_repo_key "amjadthaufeeg/hermes-os-foundation" "$FOUNDATION_KEY"
[[ -f "$AVOA_KEY" ]] && verify_repo_key "amjadthaufeeg/avoa-quote-engine" "$AVOA_KEY" || true

if [[ ! -d "$FOUNDATION_REPO/.git" ]]; then
  mkdir -p "$(dirname "$FOUNDATION_REPO")"
  GIT_SSH_COMMAND="$(ssh_env "$FOUNDATION_KEY")" GIT_TERMINAL_PROMPT=0 \
    git clone "git@github.com:amjadthaufeeg/hermes-os-foundation.git" "$FOUNDATION_REPO" || fail "Cannot clone foundation repo"
fi
ORIGIN="$(git -C "$FOUNDATION_REPO" remote get-url origin)"
[[ "$ORIGIN" == "git@github.com:amjadthaufeeg/hermes-os-foundation.git" || "$ORIGIN" == "https://github.com/amjadthaufeeg/hermes-os-foundation.git" ]] || fail "Unexpected foundation origin: $ORIGIN"

say "Loading reviewed Hermes source at immutable SHA $PINNED_HERMES_SHA"
GIT_SSH_COMMAND="$(ssh_env "$FOUNDATION_KEY")" git -C "$FOUNDATION_REPO" fetch origin "$PINNED_HERMES_SHA"
git -C "$FOUNDATION_REPO" cat-file -e "$PINNED_HERMES_SHA^{commit}" || fail "Pinned commit unavailable"
rm -rf "$SOURCE_ROOT"
git clone --no-checkout "$FOUNDATION_REPO" "$SOURCE_ROOT"
git -C "$SOURCE_ROOT" checkout --detach "$PINNED_HERMES_SHA"
[[ "$(git -C "$SOURCE_ROOT" rev-parse HEAD)" == "$PINNED_HERMES_SHA" ]] || fail "Pinned source mismatch"

PYTHON="$(command -v python3)"
"$PYTHON" - <<'PY'
import sys
assert sys.version_info >= (3,9), sys.version
PY

KIMI="$(command -v kimi || true)"
[[ -n "$KIMI" && -x "$KIMI" ]] || fail "Kimi Code CLI is not installed. Install it separately from Moonshot AI's official documentation, then rerun v3."
"$KIMI" --version
KIMI_DIR="$(dirname "$KIMI")"

say "Verifying Kimi authentication using a minimal environment"
CAP_PROMPT='Reply with exactly KIMI_BUILDER_READY and do not call tools.'
if ! /usr/bin/env -i HOME="$HOME" PATH="$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
  "$KIMI" -m kimi-code/k3-256k -p "$CAP_PROMPT" --output-format text 2>&1 | grep -q KIMI_BUILDER_READY; then
  printf '\nKimi needs authorization. Starting the official Kimi login flow.\n'
  /usr/bin/env -i HOME="$HOME" PATH="$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" "$KIMI" login
  /usr/bin/env -i HOME="$HOME" PATH="$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    "$KIMI" -m kimi-code/k3-256k -p "$CAP_PROMPT" --output-format text 2>&1 | grep -q KIMI_BUILDER_READY || fail "Kimi K3 capability probe failed"
fi

cat > "$CONFIG" <<JSON
{
  "builders": {
    "kimi-k3": {
      "executable": "$KIMI",
      "args": ["-m","kimi-code/k3-256k","-p","You are the sole assigned builder for {task_id}. Read {contract_path}. Implement only allowed scope. Do not push, merge, change branches, edit protected paths, read unrelated files, or inspect credentials. Run required validation, commit intended changes on {branch}, and exit. If scope is ambiguous, make no change and exit non-zero.","--output-format","stream-json","--auto"],
      "path_entries": ["$KIMI_DIR","/opt/homebrew/bin","/usr/local/bin","/usr/bin","/bin"]
    }
  },
  "repositories": {
    "amjadthaufeeg/hermes-os-foundation": {
      "remote_url": "git@github.com:amjadthaufeeg/hermes-os-foundation.git",
      "ssh_key": "$FOUNDATION_KEY",
      "clone_root": "$CLONE_ROOT",
      "contract_root_relpath": "docs/tasks",
      "allowed_branch_prefixes": ["feature/","fix/","chore/"],
      "protected_branches": ["main","master","production","prod"]
    },
    "amjadthaufeeg/avoa-quote-engine": {
      "remote_url": "git@github.com:amjadthaufeeg/avoa-quote-engine.git",
      "ssh_key": "$AVOA_KEY",
      "clone_root": "$CLONE_ROOT",
      "contract_root_relpath": "docs/tasks",
      "allowed_branch_prefixes": ["feature/","fix/","chore/"],
      "protected_branches": ["main","master","production","prod"]
    }
  }
}
JSON
chmod 600 "$CONFIG"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array>
<string>$PYTHON</string><string>-m</string><string>deploy.builder_dispatch.mac_worker</string>
<string>--config</string><string>$CONFIG</string><string>--state-dir</string><string>$STATE_ROOT</string><string>--poll</string><string>30</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$SOURCE_ROOT</string>
<key>HOME</key><string>$HOME</string>
<key>PATH</key><string>$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
<key>HERMES_BUILDER_CONTROL_DIR</key><string>$APP_ROOT/hermes-control</string>
<key>HERMES_CONTROL_SSH_KEY</key><string>$CONTROL_KEY</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>10</integer>
<key>StandardOutPath</key><string>$LOG_ROOT/worker.out.log</string>
<key>StandardErrorPath</key><string>$LOG_ROOT/worker.err.log</string>
</dict></plist>
PLIST
chmod 600 "$PLIST"

launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl kickstart -k "gui/$UID/$LABEL"
sleep 2
launchctl print "gui/$UID/$LABEL" >/dev/null || fail "launchd worker did not start"

say "Running fail-closed worker self-test"
/usr/bin/env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" PYTHONPATH="$SOURCE_ROOT" \
HERMES_BUILDER_CONTROL_DIR="$APP_ROOT/hermes-control" HERMES_CONTROL_SSH_KEY="$CONTROL_KEY" \
"$PYTHON" -m deploy.builder_dispatch.mac_worker --config "$CONFIG" --state-dir "$STATE_ROOT" --once

HOST="$(scutil --get ComputerName 2>/dev/null || hostname)"
STATUS="$APP_ROOT/worker-status.json"
cat > "$STATUS" <<JSON
{"status":"READY_V3","host":"$HOST","source_sha":"$PINNED_HERMES_SHA","user":"$(id -un)","admin":false,"isolation":"full-task-clones","kimi_model":"kimi-code/k3-256k","verified_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON
/usr/bin/env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" PYTHONPATH="$SOURCE_ROOT" \
HERMES_BUILDER_CONTROL_DIR="$APP_ROOT/hermes-control" HERMES_CONTROL_SSH_KEY="$CONTROL_KEY" \
"$PYTHON" - "$STATUS" "builders/worker-status/${HOST// /-}.json" <<'PY'
import sys
from deploy.builder_dispatch.mac_transport import commit_and_push
ok,msg,sha=commit_and_push([(sys.argv[2],open(sys.argv[1]).read())],"builder-worker-ready-v3")
if not ok: raise SystemExit(msg)
print("CONTROL_SHA="+str(sha))
PY

printf '\nHERMES_BUILDER_V3_READY\nSOURCE_SHA=%s\nUSER=%s\n' "$PINNED_HERMES_SHA" "$(id -un)"
