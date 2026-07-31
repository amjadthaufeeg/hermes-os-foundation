# Hermes Product OS v3.1 — Document Index

**Status:** IMPLEMENTING (HOS-1)
**Version:** 3.1
**Date:** 31 July 2026
**Supersedes:** Hermes OS v1.0 Foundation Pack, Hermes OS v3 Target Model
**Authority:** Amjad — approved

---

## Purpose

The Hermes Product OS v3.1 implementation package is the single authoritative specification for the Hermes operating model. It defines how AI agents collaborate under Hermes's sole orchestration to build, review, and maintain software products across all divisions: Engineering, Design Studio, Quality, Research, Knowledge, and Operations.

This package replaces informal multi-agent coordination with a documented, auditable, evidence-backed operating system.

---

## Document Structure

### Architecture & Organization

| # | Document | Purpose |
|---|---|---|
| 00 | `00_HERMES_OS_V3_1_INDEX.md` | This index — package overview and navigation |
| 01 | `01_HERMES_OS_V3_1_ARCHITECTURE.md` | System architecture, component map, data flow |
| 02 | `02_ORGANIZATIONAL_MODEL.md` | Department structure, role definitions, responsibility boundaries |
| 03 | `03_AUTHORITY_AND_AGENT_PERMISSIONS.md` | Permissions matrix, least-privilege rules, authority order |

### Contracts & Lifecycle

| # | Document | Purpose |
|---|---|---|
| 04 | `04_TASK_CONTRACT_STANDARD.md` | Task contract schema, creation, validation, lifecycle |
| 05 | `05_UI_CONTRACT_STANDARD.md` | UI contract schema for visual tasks |
| 06 | `06_TASK_LIFECYCLE.md` | Full 22-state machine with entry/exit/transition rules |
| 07 | `07_RISK_CLASSIFICATION.md` | R1-R4 risk model with parallelism rules |
| 08 | `08_PROTECTED_ZONES_AND_SCOPE_CONTROL.md` | Protected file/folder enforcement, change budgets |

### Parallel Execution

| # | Document | Purpose |
|---|---|---|
| 09 | `09_PARALLEL_EXECUTION_STANDARD.md` | Controller spec, eligibility, decomposition |
| 10 | `10_WORKTREE_AND_FILE_OWNERSHIP_STANDARD.md` | Single-writer enforcement, collision detection |

### Design Studio

| # | Document | Purpose |
|---|---|---|
| 11 | `11_DESIGN_STUDIO_OPERATING_MODEL.md` | Design roles, workflow, review gates |
| 12 | `12_AVOA_DESIGN_SYSTEM_PLAN.md` | AVOA-specific design token, component, and pattern audit |
| 13 | `13_DESIGN_REVIEW_AND_VISUAL_QA.md` | Visual review protocol, screenshot evidence standards |

### Quality & Review

| # | Document | Purpose |
|---|---|---|
| 14 | `14_AUTOMATED_QUALITY_GATES.md` | CI gate definitions, AVOA fixture requirements |
| 15 | `15_TECHNICAL_REVIEW_AND_FINDINGS_PROTOCOL.md` | Claude Code review package, findings schema, triage |

### Memory & Evidence

| # | Document | Purpose |
|---|---|---|
| 16 | `16_DECISION_MEMORY_STANDARD.md` | Decision register schema and lifecycle |
| 17 | `17_REGRESSION_MEMORY_STANDARD.md` | Regression register schema and protection rules |
| 18 | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` | Evidence package, readiness gates, completion criteria |
| 19 | `19_AGENT_ROUTING_AND_SCORECARDS.md` | Builder scorecard schema, evidence-based routing |

### Operations

| # | Document | Purpose |
|---|---|---|
| 20 | `20_ROLLBACK_AND_DEPLOYMENT_SAFETY.md` | Rollback packages, deployment gates, feature flags |

### Command Center

| # | Document | Purpose |
|---|---|---|
| 21 | `21_HERMES_COMMAND_CENTER_PRD.md` | Product requirements for the operational dashboard |
| 22 | `22_COMMAND_CENTER_INFORMATION_ARCHITECTURE.md` | Module structure, navigation, user flows |
| 23 | `23_COMMAND_CENTER_DATA_MODEL.md` | Entity definitions, relationships, storage approach |

### Migration & Backlog

| # | Document | Purpose |
|---|---|---|
| 24 | `24_MIGRATION_PLAN.md` | HOS-1 through HOS-8 release sequence |
| 25 | `25_PILOT_AND_ROLLOUT_PLAN.md` | 5 pilot definitions with acceptance criteria |
| 26 | `26_IMPLEMENTATION_BACKLOG.md` | 26 epics with detailed tasks, dependencies, risk |

---

## Machine-Readable Foundation

Located at `.hermes/`:

```
.hermes/
├── schemas/       # 13 JSON schemas for contracts, evidence, records
├── policies/      # 9 YAML policy files (risk, routing, permissions, etc.)
├── templates/     # 12 YAML templates for all contract/record types
├── registers/     # Decision and regression record storage
├── events/        # Task state event log
└── audit/         # Gap analysis (existing)
```

---

## Authority Order

1. Explicit current instruction from Amjad
2. Locked approved decisions
3. Approved parent task contract
4. Approved subtask and UI contracts
5. Product and architecture specifications
6. Risk, permission and protected-zone policies
7. Design-system standards
8. Agent recommendations

No lower-level instruction may override a higher-authority source.

---

## Implementation Status

| Release | Name | Status |
|---|---|---|
| HOS-1 | Governance and repository-safety foundation | **PLANNED** |
| HOS-2 | Design foundation and UI contracts | PLANNED |
| HOS-3 | Command Center data and event foundation | PLANNED |
| HOS-4 | Command Center MVP | PLANNED |
| HOS-5 | Read-only parallel-execution pilot | PLANNED |
| HOS-6 | Controlled UI parallelism | PLANNED |
| HOS-7 | Expanded specialist parallelism | PLANNED |
| HOS-8 | Operational maturity and routing optimization | PLANNED |

---

*Version 3.1 — Specification. Awaiting implementation authorization.*