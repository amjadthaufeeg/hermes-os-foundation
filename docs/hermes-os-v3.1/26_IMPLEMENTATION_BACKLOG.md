# 26 — Implementation Backlog

**Status:** SPECIFICATION
**Version:** 3.1

## Epic Summary

| Epic | Title | Release | Complexity | Risk |
|---|---|---|---|---|
| EPIC-HOS-001 | Core schemas and policy files | HOS-1 | M | Low |
| EPIC-HOS-002 | Task-contract engine | HOS-1 | L | Low |
| EPIC-HOS-003 | Risk classifier | HOS-1 | S | Low |
| EPIC-HOS-004 | Task state machine | HOS-1 | M | Low |
| EPIC-HOS-005 | Scope and protected-zone enforcement | HOS-1 | M | Medium |
| EPIC-HOS-006 | Evidence collection | HOS-1 | M | Low |
| EPIC-HOS-007 | Technical review triage | HOS-1 | M | Low |
| EPIC-HOS-008 | Decision register | HOS-1 | S | Low |
| EPIC-HOS-009 | Regression register | HOS-1 | S | Low |
| EPIC-HOS-010 | Rollback manager | HOS-1 | S | Low |
| EPIC-HOS-011 | Minimum CI and repository safety | HOS-1 | L | High |
| EPIC-HOS-012 | Organizational model | HOS-1 | S | Low |
| EPIC-HOS-013 | UI-contract engine | HOS-2 | M | Low |
| EPIC-HOS-014 | Design Studio foundation | HOS-2 | M | Medium |
| EPIC-HOS-015 | AVOA design system | HOS-2 | L | Low |
| EPIC-HOS-016 | Design review and Visual QA | HOS-2 | M | Medium |
| EPIC-HOS-017 | Command Center event foundation | HOS-3 | M | Low |
| EPIC-HOS-018 | Command Center backend | HOS-3 | L | Medium |
| EPIC-HOS-019 | Command Center MVP | HOS-4 | XL | Medium |
| EPIC-HOS-020 | Parallel eligibility engine | HOS-5 | M | Low |
| EPIC-HOS-021 | File ownership and collision detection | HOS-5 | M | Medium |
| EPIC-HOS-022 | Worktree manager | HOS-6 | L | Medium |
| EPIC-HOS-023 | Subtask dependency controller | HOS-6 | M | Medium |
| EPIC-HOS-024 | Integration manager | HOS-6 | M | Medium |
| EPIC-HOS-025 | Parallel execution pilots | HOS-5-7 | L | Low |
| EPIC-HOS-026 | Agent routing and scorecards | HOS-8 | M | Low |

## HOS-1 Detailed Tasks (EPIC-001 through EPIC-011)

### EPIC-HOS-001 — Core Schemas and Policy Files

| Task | Title | Complexity | Builder | Risk |
|---|---|---|---|---|
| HOS-001-01 | Create task-contract JSON schema | S | Hermes | R1 |
| HOS-001-02 | Create UI-contract JSON schema | S | Hermes | R1 |
| HOS-001-03 | Create evidence-package JSON schema | S | Hermes | R1 |
| HOS-001-04 | Create review-report JSON schema | S | Hermes | R1 |
| HOS-001-05 | Create decision-record JSON schema | S | Hermes | R1 |
| HOS-001-06 | Create regression-record JSON schema | S | Hermes | R1 |
| HOS-001-07 | Create risk-levels.yaml policy | S | Hermes | R1 |
| HOS-001-08 | Create role-permissions.yaml policy | S | Hermes | R1 |
| HOS-001-09 | Create protected-zones.yaml policy | S | Hermes | R1 |
| HOS-001-10 | Create quality-gates.yaml policy | S | Hermes | R1 |
| HOS-001-11 | Create direct-push-policy.yaml | S | Hermes | R1 |

### EPIC-HOS-002 — Task-Contract Engine

| Task | Title | Complexity | Builder | Risk |
|---|---|---|---|---|
| HOS-002-01 | Create task-contract template (YAML) | S | Hermes | R1 |
| HOS-002-02 | Create task-contract validation script | M | Hermes | R1 |
| HOS-002-03 | Create task-contract amendment workflow doc | S | Hermes | R1 |

### EPIC-HOS-004 — Task State Machine

| Task | Title | Complexity | Builder | Risk |
|---|---|---|---|---|
| HOS-004-01 | Define state machine as Python enum | S | Kimi K3 | R1 |
| HOS-004-02 | Implement state transition validation | M | Kimi K3 | R1 |
| HOS-004-03 | Create task-state-event logging | M | Kimi K3 | R1 |

### EPIC-HOS-005 — Scope and Protected-Zone Enforcement

| Task | Title | Complexity | Builder | Dependencies | Risk |
|---|---|---|---|---|---|
| HOS-005-01 | Create scope-check script | M | Kimi K3 | HOS-001-09 | R2 |
| HOS-005-02 | Create protected-zone-check script | M | Kimi K3 | HOS-001-09 | R2 |
| HOS-005-03 | Create change-budget-check script | M | Kimi K3 | HOS-001-09 | R2 |
| HOS-005-04 | Integrate scripts into CI | M | Hermes | HOS-005-01,02,03 | R2 |

### EPIC-HOS-008 — Decision Register

| Task | Title | Complexity | Builder | Risk |
|---|---|---|---|---|
| HOS-008-01 | Create decision register directory structure | S | Hermes | R1 |
| HOS-008-02 | Write 17 proposed decision records (2 locked) | M | Hermes | R1 |
| HOS-008-03 | Create decision retrieval and citation system | M | Kimi K3 | R1 |

### EPIC-HOS-011 — Minimum CI and Repository Safety

| Task | Title | Complexity | Builder | Dependencies | Risk |
|---|---|---|---|---|---|
| HOS-011-01 | Fix test collection error | S | Codex | — | R2 |
| HOS-011-02 | Create GitHub Actions CI workflow | M | Hermes | HOS-011-01 | R2 |
| HOS-011-03 | Integrate scope and protected-zone checks into CI | M | Hermes | HOS-005-04 | R2 |
| HOS-011-04 | Verify CI passes on feature branch | S | Hermes | HOS-011-02 | R2 |
| HOS-011-05 | Document branch protection check names | S | Hermes | HOS-011-04 | R2 |
| HOS-011-06 | Test pilot branch with protected master | M | Hermes | HOS-011-05 | R2 |

---

## Deferred Epics (HOS-5 through HOS-8)

Detailed task breakdown for HOS-5 through HOS-8 should be created after HOS-1 through HOS-4 are complete, when the infrastructure for parallel execution and scorecards is better understood.

---

*Part of Hermes OS v3.1 — Specification.*