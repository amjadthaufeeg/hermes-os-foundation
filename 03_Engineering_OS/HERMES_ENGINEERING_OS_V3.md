# Hermes Engineering OS v3 — Target Operating Model

**Status: APPROVED DIRECTION — Awaiting Audit Before Implementation**

**Approved by:** Amjad
**Date:** 31 July 2026
**Supersedes:** Hermes OS v1.0 DEVELOPMENT_OPERATING_MODEL.md

> **IMPORTANT:** This document is the approved target. Do not implement yet.
> An audit of the current implementation against this target is required first.
> Implementation order is defined in Section 17.

---

## Section 1 — Final Authority and Agent Roles

### Amjad

Amjad is:

- product owner;
- business-rule authority;
- commercial-rule authority;
- final approval authority;
- final authority for architecture or scope decisions that materially affect the product.

Amjad should approve:

- product direction;
- workflow behaviour;
- major architecture changes;
- critical commercial logic;
- pricing behaviour;
- release readiness where required;
- final visual and product outcome.

Amjad should not need to approve routine technical implementation details when they remain within an already approved task contract.

### Hermes

Hermes is the:

- sole orchestrator;
- persistent context layer;
- engineering manager;
- scope controller;
- task-state authority;
- evidence manager;
- decision-memory manager;
- regression-memory manager;
- agent router;
- review-triage authority.

Hermes must remain the only agent allowed to:

- create or approve task contracts;
- define or change scope;
- classify risk;
- unlock protected zones;
- accept or reject reviewer findings;
- route work between agents;
- declare a task ready for Amjad;
- authorize merge or deployment after required gates.

Hermes must not delegate orchestration authority to Kimi, Codex or Claude Code.

Agents must not directly control one another.

Required communication path:

```
Builder submits implementation
→ Hermes sends evidence package to reviewer
→ Reviewer submits findings to Hermes
→ Hermes accepts or rejects findings
→ Hermes sends only approved corrections to builder
```

Claude Code must not directly instruct the builder.

The builder must not independently implement every reviewer suggestion.

### Kimi K3

Kimi K3 is the **primary building agent**.

Kimi should normally handle:

- new feature implementation;
- multi-file implementation;
- vertical slices;
- frontend development;
- backend development;
- API implementation;
- repository-wide tasks requiring large context;
- coordinated code and documentation updates;
- controlled refactoring;
- approved corrections.

Kimi has implementation write access only within the active task contract.

Kimi must not:

- redefine the objective;
- expand task scope;
- change architecture without approval;
- edit protected zones without an explicit unlock;
- treat reviewer findings as direct instructions;
- mark its own work approved;
- mark a task safe for production;
- merge directly into a protected branch;
- deploy production independently.

Kimi may report only:

> Implementation submitted with supporting evidence.

### Claude Code

Claude Code is the **independent reviewer**.

Claude should initially operate in review-only mode.

Claude may inspect:

- the repository;
- task contract;
- Git diff;
- relevant product decisions;
- regression records;
- test results;
- build results;
- screenshots;
- builder assumptions;
- acceptance criteria.

Claude should review:

- objective completion;
- scope compliance;
- architecture compliance;
- business-rule compliance;
- regression risk;
- maintainability;
- security;
- test adequacy;
- accessibility where relevant;
- alignment between the builder's explanation and actual code changes.

Claude must return structured findings to Hermes.

Claude must not:

- directly instruct Kimi;
- change task scope;
- automatically rewrite the implementation;
- merge code;
- approve production deployment;
- act as a second orchestrator.

Claude may report only:

> Review completed with findings.

Hermes decides what happens next.

### Codex

Codex remains available as the:

- precision builder;
- recovery builder;
- fallback builder;
- challenger implementation agent;
- surgical bug-fix agent.

Hermes should consider routing to Codex when:

- the task is a narrow bug fix;
- only a few named files may change;
- preserving existing behaviour is the highest priority;
- Kimi fails two controlled correction cycles;
- Kimi repeatedly exceeds scope;
- an independent implementation is required for comparison;
- a technically precise repair is needed;
- Hermes determines Codex has stronger historical performance for that task category.

Codex is not the default builder, but it must remain available.

### GitHub

GitHub is the authoritative source of truth for:

- branches;
- commits;
- pull requests;
- reviews;
- test history;
- release history;
- rollback history.

No agent should directly modify a protected production branch.

### Preview Environment

Replit may be used for:

- rapid experiments;
- prototypes;
- live UI review;
- temporary previews;
- runtime inspection.

Replit must not become the authoritative code repository.

For main AVOA development, prefer GitHub-connected pull-request or staging previews that remain close to the production environment.

---

## Section 2 — Approved Operating Workflow

```
                    AMJAD
          Product owner / final authority
                      │
                      ▼
                   HERMES
     Persistent context + sole orchestrator
     Scope, risk, routing and evidence control
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
       KIMI K3               CLAUDE CODE
   Primary implementation    Independent review
   Contract-limited write    Review-only initially
          │                       │
          └───────────┬───────────┘
                      ▼
                   HERMES
        Accept/reject and triage findings
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
       KIMI K3                  CODEX
 Normal approved fixes     Precision/recovery fixes
          │                       │
          └───────────┬───────────┘
                      ▼
             AUTOMATED QUALITY GATES
       Build / tests / scope / business fixtures
                      │
                      ▼
                CLAUDE CODE
                Final validation
                      │
                      ▼
                   HERMES
          Evidence-based readiness decision
                      │
                      ▼
                    AMJAD
      Visual, product and commercial approval
                      │
                      ▼
              GITHUB MERGE / DEPLOY
```

---

## Section 3 — Task-Contract Requirement

Hermes must not send vague development requests directly to a builder.

Every development task must first become a structured task contract containing at least:

```yaml
task_id:
project:
title:
task_type:
risk_level:

objective:

context_required:

allowed_files:
allowed_folders:

protected_areas:

must_not_change:

change_budget:
  max_files:
  max_folders:
  max_lines_changed:

acceptance_criteria:

required_checks:

required_evidence:

stop_conditions:

builder:
reviewer:
final_authority:
```

A task contract must distinguish:

- what should change;
- what may change;
- what must not change;
- how success will be proven;
- when the builder must stop.

For vague requests such as "Make this page cleaner," Hermes should internally convert the request into something like:

```
Objective:
Improve visual hierarchy, spacing and readability.

Permitted:
Presentation-layer changes in named UI components.

Forbidden:
Workflow, state, API, database, navigation, permission or calculation changes.
```

The builder receives the structured contract, not merely the vague original request.

---

## Section 4 — Task Lifecycle

Hermes must own the task state machine.

Target states:

```
REQUESTED
CONTEXT_RETRIEVAL
CONTRACT_DRAFTED
SCOPE_APPROVED
BUILDING
IMPLEMENTATION_SUBMITTED
AUTOMATED_VALIDATION
INDEPENDENT_REVIEW
FINDINGS_TRIAGE
CORRECTION
FINAL_VALIDATION
READY_FOR_AMJAD
APPROVED
MERGED
DEPLOYED
MONITORED
CLOSED
```

Failure or exception states:

```
BLOCKED
SCOPE_EXCEEDED
VALIDATION_FAILED
REVIEW_REJECTED
AWAITING_DECISION
ROLLBACK_REQUIRED
CANCELLED
```

Kimi, Codex and Claude must not advance their own tasks into approved, merged, deployed or closed states.

Hermes controls state transitions.

---

## Section 5 — Risk Classification

Every task must receive a risk level before implementation.

### Risk Level 1 — Low

Examples: copy, spacing, colours, documentation, non-functional styling, isolated presentation-layer improvements.

Requirements: task contract, build, scope check, relevant tests, Claude review, Amjad visual approval where appropriate.

### Risk Level 2 — Moderate

Examples: forms, filters, frontend state, admin pages, non-critical APIs, normal workflow UI.

Requirements: task contract, automated tests, independent review, preview, scope verification, correction cycle if needed.

### Risk Level 3 — High

Examples: authentication, permissions, database schema, migrations, integrations, reservation lifecycle, API contracts, important state transitions.

Requirements: explicit Hermes approval, stronger test package, rollback package, migration or compatibility validation, independent review, Amjad approval where behaviour materially changes.

### Risk Level 4 — Critical

Examples: pricing, occupancy, offers, taxes, commissions, markups, cancellation calculations, amendments, reconciliation, commercial audit logic, financial behaviour.

Requirements: task contract, Amjad approval before implementation when commercial behaviour changes, deterministic fixtures, protected-zone authorization, builder implementation, automated regression suite, Claude review, Hermes findings triage, final validation, Amjad commercial approval, controlled deployment and rollback readiness.

---

## Section 6 — Protected Zones

Hermes must support protected folders, files and domains.

Protected zones should include, once mapped to the actual repository:

```
pricing engine
offer engine
occupancy engine
tax logic
markup and commission logic
cancellation logic
reconciliation
authentication
permissions
database schema
migrations
reservation state machine
API contracts
audit records
```

An agent attempting to edit an unauthorized protected zone must trigger:

```
STATUS: SCOPE_EXCEEDED

Protected area change detected.

Stop implementation.
Return the task to Hermes.
Do not continue or widen the scope.
```

Protected-zone control must eventually be enforced through scripts or CI checks, not only through prompts.

---

## Section 7 — Change Budgets

Each task should define a reasonable maximum:

- number of changed files;
- number of changed folders;
- number of changed lines;
- dependency changes;
- database changes.

Exceeding the approved change budget must stop the task and return it to Hermes.

Change budgets are safety boundaries, not performance targets.

Hermes may revise the budget only after reviewing why additional scope is necessary.

---

## Section 8 — Automated Gates

A task cannot be completed merely because an agent says it is correct.

Baseline automated gates should include, where applicable:

```
Build passes
Type checking passes
Linting passes
Unit tests pass
Integration tests pass
Changed files match contract
Protected zones remain untouched
Change budget is respected
No unauthorized dependency changes
Required documentation is updated
API compatibility is preserved
Rollback information is available
```

AVOA-specific gates should include:

```
Pricing fixtures
Occupancy fixtures
Offer-combination fixtures
Tax fixtures
Markup and commission fixtures
Cancellation fixtures
Quote reproducibility
Reservation-state validation
API-contract checks
Audit-event checks
```

Objective test evidence has higher authority than agent opinion.

```
Kimi says correct
Claude says correct
Required fixture fails
→ Task rejected
```

---

## Section 9 — Review Protocol

Claude should receive a review package containing:

```
Original request
Task contract
Acceptance criteria
Relevant locked decisions
Relevant regression records
Git diff
Changed-file list
Builder report
Build results
Test results
Screenshots
Known assumptions
Known limitations
```

Claude should return structured findings containing:

```yaml
review_id:
task_id:

summary:
  objective_achieved:
  scope_respected:
  tests_sufficient:
  ready_for_correction:
  ready_for_final_validation:

findings:
  - finding_id:
    severity:
    category:
    file:
    location:
    description:
    evidence:
    recommendation:
```

Severity levels:

```
BLOCKER
HIGH
MEDIUM
LOW
OPTIONAL
```

Hermes must decide for every meaningful finding:

```yaml
finding_id:
decision: accepted | rejected | deferred
reason:
approved_correction:
```

Only approved corrections may be sent to the builder.

Broad refactors or architecture changes suggested during review must become separate tasks unless they are essential to correct the approved task.

---

## Section 10 — Decision Register

Hermes must maintain durable architectural, product and commercial decisions.

Each record should include:

```yaml
decision_id:
title:
status:
date:
owner:
applies_to:
decision:
reason:
alternatives_considered:
supersedes:
superseded_by:
related_tasks:
```

### Initial Locked Decisions

```yaml
decision_id: DEC-HOS-001
title: Hermes remains the sole orchestrator
status: locked
decision: >
  Kimi, Codex and Claude may build or review within assigned roles,
  but they may not independently control scope, task-state transitions,
  agent routing, approval, merge or deployment.
reason: >
  Prevent conflicting agent authority and uncontrolled workflow expansion.
```

```yaml
decision_id: DEC-AVOA-PRICING-001
title: Final commercial calculations remain deterministic
status: locked
decision: >
  AI may extract, interpret, normalize and explain contract data.
  Final prices, offers, occupancy outcomes, taxes, commissions,
  markups, cancellation values and reconciliation values must be
  produced by deterministic code using approved structured inputs.
reason: >
  Commercial results must be reproducible, auditable and testable.
```

---

## Section 11 — Regression Register

Every important fixed defect should create a regression record.

Each regression record should contain:

```yaml
regression_id:
title:
affected_area:
symptoms:
root_cause:
fix:
protection:
  tests:
  fixtures:
related_files:
related_tasks:
status:
last_verified:
```

Before assigning related work, Hermes should retrieve relevant regression records and include them in the task contract.

An important bug should not be considered permanently fixed until protected by a test, fixture or repeatable validation whenever technically possible.

---

## Section 12 — Builder Scorecards

Hermes should collect performance evidence for Kimi and Codex.

Track:

```
Task category
Risk level
First-pass build success
First-pass test success
Scope violations
Protected-zone violations
Reviewer blockers
Reviewer high findings
Correction cycles
Regression introduced
Human acceptance
Cost
Execution time
Final outcome
```

Agent routing should gradually become evidence-based.

Kimi remains the default builder initially, but Hermes may route tasks differently when actual project performance justifies it.

---

## Section 13 — Rollback Safety

Every high-risk or deployable task should produce a rollback package containing:

```
Branch
Current commit
Previous stable commit
Files changed
Dependencies changed
Database migrations
Migration rollback instructions
Feature flags
Deployment identifier
Rollback steps
Post-rollback checks
```

High-risk features should use feature flags or gradual deployment where practical.

---

## Section 14 — Mission Control Dashboard

Mission Control is not merely a visual chat interface. It must display structured, evidence-backed engineering state.

Initial dashboard areas:

```
Portfolio overview
Project overview
Release overview
Active tasks
Blocked tasks
Tasks ready for Amjad
Task detail
Task contracts
Agent runs
Changed files
Validation results
Review findings
Finding decisions
Decision register
Regression register
Builder scorecards
Deployment history
Rollback packages
```

The dashboard must not display invented progress numbers.

Do not show an arbitrary "72% complete" unless a documented formula exists.

Prefer evidence-based stage progress:

```
Contract: complete
Implementation: complete
Automated gates: 8 of 10
Independent review: in progress
Corrections: pending
Amjad approval: not started
```

Mission Control must read from actual task, evidence, review and deployment records.

It should not infer critical status only from conversation text.

---

## Section 15 — Two-Memory Model

Hermes should distinguish:

### Product Memory

Long-lived:

- product architecture;
- business rules;
- locked decisions;
- design system;
- release plan;
- feature disposition;
- regression records;
- domain vocabulary.

### Task Memory

Temporary:

- current branch;
- active task;
- current correction;
- current test failures;
- active review;
- transient logs.

Task memory should be archived or reduced after task closure.

Product memory must remain durable.

---

## Section 16 — Evidence-Based Completion

Hermes must not mark a task ready because the builder reports completion.

A completion evidence package should include, as applicable:

```
Objective achieved
Acceptance criteria checked
Allowed scope respected
Protected zones unchanged or properly authorized
Build passed
Type check passed
Lint passed
Tests passed
Business fixtures passed
Review completed
Accepted findings resolved
Final validation completed
Preview available
Rollback ready
Known limitations disclosed
```

Hermes may then mark the task:

> READY_FOR_AMJAD

Hermes must not call a task complete when required evidence is missing.

---

## Section 17 — Implementation Order

Do not build the Mission Control interface before the underlying task, evidence, review and decision records exist.

```
1. Audit existing Hermes
2. Preserve current working system
3. Define schemas and policies
4. Implement task contracts
5. Implement risk classification
6. Implement state machine
7. Implement protected-zone and scope checks
8. Implement evidence collection
9. Implement review triage
10. Implement decision and regression memory
11. Implement rollback records
12. Implement Mission Control APIs
13. Implement Mission Control interface
14. Run controlled pilots
15. Gradually migrate normal development work
```

---

## Section 18 — Immediate Instruction

These decisions are stored as the target Hermes Engineering OS v3 operating model.

Do not yet make broad implementation changes.

Next: conduct a repository and workflow audit using a separate audit instruction.

When reporting, clearly distinguish:

- current verified behaviour;
- assumptions;
- missing information;
- proposed changes;
- decisions requiring Amjad.

---

*Version 3.0 — Approved 31 July 2026. Supersedes Hermes OS v1.0 DEVELOPMENT_OPERATING_MODEL.md.*