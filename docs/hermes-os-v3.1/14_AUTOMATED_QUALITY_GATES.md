# 14 — Automated Quality Gates

**Status:** SPECIFICATION
**Version:** 3.1
**Part of:** Hermes Engineering OS v3.1 Implementation Package

---

## Purpose

Automated quality gates are the non-negotiable technical enforcement layer. No task may be declared complete because an agent asserts correctness — every gate must produce verifiable pass/fail evidence.

---

## Gate Hierarchy

### Baseline Gates (ALL tasks)

| Gate | Description | R1 | R2 | R3 | R4 |
|---|---|---|---|---|---|
| Build passes | Application compiles/builds without error | ✓ | ✓ | ✓ | ✓ |
| Type check passes | Static type analysis (mypy, tsc) | ✓ | ✓ | ✓ | ✓ |
| Lint passes | Code style enforcement (ruff, eslint) | ✓ | ✓ | ✓ | ✓ |
| Changed files match contract | Diff against contract allowed_files | ✓ | ✓ | ✓ | ✓ |
| Protected zones untouched | Diff against protected-zones.yaml | ✓ | ✓ | ✓ | ✓ |
| Change budget respected | Lines/files/folders within limits | — | ✓ | ✓ | ✓ |
| No unauthorized dependencies | New deps require explicit approval | — | ✓ | ✓ | ✓ |

### Test Gates

| Gate | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Unit tests pass | ✓ | ✓ | ✓ | ✓ |
| Integration tests pass | — | ✓ | ✓ | ✓ |
| API contract tests pass | — | — | ✓ | ✓ |
| Schema validation passes | — | — | ✓ | ✓ |
| Migration tests pass | — | — | ✓ | ✓ |

### Evidence Gates

| Gate | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Documentation updated | — | ✓ | ✓ | ✓ |
| Rollback information available | — | ✓ | ✓ | ✓ |
| Screenshot evidence (visual tasks) | ✓ | ✓ | ✓ | ✓ |
| Accessibility baseline | — | ✓ | ✓ | ✓ |

### AVOA-Specific Business Gates

| Gate | R2 | R3 | R4 |
|---|---|---|---|
| Pricing fixtures pass | — | — | ✓ |
| Occupancy fixtures pass | — | — | ✓ |
| Offer-combination fixtures pass | — | — | ✓ |
| Tax fixtures pass | — | — | ✓ |
| Markup and commission fixtures pass | — | — | ✓ |
| Cancellation fixtures pass | — | — | ✓ |
| Quote reproducibility | — | — | ✓ |
| Reservation-state validation | — | ✓ | ✓ |
| API-contract checks | — | ✓ | ✓ |
| Audit-event checks | — | — | ✓ |

---

## CI Workflow Specification

### Minimum CI (HOS-1)

```yaml
name: Hermes OS v3.1 CI
on:
  push:
    branches: [feature/**]
  pull_request:
    branches: [master]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Type check
        run: mypy backend/app/
      - name: Lint
        run: ruff check backend/
      - name: Unit tests
        run: python -m pytest backend/tests/ -v --tb=short
      - name: Changed-file report
        run: .hermes/scripts/scope-check.sh
      - name: Protected-zone check
        run: .hermes/scripts/protected-zone-check.sh

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Type check
        run: cd frontend && npx tsc --noEmit
      - name: Lint
        run: cd frontend && npx eslint src/
      - name: Build
        run: cd frontend && npm run build
```

---

## Scope Check Script Specification

`scope-check.sh`: Compares `git diff` files against the task contract's `allowed_files` list.

```bash
# Input: TASK_ID from environment or first argument
# Reads: .hermes/contracts/${TASK_ID}.yaml
# Output: PASS if all changed files are in allowed_files, FAIL with violations otherwise
# Exit: 0 on PASS, 1 on FAIL
```

### Protected-Zone Check Script Specification

`protected-zone-check.sh`: Compares `git diff` files against protected-zones.yaml.

```bash
# Input: TASK_ID from environment or first argument
# Reads: .hermes/policies/protected-zones.yaml
# Output: PASS if no protected files changed, FAIL with violations
# Exit: 0 on PASS, 1 on FAIL
# SCOPE_EXCEEDED trigger: if protected zone change detected without authorization
```

---

## Evidence Authority

Objective test evidence has higher authority than agent opinion.

```
Kimi says correct     ┐
Claude says correct   ├─→ BOTH agents agree
Required fixture fails ┘
→ TASK REJECTED
```

---

## Missing Gate Handling

If a required gate has no implementation yet:

- Report honestly: "Gate X: NOT IMPLEMENTED"
- Do not fabricate a passing result
- Do not skip the gate silently
- Hermes records the gap in the task evidence

---

## Gate Results Format

```yaml
validation_run:
  task_id:
  run_id:
  timestamp:
  gates:
    - gate_id:
      name:
      required: true|false
      status: passed|failed|skipped|not_implemented
      evidence:
      error:
```

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*