# 17 — Regression Memory Standard

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

Every important fixed defect must create a durable regression record. A bug is not considered permanently fixed until protected by a test, fixture, or repeatable validation.

---

## Regression Record Schema

```yaml
regression_id: REG-XXX-NNN
title:
status: active|guarded|retired
date_identified:
date_fixed:
last_verified:

affected_area:
  product: avoa
  domain: pricing|occupancy|offers|tax|commission|cancellation|reconciliation|auth|permissions|schema|ui|api
  files:
    - path/to/file.py
    - path/to/file.tsx

symptoms: >
  What was observed. Be specific. Include inputs that trigger the defect.

root_cause: >
  Why it happened. Technical explanation.

fix: >
  What was changed to resolve it.

protection:
  tests:
    - test_file.py::test_name
  fixtures:
    - fixture_file.json
  gates:
    - protected_zone_check
    - business_fixture_check

related_tasks:
  - TASK-XXXX

related_regressions:
  - REG-XXX-NNN
```

---

## Status Lifecycle

```
active → guarded → retired
```

- **Active:** Defect fixed but not yet protected by automated test
- **Guarded:** Protected by automated test or fixture that would catch recurrence
- **Retired:** No longer applicable (code removed, system retired)

---

## Usage

- Hermes retrieves relevant regressions before assigning related work
- Task contracts include applicable regression IDs in `regressions_required`
- Claude receives relevant regressions in review package
- A regression graduates from `active` to `guarded` when a test exists that would fail on recurrence
- A `guarded` regression is re-verified periodically

---

## Current State (Audit Finding)

The v1.0 REGRESSION_REGISTER.md is a 16-line template with **zero entries**. No regression records exist.

### Seeding

Hermes should identify recently fixed defects and create REG-001 through REG-00N. If fewer than 3 verified defects can be identified, create only the verified records and report the gap.

**Do not invent regression records to satisfy a number.**

---

## Storage

```
.hermes/registers/regressions/
├── REG-001.yaml
├── REG-002.yaml
└── ...
```

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*