#!/bin/bash
# schema-validate.sh — Hermes Product OS v3.1
# Validates all JSON schemas and YAML records against their schemas.
# Compatible with bash 3.2+ and python3.
# Exit codes: 0=PASS, 1=FAIL (validation errors), 2=ERROR (system)

set -euo pipefail

python3 -c "import yaml, json, jsonschema" 2>/dev/null || {
    echo "SCHEMA_VALIDATE: ERROR — Required packages not installed (pyyaml, jsonschema)"
    exit 2
}

HAS_ERRORS=0
SCHEMA_COUNT=0; SCHEMA_FAILS=0
RECORD_COUNT=0; RECORD_FAILS=0

echo "=== Schema Validation ==="

validate_records() {
    local schema_name="$1" schema_file="$2"
    shift 2
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
            fi
        done
    done
}

for schema_file in .hermes/schemas/*.schema.json; do
    [ -f "$schema_file" ] || continue
    SCHEMA_COUNT=$((SCHEMA_COUNT + 1))
    schema_name=$(basename "$schema_file" .schema.json)
    
    if ! python3 -c "import json; json.load(open('$schema_file'))" 2>/dev/null; then
        echo "  FAIL: $schema_name — invalid JSON"
        SCHEMA_FAILS=$((SCHEMA_FAILS + 1)); HAS_ERRORS=1; continue
    fi
    echo "  PASS: $schema_name"
    
    case "$schema_name" in
        task-contract)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/contracts/TASK-"* ".hermes/contracts/CI.yaml" \
                ".hermes/schema-validation-tests/valid-task-contract.yaml"
            ;;
        ui-contract)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-ui-contract.yaml"
            ;;
        review-report)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-review-report.yaml"
            ;;
        design-review)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-design-review.yaml"
            ;;
        finding-decision)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-finding-decision.yaml"
            ;;
        evidence-package)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-evidence-package.yaml"
            ;;
        task-state-event)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-task-state-event.yaml"
            ;;
        decision-record)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/registers/decisions/DEC-"* \
                ".hermes/schema-validation-tests/valid-decision.yaml"
            ;;
        regression-record)
            validate_records "$schema_name" "$schema_file" \
                ".hermes/schema-validation-tests/valid-regression-record.yaml"
            ;;
    esac
done

echo ""
echo "=== Result ==="
echo "  Schemas: ${SCHEMA_COUNT} checked, ${SCHEMA_FAILS} failed"
echo "  Records: ${RECORD_COUNT} checked, ${RECORD_FAILS} failed"
if [ "$HAS_ERRORS" -eq 0 ]; then echo "SCHEMA_VALIDATE: PASS"; exit 0
else echo "SCHEMA_VALIDATE: FAIL"; exit 1; fi