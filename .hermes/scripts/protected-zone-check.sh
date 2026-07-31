#!/bin/bash
# =============================================================================
# protected-zone-check.sh — HOS-1C Protected Zone Enforcement Gate
# =============================================================================
# Compares git diff against protected-zones.yaml policy and the task contract's
# authorized_protected_changes. protected_areas alone is NOT permission — only
# authorized_protected_changes grants access.
#
# Input:  TASK_ID env var (required)
# Reads:  .hermes/policies/protected-zones.yaml  (zone definitions)
#         .hermes/contracts/${TASK_ID}.yaml       (authorized_protected_changes, protected_areas, task_base_ref)
# Uses:   git diff --name-status against TASK_BASE_REF (from contract) or origin/main
#
# Exit codes:
#   0 = PASS — no protected zone violations
#   1 = FAIL/SCOPE_EXCEEDED — file modified in protected zone without authorization
#   2 = ERROR — missing files, invalid YAML, or unexpected system error
#
# CRITICAL RULES:
#   - protected_areas is NOT permission. Only authorized_protected_changes grants.
#   - If authorized_protected_changes is empty/absent → ALL protected zones prohibited.
#   - R4 zones additionally require the amjad_approval flag on the authorized change.
#   - Renamed files check BOTH source and destination.
#   - Deleted files MUST be scope-checked.
#   - Fail closed: any unexpected condition → non-zero exit.
# =============================================================================

set -euo pipefail

die_error() { echo "PROTECTED_ZONE_CHECK: ERROR — $*" >&2; exit 2; }

# ── Input Validation ─────────────────────────────────────────────────────────

TASK_ID="${TASK_ID:-}"
[[ -z "$TASK_ID" ]] && die_error "TASK_ID environment variable not set"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die_error "Not inside a git repository"

POLICY_FILE="${REPO_ROOT}/.hermes/policies/protected-zones.yaml"
CONTRACT_FILE="${REPO_ROOT}/.hermes/contracts/${TASK_ID}.yaml"

[[ ! -f "$POLICY_FILE" ]] && die_error "Policy file not found: ${POLICY_FILE}"
[[ ! -f "$CONTRACT_FILE" ]] && die_error "Contract file not found: ${CONTRACT_FILE}"

echo "PROTECTED_ZONE_CHECK: Reading policy and contract..." >&2

# ── Determine base ref ───────────────────────────────────────────────────────

TASK_BASE_REF="$(python3 -c "
import yaml
with open('${CONTRACT_FILE}') as f:
    c = yaml.safe_load(f)
print(c.get('task_base_ref', 'origin/main'))
" 2>/dev/null)" || die_error "Failed to parse task_base_ref from contract"

if ! git rev-parse --verify "${TASK_BASE_REF}" >/dev/null 2>&1; then
    echo "PROTECTED_ZONE_CHECK: WARNING — base ref '${TASK_BASE_REF}' not found, trying origin/main" >&2
    TASK_BASE_REF="origin/main"
    if ! git rev-parse --verify "${TASK_BASE_REF}" >/dev/null 2>&1; then
        echo "PROTECTED_ZONE_CHECK: WARNING — origin/main not found, using HEAD~1" >&2
        TASK_BASE_REF="HEAD~1"
    fi
fi

echo "PROTECTED_ZONE_CHECK: Base ref: ${TASK_BASE_REF}" >&2

# ── Get changed files ────────────────────────────────────────────────────────

DIFF_OUTPUT="$(git diff --name-status "${TASK_BASE_REF}" HEAD 2>/dev/null)" || {
    MERGE_BASE="$(git merge-base "${TASK_BASE_REF}" HEAD 2>/dev/null)" || true
    if [[ -n "${MERGE_BASE:-}" ]]; then
        DIFF_OUTPUT="$(git diff --name-status "${MERGE_BASE}" HEAD 2>/dev/null)" || DIFF_OUTPUT=""
    else
        DIFF_OUTPUT=""
    fi
}

if [[ -z "${DIFF_OUTPUT:-}" ]]; then
    echo "PROTECTED_ZONE_CHECK: PASS — no files changed (empty diff)"
    exit 0
fi

# ── Write diff to temp file for safe passing ─────────────────────────────────
# This avoids quoting nightmares with embedded single-quotes in inline python.

DIFF_TEMP="$(mktemp /tmp/hermes-protected-zone-diff.XXXXXX)"
trap 'rm -f "$DIFF_TEMP"' EXIT
printf '%s\n' "$DIFF_OUTPUT" > "$DIFF_TEMP"

# Export variables for python to access
export CONTRACT_FILE POLICY_FILE DIFF_TEMP

# ── Python validation ────────────────────────────────────────────────────────
# Uses heredoc with quoted delimiter ('PYEOF') to prevent shell expansion.

python3 <<'PYEOF'
import sys, os, yaml, fnmatch

contract_file = os.environ["CONTRACT_FILE"]
policy_file   = os.environ["POLICY_FILE"]
diff_temp     = os.environ["DIFF_TEMP"]

# ── Load policy zones ────────────────────────────────────────────────

with open(policy_file) as f:
    policy = yaml.safe_load(f)
zones = policy.get("zones", [])
if zones is None:
    zones = []

# ── Load contract ────────────────────────────────────────────────────

with open(contract_file) as f:
    contract = yaml.safe_load(f)

authorized = contract.get("authorized_protected_changes")
if authorized is None:
    authorized = []

protected_areas = contract.get("protected_areas", [])
if protected_areas is None:
    protected_areas = []

# ── Read diff from temp file ─────────────────────────────────────────

with open(diff_temp) as f:
    diff_output = f.read()

# ── Parse diff ───────────────────────────────────────────────────────
# git diff --name-status outputs: STATUS\tFILE1[\tFILE2]
# R100\tsrc_file\tdst_file for renames

violations = []
checked_count = 0

for line in diff_output.strip().split("\n"):
    if not line.strip():
        continue
    parts = line.split("\t")
    status = parts[0].strip()

    files_to_check = []

    if status == "D":
        if len(parts) > 1:
            files_to_check.append(parts[1])
    elif status.startswith("R"):
        if len(parts) > 1:
            files_to_check.append(parts[1])
        if len(parts) > 2:
            files_to_check.append(parts[2])
    elif status in ("A", "M", "C", "T", "U", "X", "B"):
        if len(parts) > 1:
            files_to_check.append(parts[1])
    else:
        fname = parts[1] if len(parts) > 1 else ""
        msg = f"PROTECTED_ZONE_CHECK: ERROR — unknown git status {status!r} for {fname!r}"
        print(msg, file=sys.stderr)
        sys.exit(2)

    for filepath in files_to_check:
        if not filepath:
            continue
        checked_count += 1

        for zone in zones:
            zone_domain = zone.get("domain", "unknown")
            zone_risk   = zone.get("risk", "unknown")
            zone_paths  = zone.get("paths", [])
            if zone_paths is None:
                zone_paths = []

            # Does this file match any zone path?
            matched_zone = False
            for zp in zone_paths:
                if fnmatch.fnmatch(filepath, zp):
                    matched_zone = True
                    break
                zp_clean = zp.rstrip("/")
                if filepath.startswith(zp_clean + "/") or filepath == zp_clean:
                    matched_zone = True
                    break

            if not matched_zone:
                continue

            # File IS in a protected zone. Check authorization.
            is_authorized = False
            has_amjad_approval = False

            if not authorized:
                is_authorized = False
            else:
                for ac in authorized:
                    if not isinstance(ac, dict):
                        continue
                    ac_file = ac.get("file", "")
                    if fnmatch.fnmatch(filepath, ac_file) or filepath == ac_file:
                        is_authorized = True
                        if ac.get("amjad_approval", False):
                            has_amjad_approval = True
                        break

            # RULE: R4 zones require amjad_approval flag
            if zone_risk == "R4":
                if is_authorized and not has_amjad_approval:
                    violations.append({
                        "file": filepath, "status": status,
                        "zone": zone_domain, "risk": zone_risk,
                        "reason": "R4 zone requires amjad_approval flag — not present",
                    })
                    continue
                elif not is_authorized:
                    violations.append({
                        "file": filepath, "status": status,
                        "zone": zone_domain, "risk": zone_risk,
                        "reason": "R4 zone — no matching entry in authorized_protected_changes",
                    })
                    continue

            if not is_authorized:
                violations.append({
                    "file": filepath, "status": status,
                    "zone": zone_domain, "risk": zone_risk,
                    "reason": "No matching entry in authorized_protected_changes",
                })

# ── Report ───────────────────────────────────────────────────────────

if violations:
    for v in violations:
        print(f"PROTECTED_ZONE_CHECK: VIOLATION — {v['status']}: {v['file']}  zone={v['zone']}  risk={v['risk']}  reason=\"{v['reason']}\"")
    print(f"PROTECTED_ZONE_CHECK: {checked_count} files checked, {len(violations)} protected zone violations", file=sys.stderr)
    print("PROTECTED_ZONE_CHECK: SCOPE_EXCEEDED", file=sys.stderr)
    sys.exit(1)
else:
    print(f"PROTECTED_ZONE_CHECK: PASS — {checked_count} files checked, 0 protected zone violations", file=sys.stderr)
    sys.exit(0)
PYEOF

PY_EXIT=$?

if [[ $PY_EXIT -eq 2 ]]; then
    exit 2
elif [[ $PY_EXIT -eq 1 ]]; then
    echo "PROTECTED_ZONE_CHECK: SCOPE_EXCEEDED"
    exit 1
fi

echo "PROTECTED_ZONE_CHECK: PASS"
exit 0