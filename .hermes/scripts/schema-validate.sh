#!/bin/bash
# schema-validate.sh — Hermes Product OS v3.1
# Validates JSON schemas, YAML policies, and validates records against their JSON schemas.
#
# Exit codes:
#   0 = All valid
#   1 = Validation failures found
#   2 = Missing dependencies or system error

set -euo pipefail

HAS_ERRORS=0

# Require python3
if ! command -v python3 &>/dev/null; then
    echo "SCHEMA_VALIDATE: ERROR — python3 not found"
    exit 2
fi

python3 -c "import yaml, json, jsonschema" 2>/dev/null || {
    echo "SCHEMA_VALIDATE: ERROR — Required packages not installed (pyyaml, jsonschema)"
    exit 2
}

echo "=== Schema Validation ==="

# ── Validate JSON schemas themselves ───────────────────────────
SCHEMA_DIR=".hermes/schemas"
SCHEMA_COUNT=0; SCHEMA_FAILS=0
if [ -d "$SCHEMA_DIR" ]; then
    for schema in "$SCHEMA_DIR"/*.json; do
        [ -f "$schema" ] || continue
        SCHEMA_COUNT=$((SCHEMA_COUNT + 1))
        if python3 -c "
import json
with open('$schema') as f:
    try:
        json.load(f)
        print('PASS')
    except json.JSONDecodeError as e:
        print(f'FAIL: {e}')
        exit(1)
" 2>/dev/null; then :; else SCHEMA_FAILS=$((SCHEMA_FAILS + 1)); HAS_ERRORS=1; fi
    done
    echo "  Schemas: ${SCHEMA_COUNT} checked, ${SCHEMA_FAILS} failed"
fi

# ── Validate YAML policies parse ───────────────────────────────
POLICY_DIR=".hermes/policies"
POLICY_COUNT=0; POLICY_FAILS=0
if [ -d "$POLICY_DIR" ]; then
    for policy in "$POLICY_DIR"/*.yaml; do
        [ -f "$policy" ] || continue
        POLICY_COUNT=$((POLICY_COUNT + 1))
        name=$(basename "$policy")
        if python3 -c "
import yaml
with open('$policy') as f:
    yaml.safe_load(f)
print('PASS')
" 2>/dev/null; then :; else POLICY_FAILS=$((POLICY_FAILS + 1)); HAS_ERRORS=1; fi
    done
    echo "  Policies: ${POLICY_COUNT} checked, ${POLICY_FAILS} failed"
fi

# ── Validate decision records against decision-record.schema.json ──
DECISION_DIR=".hermes/registers/decisions"
DECISION_SCHEMA=".hermes/schemas/decision-record.schema.json"
DEC_COUNT=0; DEC_FAILS=0
if [ -d "$DECISION_DIR" ] && [ -f "$DECISION_SCHEMA" ]; then
    for decision in "$DECISION_DIR"/*.yaml; do
        [ -f "$decision" ] || continue
        DEC_COUNT=$((DEC_COUNT + 1))
        name=$(basename "$decision")
        if python3 -c "
import yaml, json, jsonschema, sys
with open('$DECISION_SCHEMA') as sf:
    schema = json.load(sf)
with open('$decision') as df:
    try:
        data = yaml.safe_load(df)
    except yaml.YAMLError as e:
        print(f'  FAIL: $name — YAML parse error: {e}')
        sys.exit(1)
try:
    jsonschema.validate(instance=data, schema=schema)
    print(f'  PASS: $name ({data.get(\"decision_id\",\"?\")}: {data.get(\"status\",\"?\")})')
except jsonschema.ValidationError as e:
    path = '.'.join(str(p) for p in e.absolute_path) if e.absolute_path else '(root)'
    print(f'  FAIL: $name — {e.message} at {path}')
    sys.exit(1)
" 2>&1; then :; else DEC_FAILS=$((DEC_FAILS + 1)); HAS_ERRORS=1; fi
    done
    echo "  Decision records: ${DEC_COUNT} checked, ${DEC_FAILS} failed (validated against decision-record.schema.json)"
fi

# ── Summary ────────────────────────────────────────────────────
echo ""
echo "=== Result ==="
if [ "$HAS_ERRORS" -eq 0 ]; then
    echo "SCHEMA_VALIDATE: PASS"
    exit 0
else
    echo "SCHEMA_VALIDATE: FAIL"
    exit 1
fi