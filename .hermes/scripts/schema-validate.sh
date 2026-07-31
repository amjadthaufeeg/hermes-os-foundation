#!/bin/bash
# schema-validate.sh — Hermes Product OS v3.1
# Validates all JSON schemas and YAML policy/decision/template files.
#
# Exit codes:
#   0 = All valid
#   1 = Validation failures found
#   2 = Missing dependencies or system error

set -euo pipefail

HAS_ERRORS=0
HAS_DEPS=true

# Check python3 and dependencies
if ! command -v python3 &>/dev/null; then
    echo "SCHEMA_VALIDATE: ERROR — python3 not found"
    exit 2
fi

python3 -c "import yaml, json" 2>/dev/null || {
    echo "SCHEMA_VALIDATE: ERROR — Required Python packages not installed (pyyaml)"
    exit 2
}

echo "=== Schema Validation ==="
echo ""

# ── Validate JSON schemas ──────────────────────────────────────
SCHEMA_DIR=".hermes/schemas"
if [ -d "$SCHEMA_DIR" ]; then
    SCHEMA_COUNT=0
    SCHEMA_FAILS=0
    for schema in "$SCHEMA_DIR"/*.json; do
        [ -f "$schema" ] || continue
        SCHEMA_COUNT=$((SCHEMA_COUNT + 1))
        
        if python3 -c "
import json, sys
with open('$schema') as f:
    try:
        data = json.load(f)
        # Valid JSON = can be loaded
        print(f'  PASS: $(basename $schema)')
    except json.JSONDecodeError as e:
        print(f'  FAIL: $(basename $schema) — {e}', file=sys.stderr)
        sys.exit(1)
" 2>/dev/null; then
            :
        else
            SCHEMA_FAILS=$((SCHEMA_FAILS + 1))
            HAS_ERRORS=1
        fi
    done
    echo "  Schemas: ${SCHEMA_COUNT} checked, ${SCHEMA_FAILS} failed"
else
    echo "  Schemas: directory not found ($SCHEMA_DIR)"
fi
echo ""

# ── Validate YAML policies ─────────────────────────────────────
POLICY_DIR=".hermes/policies"
if [ -d "$POLICY_DIR" ]; then
    POLICY_COUNT=0
    POLICY_FAILS=0
    for policy in "$POLICY_DIR"/*.yaml; do
        [ -f "$policy" ] || continue
        POLICY_COUNT=$((POLICY_COUNT + 1))
        name=$(basename "$policy")
        
        if python3 -c "
import yaml, sys
try:
    with open('$policy') as f:
        yaml.safe_load(f)
    print(f'  PASS: $name')
except yaml.YAMLError as e:
    print(f'  FAIL: $name — {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            :
        else
            POLICY_FAILS=$((POLICY_FAILS + 1))
            HAS_ERRORS=1
        fi
    done
    echo "  Policies: ${POLICY_COUNT} checked, ${POLICY_FAILS} failed"
else
    echo "  Policies: directory not found ($POLICY_DIR)"
fi
echo ""

# ── Validate decision records ──────────────────────────────────
DECISION_DIR=".hermes/registers/decisions"
if [ -d "$DECISION_DIR" ]; then
    DEC_COUNT=0
    DEC_FAILS=0
    for decision in "$DECISION_DIR"/*.yaml; do
        [ -f "$decision" ] || continue
        DEC_COUNT=$((DEC_COUNT + 1))
        name=$(basename "$decision")
        
        if python3 -c "
import yaml, sys
try:
    with open('$decision') as f:
        data = yaml.safe_load(f)
    # Check required fields
    required = ['decision_id', 'title', 'status', 'decision', 'reason']
    missing = [f for f in required if f not in data]
    if missing:
        print(f'  FAIL: $name — missing fields: {missing}', file=sys.stderr)
        sys.exit(1)
    print(f'  PASS: $name ({data.get(\"decision_id\", \"?\")}: {data.get(\"status\", \"?\")})')
except yaml.YAMLError as e:
    print(f'  FAIL: $name — {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            :
        else
            DEC_FAILS=$((DEC_FAILS + 1))
            HAS_ERRORS=1
        fi
    done
    echo "  Decision records: ${DEC_COUNT} checked, ${DEC_FAILS} failed"
else
    echo "  Decision records: directory not found ($DECISION_DIR)"
fi
echo ""

# ── Summary ────────────────────────────────────────────────────
echo "=== Result ==="
if [ "$HAS_ERRORS" -eq 0 ]; then
    echo "SCHEMA_VALIDATE: PASS"
    exit 0
else
    echo "SCHEMA_VALIDATE: FAIL"
    exit 1
fi