# Hermes Development Operating Model v1.0

## Status

**Approved target operating model**

This document defines the controlled development workflow for AVOA, Maldives Experts, and future Nauvis Labs products.

It replaces informal multi-agent development with a single, auditable operating model.

---

## 1. Operating Decision

The preferred development model is:

```text
Amjad
= product direction, business decisions, visual acceptance, and final approval

Hermes
= sole orchestrator, scope controller, project memory, and evidence manager

Kimi K3
= primary building agent for substantial implementation work

Codex
= precision builder, repair specialist, fallback, and challenger

Claude Code
= independent reviewer and architectural critic

GitHub
= authoritative source of code, branches, review history, and rollback

Replit
= live preview and runtime-feedback environment

Automated verification
= non-negotiable quality gate
```

Kimi K3 is the default primary builder, but no model is assumed to be universally superior. Hermes must route work using task scope, risk, and measured performance on the actual project.

---

## 2. Core Principles

1. **One orchestrator:** Hermes is the only agent authorized to assign work, define scope, and coordinate handoffs.
2. **One source of truth:** GitHub is authoritative. No agent or preview environment may maintain unique uncommitted product code.
3. **One writer at a time:** Only the assigned builder may modify a task branch during an implementation or repair cycle.
4. **Immutable task contract:** The approved objective, protected areas, and acceptance criteria cannot be reinterpreted by the builder or reviewer.
5. **Preserve working behavior by default:** A request to change one area does not authorize changes to adjacent workflows, logic, APIs, schemas, or architecture.
6. **Smallest sufficient change:** Builders must patch existing code rather than regenerate or refactor unrelated areas.
7. **Evidence over claims:** A task is complete only when supported by diffs, tests, review evidence, and a working preview.
8. **Humans approve product decisions:** Agents may implement and evaluate, but Amjad remains the authority for product behavior, business rules, and visual acceptance.
9. **Every confirmed defect becomes institutional memory:** Important fixes must be recorded and protected by tests or repeatable validation checks.
10. **Rollback is mandatory:** Every task must have a known baseline commit and a reversible delivery path.

---

## 3. What Hermes Should Learn From Replit

Replit is valuable primarily because it shortens the feedback loop:

> Idea → Plan → Code → Run → Preview → Fix → Deploy

Hermes should reproduce the strength of that workflow while adding stronger organizational context and control:

- durable product and business memory;
- strict task boundaries;
- specialized implementation and review agents;
- independent validation;
- visible progress and evidence;
- protected product decisions;
- reliable rollback;
- context across AVOA, Maldives Experts, and future products.

The goal is not to reproduce Replit exactly. The goal is to combine Replit-like speed with stronger governance and project memory.

---

## 4. Target Architecture

```text
                              AMJAD
                 Product Owner / Final Authority
                                │
                                ▼
                              HERMES
             Sole Orchestrator and Engineering Manager
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
 Product context         Change contract          Regression register
 Locked decisions        Task state               Builder scorecards
 Architecture records    Scope and risk           Delivery evidence
       │                        │                        │
       └────────────────────────┴────────────────────────┘
                                │
                                ▼
                         BUILDER ROUTING
                  Kimi K3 or Codex — never both
                                │
                                ▼
                     ISOLATED FEATURE BRANCH
                      or dedicated Git worktree
                                │
                                ▼
                              GITHUB
                    Authoritative task branch
                                │
                ┌───────────────┴────────────────┐
                ▼                                ▼
       AUTOMATED VERIFICATION              CLAUDE CODE
       Build, tests, lint,                 Independent review,
       type checks, contracts,             regression and scope audit
       visual and rule fixtures                  │
                │                                │
                └───────────────┬────────────────┘
                                ▼
                              HERMES
                 Accepts or rejects review findings
                                │
                    Approved corrections only
                                │
                                ▼
                      ORIGINAL BUILDER OR CODEX
                                │
                                ▼
                    FINAL VERIFICATION + REVIEW
                                │
                                ▼
                              REPLIT
                  Live preview of committed branch
                                │
                                ▼
                              AMJAD
                 Product, workflow, and visual review
                                │
                                ▼
                      APPROVAL → MERGE → DEPLOY
```

---

## 5. Authority Model

### 5.1 Amjad — Product Owner

Amjad is the final authority for:

- product direction;
- business rules;
- user workflows;
- visual acceptance;
- unlocking or changing locked decisions;
- production release approval.

### 5.2 Hermes — Sole Orchestrator

Hermes owns:

- task intake and interpretation;
- retrieval of relevant project context;
- task classification and risk assessment;
- change-contract creation;
- builder selection;
- branch and baseline tracking;
- scope enforcement;
- review coordination;
- regression-register maintenance;
- evidence collection;
- status and delivery reporting.

Hermes must not write major production code by default.

Hermes must not silently change or reinterpret an approved product decision. When requirements conflict, Hermes must surface the conflict rather than allowing a builder to choose.

### 5.3 Kimi K3 — Primary Builder

Use Kimi K3 for:

- new features;
- full vertical slices;
- frontend and backend implementation;
- coordinated multi-file work;
- repository-wide understanding;
- large-context tasks;
- controlled refactoring;
- coordinated code and documentation updates.

Kimi may modify only the assigned task branch and only within the approved change contract.

### 5.4 Codex — Precision Builder and Fallback

Use Codex for:

- surgical bug fixes;
- narrowly scoped patches;
- highly sensitive behavior-preservation work;
- tasks limited to a few permitted files;
- repair of a failed or overbroad Kimi implementation;
- independent implementation challenges for high-risk work;
- cases where Kimi fails verification or exceeds scope.

Codex is not a second orchestrator. It receives the same immutable task contract as Kimi.

### 5.5 Claude Code — Independent Reviewer

Claude Code evaluates:

- whether the requested outcome was achieved;
- whether the implementation matches the change contract;
- whether protected areas or locked decisions were altered;
- whether unrelated files or behavior changed;
- whether regressions were introduced;
- whether tests and validation are adequate;
- whether security, data, permissions, or architecture risks were introduced;
- whether the builder's report matches the actual diff.

Claude must begin in **review-only mode**. It must not automatically rewrite the implementation during the initial review.

Claude reports findings to Hermes, not directly into the codebase.

### 5.6 Replit — Live Preview Environment

Replit is used for:

- live application preview;
- responsive and visual inspection;
- user-journey testing;
- runtime behavior checks;
- stakeholder demonstrations;
- rapid product feedback.

Replit is not an implementation authority and is not the source of truth.

**Direct code editing in Replit is prohibited by default.** Any emergency edit must be committed to the same GitHub task branch and reviewed through the normal workflow.

### 5.7 GitHub — Source of Truth

GitHub owns:

- protected branches;
- task branches;
- commits;
- pull requests;
- code diffs;
- review history;
- CI results;
- tags and releases;
- rollback capability.

No task is considered delivered until its code exists in a traceable GitHub commit.

---

## 6. Single-Writer Rule

To prevent agents from overwriting one another:

1. Each task has one assigned builder at a time.
2. The reviewer has read-only access during initial review.
3. Hermes does not modify the builder's working tree.
4. Replit does not create untracked product changes.
5. If a task is transferred from Kimi to Codex, Hermes records the transfer and baseline commit before Codex begins.
6. Parallel work must use separate branches or worktrees.
7. Two agents must never edit the same branch simultaneously.

Violation of the single-writer rule automatically pauses the task and requires branch reconciliation.

---

## 7. Required Project Control Files

Each repository should maintain:

```text
/docs/product/PRODUCT_SPEC.md
/docs/product/LOCKED_DECISIONS.md
/docs/product/FEATURE_DISPOSITION_REGISTER.md
/docs/design/DESIGN_SYSTEM.md
/docs/architecture/ARCHITECTURE_DECISIONS.md
/docs/engineering/AGENT_AUTHORITY.md
/docs/engineering/CONTROLLED_CHANGE_PROTOCOL.md
/docs/engineering/REGRESSION_REGISTER.md
/docs/engineering/VALIDATION_MATRIX.md
/docs/tasks/TASK-XXXX.md
```

These files are authoritative in the following order:

1. Explicit current instruction from Amjad;
2. Locked decisions and Feature Disposition Register;
3. Approved task contract;
4. Product specification and architecture decisions;
5. Design system;
6. Existing implementation;
7. Agent suggestions.

An agent suggestion never overrides an authoritative project decision.

---

## 8. Mandatory Task Record

Every task must have a unique task file:

```md
# TASK-XXXX — [Title]

Status:
Classification:
Risk level:
Requested by:
Orchestrator: Hermes
Builder:
Reviewer: Claude Code
Branch:
Worktree:
Baseline commit:
Current implementation commit:
Preview URL:

## Original Request

## Relevant Locked Decisions

## Objective

## In Scope

## Allowed Files

## Protected Areas

## Must Remain Unchanged

## Acceptance Criteria

## Required Validation

## Stop Conditions

## Baseline Results

## Builder Report

## Automated Verification

## Claude Review

## Approved Repair Findings

## Amjad Preview Feedback

## Final Validation

## Approval and Merge Record

## Rollback Method
```

The task record must be updated at each workflow state. It is the handoff packet between agents.

---

## 9. Mandatory Change Contract

Before any builder modifies code, Hermes must define:

```text
TASK
Redesign the quote review page without changing the quote workflow.

CLASSIFICATION
VISUAL_ONLY

RISK
MEDIUM — shared display components, protected pricing behavior

OBJECTIVE
Improve hierarchy, readability, spacing, and responsive behavior.

ALLOWED FILES
- app/quotes/[id]/review/page.tsx
- components/quotes/QuoteReviewHeader.tsx
- components/quotes/QuoteReviewTable.tsx

PROTECTED AREAS
- Pricing calculations
- Database schema
- Authentication
- Quote lifecycle
- Approval workflow
- API contracts
- Navigation structure
- Shared state shape

MUST REMAIN UNCHANGED
- Quote totals
- Existing approval states
- Request and response formats
- Permission rules
- Existing business logic
- Existing user journey

ACCEPTANCE CRITERIA
- Improved visual hierarchy
- No workflow or data changes
- Correct display at approved breakpoints
- Existing actions remain functional

REQUIRED VALIDATION
- Baseline checks recorded before editing
- Application builds successfully
- Existing tests pass
- Pricing regression tests pass
- Relevant user journey passes
- Desktop and mobile screenshots supplied
- Changed-file list supplied
- Explanation supplied for every changed file
- Final diff compared with baseline commit

STOP CONDITIONS
- Additional files appear necessary
- Existing architecture must change
- Business logic appears inconsistent
- Requirement conflicts with a locked decision
- Baseline is already failing in a relevant area
- Scope exceeds the approved change budget

When a stop condition occurs, do not silently expand the task. Return the issue to Hermes.
```

The builder must never independently decide that a broader redesign, workflow rewrite, schema change, or architecture change is required.

---

## 10. Task Classification

Hermes must classify every task as one primary type:

- `VISUAL_ONLY`
- `INTERACTION_ONLY`
- `BUG_FIX`
- `FEATURE`
- `REFACTOR`
- `BUSINESS_LOGIC`
- `DATA_MODEL`
- `INFRASTRUCTURE`
- `ARCHITECTURE`

### Special rule for `VISUAL_ONLY`

A visual task must state:

```text
This is a presentation-layer change.

Do not modify:
- business logic;
- workflow;
- APIs;
- database or schemas;
- state shape or state transitions;
- permissions;
- calculations;
- routes;
- event semantics.
```

Any necessary nonvisual change becomes a separate task requiring explicit approval.

---

## 11. Builder Routing

Default routing:

```text
New feature or broad multi-file implementation
→ Kimi K3

Large-context repository work
→ Kimi K3

Frontend plus backend vertical slice
→ Kimi K3

Controlled repository-wide refactor
→ Kimi K3

Small, precise bug fix
→ Codex

Highly sensitive existing behavior
→ Codex

Few-file visual or logic-preservation patch
→ Codex

Kimi fails the same validation twice
→ Stop, preserve evidence, and re-route repair to Codex

Kimi exceeds allowed scope
→ Reject implementation or revert to baseline; re-plan or route to Codex

High-risk architecture, permissions, pricing, or financial logic
→ Builder selected by Hermes; Claude review plus deterministic tests mandatory
```

Routing should later use measured builder scorecards rather than fixed assumptions alone.

---

## 12. End-to-End Workflow

### State 1 — Intake

Hermes receives the requested outcome and records the original wording without rewriting its meaning.

### State 2 — Context Retrieval

Hermes retrieves only relevant context:

- product specification;
- locked decisions;
- Feature Disposition Register;
- business rules;
- architecture decisions;
- design system;
- related regression entries;
- previous implementation attempts;
- repository structure.

Hermes must avoid flooding the builder with irrelevant historical context.

### State 3 — Baseline and Scope Lock

Before editing, Hermes and the builder record:

- current branch;
- clean or dirty working-tree status;
- baseline commit hash;
- existing uncommitted work;
- relevant build, lint, type-check, and test results;
- approved files and change budget.

The task cannot proceed on an ambiguous or unrecorded baseline.

### State 4 — Builder Assignment

Hermes assigns exactly one builder and creates an isolated branch or worktree.

Recommended branch naming:

```text
feature/TASK-XXXX-short-name
fix/TASK-XXXX-short-name
chore/TASK-XXXX-short-name
```

### State 5 — Implementation

The assigned builder must:

- inspect before editing;
- follow the allowed-file list;
- preserve protected areas;
- make the smallest sufficient change;
- avoid opportunistic refactoring;
- run required checks;
- document assumptions;
- declare incomplete work;
- commit coherent changes;
- provide a changed-file summary.

### State 6 — Scope Gate

Hermes or CI compares:

- allowed files versus actual changed files;
- baseline behavior versus new behavior;
- requested scope versus actual diff size;
- protected areas versus touched dependencies.

Unexpected file or behavior changes fail the scope gate.

### State 7 — Automated Verification

Run applicable checks:

- compilation or build;
- type checking;
- linting;
- unit tests;
- integration tests;
- end-to-end tests;
- business-rule fixtures;
- pricing and calculation fixtures;
- database migration validation;
- API contract validation;
- accessibility checks;
- UI screenshot or visual regression checks;
- dependency and security checks.

Results must be attached to the task record.

### State 8 — Independent Review

Claude Code reviews the committed implementation against:

- original request;
- approved change contract;
- locked decisions;
- baseline commit;
- implementation diff;
- validation evidence;
- regression register.

Findings must be classified as:

- `BLOCKER`
- `HIGH`
- `MEDIUM`
- `LOW`
- `OPTIONAL`
- `OUT_OF_SCOPE`
- `REQUIRES_PRODUCT_DECISION`

Claude must distinguish defects from optional redesign or refactoring preferences.

### State 9 — Finding Adjudication

Hermes evaluates every Claude finding and marks it:

- accepted and required;
- accepted but deferred;
- rejected as incorrect;
- rejected as out of scope;
- escalated to Amjad for a product decision.

The reviewer cannot directly expand the task.

### State 10 — Repair Cycle

The original builder receives only the accepted findings.

If the original builder caused repeated failures or uncontrolled scope expansion, Hermes may transfer the repair to Codex after recording the transfer baseline.

After every repair:

- automated checks rerun;
- scope gate reruns;
- relevant regression checks rerun;
- Claude verifies the accepted findings;
- new changes are reviewed for new regressions.

After two failed repair cycles on the same root problem, Hermes must stop the loop and re-plan or transfer the repair to Codex.

### State 11 — Replit Live Preview

Only a committed, verification-passing task branch may be promoted to Replit preview.

Replit must:

- pull the exact GitHub task branch or commit;
- use preview-only environment variables;
- use mock or isolated preview data where possible;
- never connect destructively to production systems;
- display the commit identifier in preview metadata where practical.

Amjad reviews:

- visual appearance;
- responsive behavior;
- user journey;
- product behavior;
- whether the requested outcome was achieved;
- whether previously approved behavior remains intact.

Feedback is returned to Hermes, not directly to multiple builders.

### State 12 — Final Validation

After preview feedback is resolved:

- all required automated checks rerun;
- Claude completes final review;
- preview points to the final candidate commit;
- rollback path is confirmed;
- task record is complete.

### State 13 — Approval, Merge, and Deploy

Only after validation, independent review, and Amjad's required approval may the task merge into a protected branch.

Production deployment must use the merged GitHub commit, not a Replit-only state.

---

## 13. Replit Environment Rules

1. GitHub remains authoritative.
2. Replit previews a named branch or exact commit.
3. Direct code edits are disabled or prohibited by policy.
4. Preview secrets are stored outside the repository.
5. Production credentials and production-write access are prohibited.
6. Preview databases must be isolated, disposable, or read-only.
7. Preview URLs must be recorded in the task file.
8. The preview must identify the branch or commit being shown.
9. A stale preview must never be presented as the latest implementation.
10. Preview environments should be archived or removed after merge.

Replit Agent must not independently redesign or modify the implementation unless explicitly assigned as a builder under a separate task contract.

---

## 14. Regression Protection

Hermes must maintain a project-level regression register.

Each entry should include:

```md
## REG-XXXX — [Issue]

First observed:
Affected task:
Affected files or systems:
User-visible symptom:
Root cause:
Fix applied:
Preventive test or validation:
Related locked decision:
Last verified:
```

Before related work begins, Hermes must retrieve relevant regression entries and include them in the task contract.

Each confirmed bug should receive one of:

- an automated regression test;
- a deterministic fixture;
- an API or schema contract test;
- a visual snapshot;
- a repeatable manual validation step.

A previously fixed issue is not considered protected until a repeatable check exists.

---

## 15. Preventing the Existing Problems

### 15.1 Repeating the Same Mistake

Required controls:

- regression register;
- root-cause record;
- linked preventive check;
- retrieval of related regressions before task assignment;
- failure history included in builder routing.

### 15.2 Changing Logic During Design Work

Required controls:

- `VISUAL_ONLY` task classification;
- explicit protected behavior;
- allowed-file list;
- state, API, schema, workflow, and calculation restrictions;
- diff-based scope gate;
- separate approval for any logic change.

### 15.3 Breaking Previously Fixed Issues

Required controls:

- baseline commit and baseline test evidence;
- relevant regression checks before and after editing;
- visual and end-to-end checks for shared components;
- final diff review;
- single-writer branch ownership.

### 15.4 Overediting

Required controls:

- smallest-sufficient-change rule;
- allowed-file list;
- explicit change budget;
- rejection of opportunistic refactoring;
- automatic failure for unexplained file changes;
- explanation for every changed file.

### 15.5 Agents Overwriting One Another

Required controls:

- one assigned builder;
- separate worktrees for parallel tasks;
- read-only initial review;
- no direct Replit edits;
- handoff commit before builder transfer;
- no simultaneous edits to the same branch.

---

## 16. Evidence-Driven Completion

Hermes must not mark a task complete because a builder says it is complete.

Completion requires evidence:

```text
✓ Original objective implemented
✓ Task contract unchanged or formally amended
✓ Baseline commit recorded
✓ Allowed-file scope respected
✓ Protected areas unchanged
✓ Build passed
✓ Type checks passed
✓ Required tests passed
✓ Relevant regression checks passed
✓ Claude blockers and accepted findings resolved
✓ Replit preview points to the final candidate commit
✓ Amjad approval recorded when required
✓ Changed-file summary supplied
✓ Known limitations disclosed
✓ Rollback path documented
```

The final report must contain:

- task ID and title;
- final commit;
- what changed;
- what did not change;
- files modified;
- test and validation evidence;
- Claude review result;
- preview location;
- known limitations;
- rollback method;
- decision required from Amjad, if any.

---

## 17. Builder Performance Tracking

Hermes should maintain separate Kimi and Codex scorecards.

Track:

- first-pass success rate;
- regression rate;
- scope-violation rate;
- unrelated files changed;
- review findings by severity;
- repair-cycle count;
- build failure rate;
- human acceptance rate;
- completion speed;
- average cost;
- performance by task classification;
- performance by repository or subsystem.

Routing should gradually adapt to actual project evidence.

A model that performs well on new feature development may still perform poorly on sensitive bug fixes. Scores should therefore be category-specific rather than based on one overall ranking.

---

## 18. Protected Branch and Environment Model

Recommended environments:

| Environment | Source | Purpose |
|---|---|---|
| Production | `main` or release tag | Live customer-facing system |
| Staging | `staging` or approved release candidate | Integrated pre-production testing |
| Replit preview | Task branch or exact commit | Live task-specific review |
| Builder worktree | Same task branch | Isolated implementation |
| Reviewer worktree | Same committed candidate, read-only initially | Independent review |

Recommended protections:

- no direct pushes to `main`;
- required CI checks;
- required review for protected systems;
- merge only from traceable task branches;
- release tags for production deployments;
- branch cleanup after merge;
- automatic backups or deployment rollback.

---

## 19. Conflict Resolution

When instructions or agents disagree, use this order:

1. Amjad's explicit current decision;
2. locked decisions and Feature Disposition Register;
3. approved task contract;
4. product and architecture specifications;
5. regression protections;
6. reviewer findings accepted by Hermes;
7. builder preferences.

If a conflict changes product behavior, business logic, architecture, permissions, pricing, or data, Hermes must escalate it to Amjad instead of resolving it silently.

---

## 20. Final Operating Summary

```text
Hermes
= one orchestrator and context authority

Kimi K3
= primary builder for substantial implementation

Codex
= precision builder, repair fallback, and challenger

Claude Code
= independent reviewer, initially read-only

GitHub
= single source of truth and rollback history

Replit
= live review of committed candidate code

Automated tests
= objective quality and regression gate

Amjad
= product owner and final approval authority
```

The governing rule is:

> **One orchestrator, one active builder, one independent reviewer, one source of truth, one live preview, and evidence before completion.**

This workflow is designed specifically to stop repeated mistakes, prevent design changes from altering logic, protect previously fixed behavior, and keep every implementation reversible and auditable.
