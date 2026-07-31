#!/bin/bash
# scope-check.sh — Hermes Product OS v3.1
# Compares git diff files against task contract allowed_files/allowed_folders.
# Compatible with bash 3.2+ and python3.
#
# Exit codes: 0=PASS, 1=FAIL (violations), 2=ERROR

set -euo pipefail

TASK_ID="${TASK_ID:-}"
if [ -z "$TASK_ID" ]; then
    echo "SCOPE_CHECK: ERROR — TASK_ID not set"
    exit 2
fi

CONTRACT=".hermes/contracts/${TASK_ID}.yaml"
if [ ! -f "$CONTRACT" ]; then
    echo "SCOPE_CHECK: ERROR — Contract not found: $CONTRACT"
    exit 2
fi

export CONTRACT_FILE="$CONTRACT"

python3 << 'PYEOF'
import subprocess, sys, yaml, os, re, fnmatch

task_id = os.environ.get("TASK_ID", "UNKNOWN")
contract_file = os.environ.get("CONTRACT_FILE")

if not contract_file or not os.path.exists(contract_file):
    print(f"SCOPE_CHECK: ERROR — Contract file not found")
    sys.exit(2)

try:
    with open(contract_file) as f:
        contract = yaml.safe_load(f)
except Exception as e:
    print(f"SCOPE_CHECK: ERROR — Invalid contract YAML: {e}")
    sys.exit(2)

base_ref = contract.get("baseline_commit", "origin/main")
allowed_files = contract.get("allowed_files", [])
allowed_folders = contract.get("allowed_folders", [])

# Get git diff
result = subprocess.run(
    ["git", "diff", "--name-status", f"{base_ref}..HEAD"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"SCOPE_CHECK: ERROR — git diff failed: {result.stderr}")
    sys.exit(2)

lines = result.stdout.strip().split("\n")
if not lines or (len(lines) == 1 and not lines[0].strip()):
    print(f"SCOPE_CHECK: PASS")
    print(f"Task: {task_id}")
    print("No changed files detected.")
    sys.exit(0)

def is_allowed(path):
    """Check if a path matches allowed_files or allowed_folders."""
    for pattern in allowed_files:
        if fnmatch.fnmatch(path, pattern):
            return True
    for folder in allowed_folders:
        folder_clean = folder.rstrip("/")
        if path.startswith(folder_clean + "/") or path == folder_clean:
            return True
    return False

violations = []
for line in lines:
    if not line.strip():
        continue
    parts = line.split("\t")
    status = parts[0]
    
    paths_to_check = []
    display = ""
    
    if status.startswith("R"):
        # Renamed: check BOTH source and destination
        old_path = parts[1]
        new_path = parts[2]
        paths_to_check = [old_path, new_path]
        display = f"{status}  {old_path} → {new_path}"
    elif status in ("A", "M", "D"):
        path = parts[1]
        paths_to_check = [path]
        display = f"{status}  {path}"
    else:
        paths_to_check = [parts[1]] if len(parts) > 1 else []
        display = f"{status}  {parts[1] if len(parts) > 1 else '?'}"
    
    all_ok = all(is_allowed(p) for p in paths_to_check)
    if not all_ok:
        violations.append(f"  {display}  (not in allowed_files or allowed_folders)")

if violations:
    print("SCOPE_CHECK: FAIL")
    print(f"Task: {task_id}")
    print(f"Base ref: {base_ref}")
    print("Violations:")
    for v in violations:
        print(v)
    sys.exit(1)

print("SCOPE_CHECK: PASS")
print(f"Task: {task_id}")
print(f"All {len(lines)} changed file(s) within allowed scope.")
sys.exit(0)
PYEOF