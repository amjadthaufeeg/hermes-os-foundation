#!/bin/bash
# =============================================================================
# changed-files.sh — HOS-1C Changed-File Report
# =============================================================================
# Generates a YAML report of all files changed between the base ref and HEAD.
#
# Input:  TASK_ID env var (required)
# Reads:  .hermes/contracts/${TASK_ID}.yaml (for task_base_ref)
# Uses:   git diff --name-status against TASK_BASE_REF (from contract) or origin/main
#
# Output: YAML report to stdout with file list, status codes, summary counts.
#         Handles renames: reports previous_path for R statuses.
#
# Exit codes:
#   0 = report generated successfully
#   2 = ERROR — missing contract, invalid YAML, or system error
# =============================================================================

set -euo pipefail

die_error() { echo "CHANGED_FILES: ERROR — $*" >&2; exit 2; }

# ── Escape a string for YAML value (single-quote with '' escaping) ───────────

_yaml_q() {
    local s="$1"
    if [[ "$s" =~ [[:space:]:\"\'{}[\],&*#?|><=!%@\`] ]] || [[ -z "$s" ]]; then
        printf "'%s'" "${s//\'/\'\'}"
    else
        printf '%s' "$s"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

TASK_ID="${TASK_ID:-}"
[[ -z "$TASK_ID" ]] && die_error "TASK_ID environment variable not set"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die_error "Not inside a git repository"
CONTRACT_FILE="${REPO_ROOT}/.hermes/contracts/${TASK_ID}.yaml"
[[ ! -f "$CONTRACT_FILE" ]] && die_error "Contract file not found: ${CONTRACT_FILE}"

# ── Parse task_base_ref ──────────────────────────────────────────────────────

TASK_BASE_REF="$(python3 -c "
import yaml
with open('${CONTRACT_FILE}') as f:
    c = yaml.safe_load(f)
print(c.get('task_base_ref', 'origin/main'))
" 2>/dev/null)" || die_error "Failed to parse task_base_ref — invalid YAML?"

# ── Fallback for base ref ────────────────────────────────────────────────────

if ! git rev-parse --verify "${TASK_BASE_REF}" >/dev/null 2>&1; then
    echo "CHANGED_FILES: WARNING — base ref '${TASK_BASE_REF}' not found, trying origin/main" >&2
    TASK_BASE_REF="origin/main"
    if ! git rev-parse --verify "${TASK_BASE_REF}" >/dev/null 2>&1; then
        echo "CHANGED_FILES: WARNING — origin/main not found, using HEAD~1" >&2
        TASK_BASE_REF="HEAD~1"
    fi
fi

# ── Get diff ─────────────────────────────────────────────────────────────────

DIFF_OUTPUT="$(git diff --name-status "${TASK_BASE_REF}" HEAD 2>/dev/null)" || {
    MERGE_BASE="$(git merge-base "${TASK_BASE_REF}" HEAD 2>/dev/null)" || true
    if [[ -n "${MERGE_BASE:-}" ]]; then
        DIFF_OUTPUT="$(git diff --name-status "${MERGE_BASE}" HEAD 2>/dev/null)" || DIFF_OUTPUT=""
    else
        DIFF_OUTPUT=""
    fi
}

# ── Get commit info and stat ────────────────────────────────────────────────

BASE_SHA="$(git rev-parse --short "${TASK_BASE_REF}" 2>/dev/null || echo "unknown")"
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

INSERTIONS=0
DELETIONS=0
CHANGED_FILES_COUNT=0
STAT_OUTPUT="$(git diff --stat "${TASK_BASE_REF}" HEAD 2>/dev/null)" || true
if [[ -n "${STAT_OUTPUT:-}" ]]; then
    LAST_LINE="$(echo "$STAT_OUTPUT" | tail -1)"
    if [[ "$LAST_LINE" =~ ([0-9]+)\ files?\ changed ]]; then
        CHANGED_FILES_COUNT="${BASH_REMATCH[1]}"
    fi
    if [[ "$LAST_LINE" =~ ([0-9]+)\ insertions?\(\+\) ]]; then
        INSERTIONS="${BASH_REMATCH[1]}"
    fi
    if [[ "$LAST_LINE" =~ ([0-9]+)\ deletions?\(-\) ]]; then
        DELETIONS="${BASH_REMATCH[1]}"
    fi
fi

# ── Count by status and build file entries ───────────────────────────────────

declare -A STATUS_COUNT=( ["A"]=0 ["M"]=0 ["D"]=0 ["R"]=0 ["C"]=0 ["UNKNOWN"]=0 )
FILES_ENTRIES=()
TOTAL=0

if [[ -n "${DIFF_OUTPUT:-}" ]]; then
    while IFS=$'\t' read -r status path1 path2 rest; do
        [[ -z "$status" ]] && continue
        status="${status%$'\r'}"
        path1="${path1%$'\r'}"
        path2="${path2%$'\r'}"

        case "$status" in
            A)
                FILES_ENTRIES+=("  - status: added")
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path1")"))
                STATUS_COUNT["A"]=$((STATUS_COUNT["A"] + 1))
                ;;
            M)
                FILES_ENTRIES+=("  - status: modified")
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path1")"))
                STATUS_COUNT["M"]=$((STATUS_COUNT["M"] + 1))
                ;;
            D)
                FILES_ENTRIES+=("  - status: deleted")
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path1")"))
                STATUS_COUNT["D"]=$((STATUS_COUNT["D"] + 1))
                ;;
            R*)
                FILES_ENTRIES+=("  - status: renamed")
                FILES_ENTRIES+=($(printf '    previous_path: %s' "$(_yaml_q "$path1")"))
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path2")"))
                STATUS_COUNT["R"]=$((STATUS_COUNT["R"] + 1))
                ;;
            C*)
                FILES_ENTRIES+=("  - status: copied")
                FILES_ENTRIES+=($(printf '    previous_path: %s' "$(_yaml_q "$path1")"))
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path2")"))
                STATUS_COUNT["C"]=$((STATUS_COUNT["C"] + 1))
                ;;
            *)
                FILES_ENTRIES+=("  - status: unknown")
                FILES_ENTRIES+=($(printf '    raw_status: %s' "$(_yaml_q "$status")"))
                FILES_ENTRIES+=($(printf '    path: %s' "$(_yaml_q "$path1")"))
                STATUS_COUNT["UNKNOWN"]=$((STATUS_COUNT["UNKNOWN"] + 1))
                ;;
        esac
        TOTAL=$((TOTAL + 1))
    done <<< "$DIFF_OUTPUT"
fi

# ── Generate YAML Report ─────────────────────────────────────────────────────

cat <<YAML
# ──────────────────────────────────────────────────────────
# Hermes OS v3.1 — Changed-File Report
# Generated: ${TIMESTAMP}
# Task ID:   ${TASK_ID}
# ──────────────────────────────────────────────────────────
changed_files_report:
  task_id: "$(_yaml_q "$TASK_ID")"
  timestamp: "$TIMESTAMP"
  diff_info:
    base_ref: "$(_yaml_q "$TASK_BASE_REF")"
    base_sha: "$BASE_SHA"
    head_sha: "$HEAD_SHA"
  summary:
    total_files: ${TOTAL}
    added: ${STATUS_COUNT["A"]}
    modified: ${STATUS_COUNT["M"]}
    deleted: ${STATUS_COUNT["D"]}
    renamed: ${STATUS_COUNT["R"]}
    copied: ${STATUS_COUNT["C"]}
    other: ${STATUS_COUNT["UNKNOWN"]}
    insertions: ${INSERTIONS:-0}
    deletions: ${DELETIONS:-0}
  files:
YAML

if [[ $TOTAL -gt 0 ]]; then
    printf '%s\n' "${FILES_ENTRIES[@]}"
else
    echo "    []"
fi

exit 0