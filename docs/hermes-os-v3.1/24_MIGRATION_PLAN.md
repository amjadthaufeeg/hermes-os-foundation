# 24 — Migration Plan

**Status:** SPECIFICATION
**Version:** 3.1

## Principle

No big-bang rewrite. Each release builds incrementally on the working system. Every release must be independently deployable and reversible.

## Release Sequence

### HOS-1 — Governance and Repository-Safety Foundation

**Objective:** Implement the minimum governance schemas, policies, and enforcement that make all subsequent releases safe.

**Scope:**
- Task-contract YAML schema + template
- UI-contract schema + template
- Risk classification R1-R4
- Task state machine definitions
- Role and permission model
- Review-report schema
- Design-review schema
- Finding-decision schema
- Evidence-package schema
- Decision register (17 proposed records, 2 locked)
- Regression-register structure
- Protected-zone policy + manifest
- Direct-push policy (interim)
- Minimum CI workflow (build + lint + test)
- Schema validation script
- Changed-file reporting script
- Minimal scope checker script
- Minimal protected-zone checker script
- Branch-protection preparation
- Command Center event requirements

**Excluded from HOS-1:**
- Full Command Center UI
- Broad sub-agent autonomy
- Parallel production-code editing
- Automatic integration
- Automatic deployment
- Unrestricted worktree automation
- R4 parallel writes

**Risk:** LOW — schemas and policies only; no product code changes
**Dependencies:** None — uses existing Hermes Agent infrastructure
**Pilot:** HOS-1 is validated by applying its contracts to the next actual AVOA task

### HOS-2 — Design Foundation and UI Contracts

**Objective:** Implement Design Studio foundation — design-system documentation, UI contracts in practice, Visual QA automation.

**Scope:**
- AVOA design-system audit and documentation
- Color, typography, spacing, component tokens
- Accessibility baseline (axe-core in CI)
- Visual QA automation (screenshot capture at breakpoints)
- First formal UI contract used on a real task

**Dependencies:** HOS-1
**Risk:** LOW — design documentation only

### HOS-3 — Command Center Data and Event Foundation

**Objective:** Implement event-sourcing backbone and data storage for task state, evidence, and agent runs.

**Scope:**
- Task state event log
- Agent run tracking
- Evidence storage
- Decision register API
- Regression register API

**Dependencies:** HOS-1
**Risk:** LOW-MEDIUM — data infrastructure

### HOS-4 — Command Center MVP

**Objective:** Evidence-backed operational dashboard showing real task state.

**Scope:**
- Executive Overview module
- Engineering Mission Control module
- Quality and Evidence module
- Knowledge module (decisions/regressions)

**Dependencies:** HOS-3
**Risk:** MEDIUM — UI development

### HOS-5 — Read-Only Parallel-Execution Pilot

**Objective:** Validate parallel agent execution with read-only and restricted-write roles.

**Scope:**
- Scout profile configuration (read-only)
- Test Agent profile (test files only)
- Documentation Agent profile (docs only)
- Single pilot task with 2 parallel read-only agents

**Dependencies:** HOS-1, HOS-2
**Risk:** LOW — no production writes

### HOS-6 — Controlled UI Parallelism

**Objective:** Parallel UI implementation with non-overlapping components.

**Scope:**
- Parallel Controller basic implementation
- Worktree isolation for 2 parallel UI agents
- File ownership enforcement
- Collision detection
- Kimi K3 integration handoff

**Dependencies:** HOS-5
**Risk:** MEDIUM — new coordination mechanisms

### HOS-7 — Expanded Specialist Parallelism

**Objective:** Full parallel capability with specialist agents.

**Scope:**
- Full Parallel Execution Controller
- API Specialist, Database Specialist integration
- Multi-agent worktree management
- Integration automation
- Kanban-based task dispatch

**Dependencies:** HOS-6
**Risk:** MEDIUM-HIGH — coordination complexity

### HOS-8 — Operational Maturity and Routing Optimization

**Objective:** Evidence-based routing, scorecard-driven optimization, operational dashboard completion.

**Scope:**
- Builder scorecard automation
- Routing optimization from scorecard data
- Full Command Center (all 10 modules)
- Operational metrics and alerting
- Continuous improvement feedback loop

**Dependencies:** HOS-7
**Risk:** LOW-MEDIUM — optimization of existing

---

*Part of Hermes OS v3.1 — Specification.*