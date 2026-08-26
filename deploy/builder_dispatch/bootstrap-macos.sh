#!/usr/bin/env bash
set -euo pipefail

PINNED_HERMES_SHA="${PINNED_HERMES_SHA:-}"
KIMI_INSTALLER_PATH="${KIMI_INSTALLER_PATH:-}"
FOUNDATION_REPO="${HERMES_FOUNDATION_REPO:-$HOME/projects/hermes-os-foundation}"
AVOA_REPO="${AVOA_REPO:-$HOME/projects/avoa-quote-engine}"
APP_ROOT="$HOME/Library/Application Support/HermesBuilder"
SOURCE_ROOT="$APP_ROOT/source"
STATE_ROOT="$APP_ROOT/state"
LOG_ROOT="$APP_ROOT/logs"
CONFIG="$APP_ROOT/config.json"
PLIST="$HOME/Library/LaunchAgents/ai.hermes.builder-worker.plist"
LABEL="ai.hermes.builder-worker"

say() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || fail "This bootstrap is for macOS only"
[[ "$PINNED_HERMES_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "PINNED_HERMES_SHA must be an immutable 40-character commit SHA"
command -v git >/dev/null || fail "Git is required"
command -v shasum >/dev/null || fail "shasum is required"

mkdir -p "$APP_ROOT" "$STATE_ROOT" "$LOG_ROOT" "$HOME/Library/LaunchAgents" "$HOME/avoa-worktrees"
chmod 700 "$APP_ROOT" "$STATE_ROOT" "$LOG_ROOT"

if [[ ! -d "$FOUNDATION_REPO/.git" ]]; then
  candidate="$(find "$HOME/projects" -maxdepth 2 -type d -name hermes-os-foundation -print -quit 2>/dev/null || true)"
  [[ -n "$candidate" && -d "$candidate/.git" ]] || fail "Cannot locate hermes-os-foundation under ~/projects"
  FOUNDATION_REPO="$candidate"
fi

say "Refreshing reviewed builder source at immutable SHA $PINNED_HERMES_SHA"
git -C "$FOUNDATION_REPO" fetch origin "$PINNED_HERMES_SHA"
git -C "$FOUNDATION_REPO" cat-file -e "$PINNED_HERMES_SHA^{commit}" || fail "Pinned Hermes commit unavailable"
if [[ -e "$SOURCE_ROOT" ]]; then
  git -C "$FOUNDATION_REPO" worktree remove --force "$SOURCE_ROOT" >/dev/null 2>&1 || rm -rf "$SOURCE_ROOT"
fi
git -C "$FOUNDATION_REPO" worktree add --detach "$SOURCE_ROOT" "$PINNED_HERMES_SHA"
SOURCE_SHA="$(git -C "$SOURCE_ROOT" rev-parse HEAD)"
[[ "$SOURCE_SHA" == "$PINNED_HERMES_SHA" ]] || fail "Hermes source SHA mismatch"

say "Locating Python"
PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || fail "python3 is required"
"$PYTHON" - <<'PY'
import sys
assert sys.version_info >= (3, 9), f"Python 3.9+ required, got {sys.version}"
PY

say "Ensuring Kimi Code CLI is installed"
KIMI="$(command -v kimi || true)"
if [[ -z "$KIMI" ]]; then
  [[ -n "$KIMI_INSTALLER_PATH" ]] || fail "Kimi is not installed and no verified local installer was supplied"
  [[ -f "$KIMI_INSTALLER_PATH" ]] || fail "Verified Kimi installer file is missing"
  /bin/bash "$KIMI_INSTALLER_PATH"
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
  KIMI="$(command -v kimi || true)"
fi
[[ -n "$KIMI" && -x "$KIMI" ]] || fail "Kimi installation did not produce an executable"
"$KIMI" --version

say "Verifying Kimi authentication and K3 access"
CAP_PROMPT='Reply with exactly KIMI_BUILDER_READY and do not call tools.'
if ! "$KIMI" -m kimi-code/k3-256k -p "$CAP_PROMPT" --output-format text --auto 2>&1 | grep -q 'KIMI_BUILDER_READY'; then
  printf '\nKimi requires account authorization. Starting the official OAuth device-code flow.\n'
  "$KIMI" login
  "$KIMI" -m kimi-code/k3-256k -p "$CAP_PROMPT" --output-format text --auto 2>&1 | grep -q 'KIMI_BUILDER_READY' || fail "Kimi K3 capability probe failed after login"
fi

say "Creating trusted builder configuration"
KIMI_DIR="$(dirname "$KIMI")"
cat > "$CONFIG" <<JSON
{
  "builders": {
    "kimi-k3": {
      "executable": "$KIMI",
      "args": [
        "-m", "kimi-code/k3-256k",
        "-p", "You are the sole assigned Kimi K3 builder for {task_id}. Read the approved task contract at {contract_path}. Inspect the current repository and baseline {baseline_commit}. Implement only the contract's allowed scope, preserve all protected areas, run the required validations, then git add and commit all intended changes on the current branch {branch}. Do not push, merge, change branches, or modify unrelated files. If a stop condition occurs, make no broader change and exit non-zero. End with a concise builder report.",
        "--output-format", "stream-json",
        "--auto"
      ],
      "path_entries": ["$KIMI_DIR", "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    }
  },
  "repositories": {
    "amjadthaufeeg/hermes-os-foundation": {
      "source_repository": "$FOUNDATION_REPO",
      "worktree_root": "$HOME/hermes-worktrees",
      "contract_root_relpath": "docs/tasks",
      "allowed_branch_prefixes": ["feature/", "fix/", "chore/"]
    },
    "amjadthaufeeg/avoa-quote-engine": {
      "source_repository": "$AVOA_REPO",
      "worktree_root": "$HOME/avoa-worktrees",
      "contract_root_relpath": "docs/tasks",
      "allowed_branch_prefixes": ["feature/", "fix/", "chore/"]
    }
  }
}
JSON
chmod 600 "$CONFIG"

"$PYTHON" - "$CONFIG" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); data=json.loads(p.read_text())
for name,cfg in list(data.get('repositories',{}).items()):
    if not (pathlib.Path(cfg['source_repository']).expanduser()/'.git').exists():
        del data['repositories'][name]
p.write_text(json.dumps(data,indent=2)+"\n")
PY
chmod 600 "$CONFIG"

say "Installing launchd worker"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>-m</string><string>deploy.builder_dispatch.mac_worker</string>
    <string>--config</string><string>$CONFIG</string>
    <string>--state-dir</string><string>$STATE_ROOT</string>
    <string>--poll</string><string>30</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key><string>$SOURCE_ROOT</string>
    <key>PATH</key><string>$KIMI_DIR:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HERMES_BUILDER_CONTROL_DIR</key><string>$APP_ROOT/hermes-control</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOG_ROOT/worker.out.log</string>
  <key>StandardErrorPath</key><string>$LOG_ROOT/worker.err.log</string>
</dict>
</plist>
PLIST
chmod 600 "$PLIST"

launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl kickstart -k "gui/$UID/$LABEL"
sleep 2
launchctl print "gui/$UID/$LABEL" >/dev/null || fail "launchd worker did not start"

say "Running worker self-test"
PYTHONPATH="$SOURCE_ROOT" HERMES_BUILDER_CONTROL_DIR="$APP_ROOT/hermes-control" \
  "$PYTHON" -m deploy.builder_dispatch.mac_worker --config "$CONFIG" --state-dir "$STATE_ROOT" --once

say "Publishing worker readiness"
HOST="$(scutil --get ComputerName 2>/dev/null || hostname)"
STATUS_PATH="builders/worker-status/${HOST// /-}.json"
STATUS_JSON="$APP_ROOT/worker-status.json"
cat > "$STATUS_JSON" <<JSON
{
  "status": "READY",
  "processor": "$LABEL",
  "host": "$HOST",
  "source_sha": "$SOURCE_SHA",
  "kimi_executable": "$KIMI",
  "kimi_model": "kimi-code/k3-256k",
  "foundation_repo": "$FOUNDATION_REPO",
  "avoa_repo_present": $([[ -d "$AVOA_REPO/.git" ]] && echo true || echo false),
  "verified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
PYTHONPATH="$SOURCE_ROOT" HERMES_BUILDER_CONTROL_DIR="$APP_ROOT/hermes-control" \
  "$PYTHON" - "$STATUS_JSON" "$STATUS_PATH" <<'PY'
import sys
from deploy.builder_dispatch.mac_transport import commit_and_push
content=open(sys.argv[1]).read()
ok,msg,sha=commit_and_push([(sys.argv[2],content)],"builder-worker-ready: macOS Kimi K3")
if not ok: raise SystemExit(msg)
print("CONTROL_SHA="+str(sha))
PY

printf '\nBUILDER_WORKER_READY\nSOURCE_SHA=%s\nKIMI=%s\nPLIST=%s\n' "$SOURCE_SHA" "$KIMI" "$PLIST"
