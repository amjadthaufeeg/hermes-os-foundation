#!/bin/bash
# changed-files.sh — Hermes Product OS v3.1
# Generates structured YAML report of changed files.
# Compatible with bash 3.2+ and python3.
#
# Exit codes: 0=success, 2=error

set -euo pipefail

TASK_ID="${TASK_ID:-}"
if [ -z "$TASK_ID" ]; then
    echo "CHANGED_FILES: ERROR — TASK_ID not set"
    exit 2
fi

CONTRACT=".hermes/contracts/${TASK_ID}.yaml"
TASK_BASE_REF="origin/main"

if [ -f "$CONTRACT" ]; then
    TASK_BASE_REF=$(python3 -c "
import yaml
with open('$CONTRACT') as f:
    c = yaml.safe_load(f)
print(c.get('baseline_commit', 'origin/main'))
" 2>/dev/null || echo "origin/main")
fi

export TASK_BASE_REF

python3 << 'PYEOF'
import subprocess, sys, yaml, os

task_id = os.environ.get("TASK_ID", "UNKNOWN")
base_ref = os.environ.get("TASK_BASE_REF", "origin/main")

result = subprocess.run(
    ["git", "diff", "--name-status", base_ref + "..HEAD"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print(f"CHANGED_FILES: ERROR — git diff failed: {result.stderr}")
    sys.exit(2)

lines = result.stdout.strip().split("\n")
files = []
counts = {"A": 0, "M": 0, "D": 0, "R": 0}

for line in lines:
    if not line.strip():
        continue
    parts = line.split("\t")
    status = parts[0]
    
    if status.startswith("R"):
        entry = {
            "status": status,
            "previous_path": parts[1],
            "path": parts[2]
        }
        counts["R"] += 1
    elif status in ("A", "M", "D"):
        entry = {
            "status": status,
            "path": parts[1]
        }
        counts[status] = counts.get(status, 0) + 1
    else:
        # Unknown status — fail closed
        print(f"CHANGED_FILES: ERROR — unknown git status '{status}'", file=sys.stderr)
        sys.exit(2)
    
    files.append(entry)

total = sum(counts.values())

output = {
    "task_id": task_id,
    "base_ref": base_ref,
    "head_ref": "HEAD",
    "files": files,
    "summary": {
        "added": counts.get("A", 0),
        "modified": counts.get("M", 0),
        "deleted": counts.get("D", 0),
        "renamed": counts.get("R", 0),
        "total": total
    }
}

yaml.dump(output, sys.stdout, default_flow_style=False, sort_keys=False, allow_unicode=True)
PYEOF