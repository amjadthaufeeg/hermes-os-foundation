#!/bin/bash
# schema-validate.sh — Hermes Product OS v3.1
# Validates JSON schemas and YAML records against their schemas.
# Compatible with bash 3.2+ and python3.
#
# Exit codes: 0=PASS, 1=FAIL, 2=ERROR

set -euo pipefail

python3 -c "import yaml, json, jsonschema" 2>/dev/null || {
    echo "SCHEMA_VALIDATE: ERROR — Required packages not installed (pyyaml, jsonschema)"
    exit 2
}

HAS_ERRORS=0
SCHEMA_COUNT=0; SCHEMA_FAILS=0
RECORD_COUNT=0; RECORD_FAILS=0

echo "=== Schema Validation ==="

# Validate a schema and its mapped records
validate_records() {
    local schema_name="$1" schema_file="$2"
    shift 2
    local all_pass=true
    
    for record_pattern in "$@"; do
        for record_file in $record_pattern; do
            [ -f "$record_file" ] || continue
            RECORD_COUNT=$((RECORD_COUNT + 1))
            name=$(basename "$record_file")
            
            if python3 -c "
import yaml, json, jsonschema, sys
with open('$schema_file') as sf:
    schema = json.load(sf)
with open('$record_file') as rf:
    data = yaml.safe_load(rf)
jsonschema.validate(instance=data, schema=schema)
" 2>/dev/null; then
                echo "    PASS: $name"
            else
                echo "    FAIL: $name"
                RECORD_FAILS=$((RECORD_FAILS + 1)); HAS_ERRORS=1
                all_pass=false
            fi
        done
    done
}

# Validate each schema
for schema_file in .hermes/schemas/*.schema.json; do
    [ -f "$schema_file" ] || continue
    SCHEMA_COUNT=$((SCHEMA_COUNT + 1))
    schema_name=$(basename "$schema_file" .schema.json)
    
    if ! python3 -c "import json; json.load(open('$schema_file'))" 2>/dev/null; then
        echo "  FAIL: $schema_name — invalid JSON"
        SCHEMA_FAILS=$((SCHEMA_FAILS + 1)); HAS_ERRORS=1
        continue
    fi
    echo "  PASS: $schema_name"
    
    case "$schema_name" in
        task-contract)
            validate_records "$schema_name" "$schema_file" ".hermes/contracts/TASK-"* ".hermes/contracts/CI.yaml"
            ;;
        decision-record)
            validate_records "$schema_name" "$schema_file" ".hermes/registers/decisions/DEC-"*
            ;;
        *)
            ;;
    esac
done

echo ""
echo "=== Result ==="
echo "  Schemas: ${SCHEMA_COUNT} checked, ${SCHEMA_FAILS} failed"
echo "  Records: ${RECORD_COUNT} checked, ${RECORD_FAILS} failed"
if [ "$HAS_ERRORS" -eq 0 ]; then echo "SCHEMA_VALIDATE: PASS"; exit 0
else echo "SCHEMA_VALIDATE: FAIL"; exit 1; fi