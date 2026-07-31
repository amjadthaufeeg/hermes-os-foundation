# 09 — Parallel Execution Standard

**Status:** SPECIFICATION (not yet implemented)
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 04_TASK_CONTRACT_STANDARD, 07_RISK_CLASSIFICATION, 08_PROTECTED_ZONES_AND_SCOPE_CONTROL
**Feeds into:** 10_WORKTREE_AND_FILE_OWNERSHIP_STANDARD, 19_AGENT_ROUTING_AND_SCORECARDS

---

## 1. Purpose

This document defines when and how Hermes may execute multiple tasks in parallel. It establishes the Parallel Execution Controller (PEC), eligibility rules, decomposition standards, subtask contracts, dependency graphs, file-ownership partitioning, agent tracking, evidence collection, integration protocol, and cleanup requirements.

Parallel execution is a **privilege**, not a default. Hermes must prove each candidate task is safe to parallelize before authorizing concurrent work.

---

## 2. Controller Model

### 2.1 The Parallel Execution Controller (PEC)

The PEC is a **subsystem of Hermes**, not a separate agent. It operates subordinate to Hermes's orchestration authority and may never override Hermes's scope, risk, or routing decisions.

```
                            HERMES
               Sole Orchestrator
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
     Task Intake    PEC Subsystem   Agent Router
                    (parallelism
                     eligibility,
                     decomposition,
                     dependency mgmt)
```

**PEC responsibilities:**

| Responsibility | Description |
|---|---|
| Eligibility screening | Determine whether a task qualifies for parallel execution |
| Decomposition | Split eligible tasks into non-overlapping subtasks |
| Dependency graph | Model and enforce subtask ordering constraints |
| File-ownership partitioning | Assign disjoint file sets to each parallel agent |
| Worktree allocation | Reserve worktrees for each parallel subtask (see Doc 10) |
| Agent tracking | Monitor parallel agent progress and evidence |
| Integration sequencing | Define merge order and integration gates |
| Abort and cleanup | Halt parallel work on violation and restore clean state |

### 2.2 Controller Subordination

The PEC must not:

- Override Hermes's risk classification
- Authorize parallelism on tasks Hermes has classified as sequential-only
- Allocate write access to protected zones without explicit Hermes unlock
- Allow agents to coordinate directly with each other (all communication flows through Hermes)
- Merge parallel results without Hermes integration approval

---

## 3. Parallelism Eligibility

### 3.1 Hard Eligibility Gates

A task is **ineligible** for parallel execution if **any** of the following are true:

| Gate | Condition | Rationale |
|---|---|---|
| P1 | Risk level R4 or R5 | Critical/commercial work must be sequential and closely monitored |
| P2 | Task touches a protected zone | Protected zones require sequential authorization |
| P3 | Task has database migrations | Schema changes must be serialized |
| P4 | Task modifies shared infrastructure config | Infrastructure changes are globally scoped |
| P5 | Task modifies the integration branch directly | Never permitted (see Doc 10) |
| P6 | Fewer than 3 truly independent subtasks exist | Overhead exceeds benefit for insufficient parallelism |
| P7 | Any subtask would have zero files in its allowed set | Empty work allocation is a decomposition error |

### 3.2 Soft Eligibility Criteria

Even when hard gates pass, Hermes must evaluate soft criteria before authorizing parallelism:

| Criterion | Weight | Assessment |
|---|---|---|
| File-set disjointness | **MANDATORY** | Subtask allowed-file sets must have zero overlap |
| Folder-level separation | Strong preference | Subtasks should operate in different top-level folders |
| Test independence | Required | Subtask test suites must not interfere with each other |
| Build independence | Preferred | Subtasks should not require sequential builds |
| Risk homogeneity | Preferred | Parallel subtasks should be at similar risk levels |
| Agent availability | Practical | Enough agents must be available without contention |

### 3.3 Sequential-Only Tasks

The following task types are **always sequential**, regardless of decomposition attempts:

- R4 and R5 risk-level tasks
- Database schema changes
- Authentication and permission changes
- API contract changes
- Shared-library modifications used by all other subtasks
- Infrastructure-as-code changes
- Monorepo-wide refactoring
- Tasks where the dependency graph forms a single linear chain

---

## 4. Decomposition Protocol

### 4.1 Subtask Contract Schema

Every subtask inherits from the parent task contract and adds parallelism-specific fields:

```yaml
subtask_id: "TASK-0042-S1"
parent_task_id: "TASK-0042"
title: "Redesign quote header component"
risk_level: R1  # must be ≤ parent risk level

# Inherited from parent
objective: "Improve visual hierarchy of quote review header"
context_required: ["DESIGN_SYSTEM.md", "component tree"]

# Parallelism-specific
parallel_group: "pg-042"
dependency: []  # subtask IDs this one depends on
depends_on_completion_of: []

# File ownership (disjoint from sibling subtasks)
allowed_files:
  - "components/quotes/QuoteReviewHeader.tsx"
  - "components/quotes/QuoteReviewHeader.test.tsx"
allowed_folders:
  - "components/quotes/__tests__/__snapshots__/"

protected_areas:  # inherited from parent
  - "app/quotes/[id]/review/"

must_not_change:
  - "Quote totals calculation"
  - "Approval state machine"
  - "API request/response shapes"

change_budget:
  max_files: 3
  max_lines_changed: 200

# Own acceptance criteria
acceptance_criteria:
  - "Header matches new design system tokens"
  - "Responsive at 3 approved breakpoints"
  - "Existing header tests pass or are updated"

# Parallel-specific
required_evidence:
  - "Desktop + tablet + mobile screenshots"
  - "Changed-file list"
  - "Test results"

builder: "kimi-k3"
worktree: "wt-task-0042-s1"  # allocated by Hermes
base_commit: "abc1234"       # from parent task

stop_conditions:
  - "Any file outside allowed set requires change"
  - "Header change cascades to quote-calculation logic"
  - "Integration with sibling subtask fails"
```

### 4.2 Decomposition Rules

1. **Non-overlapping file sets**: Every file in the parent's allowed set must be assigned to exactly one subtask. No file may appear in two subtask contracts.

2. **Folder-level preference**: When possible, subtasks should own entire folders rather than individual files within a shared folder.

3. **Test file co-location**: A subtask that modifies `Component.tsx` must also own `Component.test.tsx` and related test fixtures.

4. **Shared-file prohibition**: If a file genuinely requires changes from two subtasks, the tasks are not parallelizable. Re-decompose or mark sequential.

5. **Max 8 parallel subtasks**: More than 8 parallel agents introduces coordination overhead that typically exceeds throughput gain.

6. **Min 3 parallel subtasks**: Fewer than 3 independent workstreams does not justify PEC overhead.

### 4.3 Dependency Graph

Hermes must model subtask dependencies as a directed acyclic graph (DAG):

```yaml
parallel_group: "pg-042"
dependency_graph:
  TASK-0042-S1: []
  TASK-0042-S2: []
  TASK-0042-S3: [TASK-0042-S1]  # S3 depends on S1's completion
  TASK-0042-S4: [TASK-0042-S1, TASK-0042-S2]  # S4 depends on S1 and S2
```

**Dependency types:**

| Type | Example | Rule |
|---|---|---|
| None | Independent subtasks | Execute in any order or concurrently |
| Hard | S3 must not start until S1 is integrated | Block S3 dispatch until S1 passes integration |
| Soft | S4 works better after S2, but can start | Dispatch S4; warn if S2 not yet integrated |

Cycles in the dependency graph are **invalid** and must block the entire parallel group.

---

## 5. File Ownership in Parallel Execution

### 5.1 Disjoint Partition Requirement

The file-ownership partition is the **primary safety mechanism** for parallel execution. It must be verified before any agent is dispatched:

```
Parent allowed files:  [A, B, C, D, E, F, G, H]
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     Subtask S1     Subtask S2     Subtask S3
     [A, B, C]      [D, E, F]      [G, H]
```

The partition is valid only if:

```
S1 ∩ S2 = ∅
S1 ∩ S3 = ∅
S2 ∩ S3 = ∅
S1 ∪ S2 ∪ S3 = parent allowed set
```

### 5.2 Overlap Detection

Before dispatching any parallel agent, Hermes must run overlap detection:

```python
def detect_overlap(subtask_contracts: list) -> list[Conflict]:
    conflicts = []
    for i, s1 in enumerate(subtask_contracts):
        for s2 in subtask_contracts[i+1:]:
            overlapping = set(s1.allowed_files) & set(s2.allowed_files)
            if overlapping:
                conflicts.append(Conflict(
                    subtask_a=s1.id,
                    subtask_b=s2.id,
                    overlapping_files=list(overlapping)
                ))
    return conflicts
```

**Any detected overlap blocks parallel dispatch.** Hermes must re-decompose or fall back to sequential execution.

### 5.3 Glob Conflict Detection

Beyond exact file-path matching, Hermes must detect glob-level conflicts:

| Subtask A owns | Subtask B owns | Conflict? |
|---|---|---|
| `components/quotes/*` | `components/quotes/ReviewHeader.tsx` | **YES** — glob includes the specific file |
| `components/quotes/header/*` | `components/quotes/table/*` | No — folder-level separation |
| `lib/pricing/*.ts` | `lib/pricing/__tests__/*` | No — test/impl separation acceptable if tests are independent |
| `app/**/page.tsx` | `app/quotes/page.tsx` | **YES** — glob includes the specific file |

---

## 6. Pilot Roles (Read-Only Parallel Agents)

Hermes may dispatch **read-only pilot agents** alongside an active builder. These agents do not write code and do not require file-ownership partitioning.

### 6.1 Permitted Pilot Roles

| Role | Access | Purpose | Dispatch Rule |
|---|---|---|---|
| **Scout Agent** | Read-only, full repo | Pre-research codebase for context before builder starts | Dispatch before builder; terminate before builder begins |
| **Test Agent** | Read-only + test execution | Run existing test suites and report baseline results | Dispatch in parallel with builder; test results feed into automated gates |
| **Doc Agent** | Read-only + doc files only | Update documentation, changelogs, task records | Dispatch in parallel; doc files must be disjoint from builder's allowed set |
| **Visual QA Agent** | Read-only + screenshot capture | Capture before/after screenshots, run visual regression | Dispatch after builder submits; review-only, no code modification |

### 6.2 Pilot Agent Constraints

- Pilot agents must never write to any file in the builder's allowed set
- Pilot agents must never modify source code, configuration, or dependencies
- Pilot agent findings flow to Hermes, not directly to the builder
- A pilot agent exceeding its read-only scope must be terminated immediately

### 6.3 Scout Agent Protocol

```
1. Hermes creates scout subtask with:
   - Read-only access to entire repository
   - Specific research questions
   - Time budget (max 5 minutes)
2. Scout searches, reads, and reports findings to Hermes
3. Hermes incorporates scout findings into builder's task contract
4. Scout terminates before builder dispatch
5. Scout must not cache or persist state that influences builder
```

### 6.4 Test Agent Protocol

```
1. Hermes dispatches test agent with:
   - The test suite relevant to the builder's allowed files
   - Baseline commit identifier
2. Test agent runs tests and reports:
   - Pass/fail counts
   - Specific failing tests with stack traces
   - Coverage delta from baseline
3. Hermes records baseline results before builder starts
4. Test agent re-runs after builder submission for comparison
```

### 6.5 Doc Agent Protocol

```
1. Hermes assigns doc agent a disjoint file set:
   - README.md, CHANGELOG.md, docs/*.md
   - Must not overlap builder's allowed source files
2. Doc agent updates documentation in parallel with builder
3. Doc agent commits to its own worktree
4. Integration merges doc changes after builder verification
```

---

## 7. Agent Tracking

### 7.1 Parallel Agent Registry

Hermes must maintain a live registry of all active parallel agents:

```yaml
parallel_group: "pg-042"
status: "IN_PROGRESS"
agents:
  - subtask_id: "TASK-0042-S1"
    agent: "kimi-k3"
    worktree: "wt-task-0042-s1"
    status: "BUILDING"
    started_at: "2026-07-31T10:00:00Z"
    last_heartbeat: "2026-07-31T10:15:00Z"
    files_touched: ["components/quotes/QuoteReviewHeader.tsx"]

  - subtask_id: "TASK-0042-S2"
    agent: "codex"
    worktree: "wt-task-0042-s2"
    status: "IMPLEMENTATION_SUBMITTED"
    started_at: "2026-07-31T10:00:00Z"
    submitted_at: "2026-07-31T10:20:00Z"
    files_touched: ["components/quotes/QuoteReviewTable.tsx"]

  - subtask_id: "TASK-0042-S3"
    agent: "kimi-k3"
    worktree: "wt-task-0042-s3"
    status: "BLOCKED"
    depends_on: ["TASK-0042-S1"]
    blocked_reason: "Awaiting S1 integration"
```

### 7.2 Heartbeat Monitoring

- Every parallel agent must report a heartbeat at least every 5 minutes
- An agent silent for >10 minutes triggers Hermes investigation
- An agent silent for >30 minutes triggers automatic pause of the parallel group

### 7.3 Progress Tracking

Hermes tracks per-agent progress, not aggregate percentages:

```
✅ TASK-0042-S1: Implementation submitted, awaiting review
✅ TASK-0042-S2: Implementation submitted, review in progress
⏳ TASK-0042-S3: Blocked on S1 completion
🔄 TASK-0042-S4: Building (estimated 15 min remaining)
```

Do not report "Parallel group 75% complete." Report per-subtask status.

---

## 8. Evidence Collection in Parallel Mode

### 8.1 Per-Subtask Evidence

Each subtask produces its own evidence package before integration:

```yaml
subtask_id: "TASK-0042-S1"
evidence:
  diff: "diff-s1.patch"
  build_result: "PASS"
  test_results: "12 passed, 0 failed"
  screenshots: ["desktop-s1.png", "tablet-s1.png", "mobile-s1.png"]
  changed_files: ["components/quotes/QuoteReviewHeader.tsx"]
  builder_report: "Header redesigned per design tokens..."
```

### 8.2 Integration Evidence

After all subtasks submit, Hermes collects integration evidence:

```yaml
parallel_group: "pg-042"
integration_evidence:
  merge_result: "CLEAN" | "CONFLICT"
  conflict_files: []
  integration_build: "PASS" | "FAIL"
  integration_tests: "45 passed, 0 failed"
  cross_subtask_regression: "NONE_DETECTED"
  full_diff: "diff-integrated.patch"
```

### 8.3 Evidence Hierarchy

```
Individual subtask evidence
        │
        ▼
   Integration evidence
        │
        ▼
   Complete task evidence package → Hermes review → Amjad approval
```

---

## 9. Integration Protocol

### 9.1 Integration Sequencing

Integration must follow the dependency graph's topological order:

```
1. Complete all dependency-free subtasks (leaf nodes in DAG)
2. Integrate leaf subtasks into integration branch
3. Run integration tests
4. Unblock dependent subtasks
5. Dependent subtasks rebase onto integration branch
6. Complete dependent subtasks
7. Integrate all remaining subtasks
8. Run full integration suite
9. Produce unified evidence package
```

### 9.2 Conflict Resolution

If integration produces merge conflicts:

1. Hermes pauses all parallel agents
2. Hermes identifies conflicting files and responsible subtasks
3. Hermes determines root cause (overlap detection failure, unapproved scope expansion, etc.)
4. Hermes either:
   - Resolves trivial conflicts (import ordering, formatting) directly
   - Returns conflicts to the relevant builder for resolution
   - Aborts parallelism and restarts sequentially if conflicts are structural
5. Hermes records the conflict and resolution in the task record

### 9.3 Integration Gate

The integration gate must pass before Hermes can mark the parent task ready for review:

| Gate | Requirement |
|---|---|
| Merge clean | No unresolved conflicts |
| Build | Integration branch builds successfully |
| All tests | Combined test suite passes |
| No regression | No previously passing test now fails |
| File budget | Total changed files ≤ parent change budget |
| Protected zones | No protected files modified |
| Cross-subtask | No conflicting behavior between subtasks |

---

## 10. Abort and Cleanup

### 10.1 Automatic Abort Conditions

Parallel execution must abort automatically when:

| Condition | Action |
|---|---|
| Any agent exceeds its allowed file set | Abort that agent; assess impact on group |
| Any agent touches a protected zone | Abort entire parallel group immediately |
| Overlap detected mid-execution | Pause all agents; revalidate partition |
| Agent silent >30 minutes | Pause that agent's subtask; investigate |
| Integration merge produces conflicts >5 files | Abort parallelism; restart sequentially |
| Integration tests fail | Block integration; investigate per-subtask |

### 10.2 Cleanup Protocol

On abort or completion:

```
1. Collect all agent outputs and evidence
2. Archive worktrees (do not delete until task is CLOSED)
3. Record integration outcome in task record
4. Release worktree allocations
5. Update agent scorecards with parallel performance data
6. Restore repository to clean state (integration branch only)
```

### 10.3 Abort Decision Authority

Only Hermes may decide to abort a parallel group. Individual agents must not:

- Unilaterally abort their siblings
- Attempt to resolve another agent's failures
- Merge their work around a failed sibling

---

## 11. Prohibited Actions

The following actions are **strictly prohibited** during parallel execution:

| Prohibition | Enforcement |
|---|---|
| Agents communicating directly with each other | Prompt-enforced + Hermes as sole router |
| Agents modifying another agent's worktree | Worktree permissions (see Doc 10) |
| Agents expanding scope to cover sibling's files | Scope-exceeded detection |
| Agents merging their own work into integration branch | Hermes-only merge authority |
| Hermes delegating PEC decisions to any agent | Hermes must own all PEC decisions |
| Parallel work on R4/R5 tasks | Hard block in eligibility screening |
| Parallel work with overlapping file sets | Overlap detection must block dispatch |
| Simultaneous writes to the same branch | Worktree enforcement (see Doc 10) |

---

## 12. Release Mapping

| Release | Parallelism Capability | Agent Count |
|---|---|---|
| HOS-1 to HOS-4 | Sequential only | 1 builder at a time |
| HOS-5 | Read-only pilot agents (scout, test, doc) | 1 builder + up to 3 pilots |
| HOS-6 | Controlled UI parallelism (R1 tasks only) | Up to 3 parallel builders |
| HOS-7 | Expanded specialist parallelism (R1-R2) | Up to 5 parallel builders |
| HOS-8 | Full parallel orchestration (R1-R3) | Up to 8 parallel builders |

---

## 13. Cross-References

| Reference | Document |
|---|---|
| Task contract schema | `04_TASK_CONTRACT_STANDARD.md` |
| Risk classification (R1-R5) | `07_RISK_CLASSIFICATION.md` |
| Protected zones | `08_PROTECTED_ZONES_AND_SCOPE_CONTROL.md` |
| Worktree management | `10_WORKTREE_AND_FILE_OWNERSHIP_STANDARD.md` |
| Agent scorecards | `19_AGENT_ROUTING_AND_SCORECARDS.md` |
| Evidence standards | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` |

---

*Version 3.1 — Specification. Part of Hermes Engineering OS v3.1. Awaiting implementation authorization.*