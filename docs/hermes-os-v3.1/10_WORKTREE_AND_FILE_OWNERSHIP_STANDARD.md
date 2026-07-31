# 10 — Worktree and File Ownership Standard

**Status:** SPECIFICATION (not yet implemented)
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 04_TASK_CONTRACT_STANDARD, 09_PARALLEL_EXECUTION_STANDARD
**Feeds into:** 18_EVIDENCE_AND_COMPLETION_STANDARD

---

## 1. Purpose

This document defines the Git worktree strategy that enforces the single-writer rule, file-ownership partitioning, and isolated agent workspaces. It covers worktree creation, naming conventions, base commits, synchronization, collision detection, ownership transfer, cleanup, and the absolute prohibition on sub-agent writes to the integration branch.

---

## 2. Core Principle: One Writer Per File

> **No two agents may write to the same file at the same time. No agent may write to a file owned by another active agent.**

This rule is enforced through:

1. **Worktree isolation**: Each agent works in its own Git worktree
2. **File-ownership assignment**: Each file is assigned to exactly one active agent
3. **Integration-branch prohibition**: Sub-agents never write to the shared integration branch
4. **Overlap detection**: Hermes verifies file-set disjointness before dispatch

---

## 3. Git Worktree Architecture

### 3.1 Worktree Model

```
Repository: /avoa-connect
│
├── main worktree (integration branch)
│   └── /avoa-connect/                    ← Hermes only
│
├── worktree: wt-task-0042-hermes
│   └── /avoa-connect-worktrees/wt-task-0042-hermes/  ← Hermes only
│
├── worktree: wt-task-0042-s1
│   └── /avoa-connect-worktrees/wt-task-0042-s1/      ← Agent A (Kimi K3)
│
├── worktree: wt-task-0042-s2
│   └── /avoa-connect-worktrees/wt-task-0042-s2/      ← Agent B (Codex)
│
├── worktree: wt-task-0042-review
│   └── /avoa-connect-worktrees/wt-task-0042-review/   ← Reviewer (read-only)
│
└── worktree: wt-task-0042-integration
    └── /avoa-connect-worktrees/wt-task-0042-integration/  ← Hermes integration
```

### 3.2 Worktree Directory Convention

All worktrees live under a single root:

```
<repository-root>-worktrees/
```

For AVOA Connect:

```
/Users/amjadthaufeeg/projects/avoa-connect-worktrees/
```

This keeps worktrees outside the main repository directory, preventing accidental commits and simplifying cleanup.

---

## 4. Naming Convention

### 4.1 Worktree Naming Schema

```
wt-<task_id>-<role>
```

| Component | Format | Example |
|---|---|---|
| Prefix | `wt-` | `wt-` |
| Task ID | `task-NNNN` | `task-0042` |
| Role | `hermes`, `s1`, `s2`, `review`, `integration`, `doc`, `test` | `s1` |

**Full examples:**

| Worktree Name | Purpose | Owner |
|---|---|---|
| `wt-task-0042-hermes` | Hermes working copy for contract drafting | Hermes |
| `wt-task-0042-s1` | Subtask 1 implementation | Kimi K3 |
| `wt-task-0042-s2` | Subtask 2 implementation | Codex |
| `wt-task-0042-review` | Read-only review worktree | Claude Code |
| `wt-task-0042-doc` | Documentation updates | Doc Agent |
| `wt-task-0042-test` | Test execution | Test Agent |
| `wt-task-0042-integration` | Integration and merge staging | Hermes |

### 4.2 Sequential Task Naming

For sequential (non-parallel) tasks, use:

```
wt-<task_id>-build
wt-<task_id>-review
wt-<task_id>-fix
```

---

## 5. Worktree Lifecycle

### 5.1 Creation

```bash
# Hermes creates a worktree for a task
git worktree add \
  /avoa-connect-worktrees/wt-task-0042-s1 \
  -b task/0042-s1-quote-header \
  <base-commit>
```

**Creation rules:**

1. Worktree is created from the **base commit** specified in the task contract
2. A new branch is created for the worktree (`task/<id>-<slug>`)
3. Branch name is derived from task ID and a short slug
4. Worktree directory path includes the full task ID for traceability
5. Only Hermes may create or remove worktrees

### 5.2 Base Commit Selection

| Scenario | Base Commit |
|---|---|
| First task on a fresh integration branch | `HEAD` of integration branch |
| Sequential task | `HEAD` of integration branch after previous task merged |
| Parallel subtask (independent) | Common parent commit from PEC dependency graph |
| Parallel subtask (dependent) | Commit where its dependency was integrated |
| Repair/correction cycle | Commit where builder submitted (not integration HEAD) |

### 5.3 Active Worktree Registry

Hermes maintains a registry of all active worktrees:

```yaml
worktree_registry:
  - worktree_id: "wt-task-0042-s1"
    path: "/avoa-connect-worktrees/wt-task-0042-s1"
    branch: "task/0042-s1-quote-header"
    base_commit: "abc1234"
    current_commit: null
    owner: "kimi-k3"
    task_id: "TASK-0042-S1"
    status: "ACTIVE"
    created_at: "2026-07-31T10:00:00Z"
    files_owned:
      - "components/quotes/QuoteReviewHeader.tsx"
      - "components/quotes/QuoteReviewHeader.test.tsx"

  - worktree_id: "wt-task-0042-review"
    path: "/avoa-connect-worktrees/wt-task-0042-review"
    branch: "task/0042-review"
    base_commit: "def5678"
    current_commit: null
    owner: "claude-code"
    task_id: "TASK-0042"
    status: "READ_ONLY"
    created_at: "2026-07-31T10:30:00Z"
    files_owned: []  # read-only, no write ownership
```

### 5.4 Synchronization

Before an agent begins work, Hermes must ensure the worktree is synchronized:

```bash
# In the worktree
cd /avoa-connect-worktrees/wt-task-0042-s1
git fetch origin
git reset --hard <base-commit>
```

**Synchronization rules:**

1. Worktree is always reset to its designated base commit before agent dispatch
2. Uncommitted changes in a worktree before dispatch indicate a protocol violation
3. Hermes verifies `git status --porcelain` returns empty before agent handoff
4. If dirty, Hermes stashes, records the stash, and resets

### 5.5 Cleanup

```bash
# After task closure
cd /avoa-connect
git worktree remove /avoa-connect-worktrees/wt-task-0042-s1
git branch -D task/0042-s1-quote-header  # if not merged
```

**Cleanup timing:**

| Worktree Type | Cleanup Trigger |
|---|---|
| Builder worktree | After task CLOSED + 7 days retention |
| Review worktree | After review findings accepted |
| Integration worktree | After merge to protected branch |
| Pilot worktree | After pilot report submitted |
| Failed/aborted | After root cause recorded (immediate) |

Worktrees must not be deleted until the task reaches `CLOSED` state, except for aborted tasks where the worktree is preserved for post-mortem.

---

## 6. File Ownership Model

### 6.1 Ownership Assignment

Every file in a task's allowed set must have exactly one owning agent at any time:

```yaml
file_ownership:
  "components/quotes/QuoteReviewHeader.tsx":
    owner: "kimi-k3"
    worktree: "wt-task-0042-s1"
    status: "WRITE"
    assigned_at: "2026-07-31T10:00:00Z"

  "components/quotes/QuoteReviewTable.tsx":
    owner: "codex"
    worktree: "wt-task-0042-s2"
    status: "WRITE"
    assigned_at: "2026-07-31T10:00:00Z"

  "components/quotes/QuoteReviewPage.tsx":
    owner: null  # not assigned to any agent
    worktree: null
    status: "PROTECTED"  # in protected zone, not editable
    assigned_at: null
```

### 6.2 Ownership Constraints

| Rule | Enforcement |
|---|---|
| One writer per file at any time | Overlap detection at dispatch + runtime checks |
| Ownership cannot be shared | Partition must be disjoint |
| Ownership must be explicit | Every allowed file must have an assigned owner |
| Ownership is time-bound | Ownership expires when agent submits or task completes |

### 6.3 Overlapping-Path Detection

Before dispatching any agent, Hermes runs full-path and glob-level overlap detection:

```python
def detect_overlapping_paths(assignments: dict) -> list[Overlap]:
    overlaps = []

    for file_a, owner_a in assignments.items():
        for file_b, owner_b in assignments.items():
            if owner_a.agent == owner_b.agent:
                continue
            if paths_overlap(file_a, file_b):
                overlaps.append(Overlap(
                    file_a=file_a, owner_a=owner_a.agent,
                    file_b=file_b, owner_b=owner_b.agent
                ))

    return overlaps

def paths_overlap(path_a: str, path_b: str) -> bool:
    # Exact match
    if path_a == path_b:
        return True
    # Glob match: one is a glob pattern that includes the other
    if is_glob(path_a) and glob_matches(path_a, path_b):
        return True
    if is_glob(path_b) and glob_matches(path_b, path_a):
        return True
    # Parent directory match
    if is_parent_directory(path_a, path_b):
        return True
    return False
```

### 6.4 Glob Conflict Rules

| Pattern A | Pattern B | Conflict? |
|---|---|---|
| `components/quotes/*.tsx` | `components/quotes/Header.tsx` | **YES** — glob includes specific file |
| `components/quotes/header/*` | `components/quotes/table/*` | No |
| `lib/**/*.ts` | `lib/pricing/engine.ts` | **YES** — glob includes specific file |
| `app/quotes/**` | `app/admin/**` | No |
| `styles/*.css` | `styles/quotes.css` | **YES** |
| `*.config.ts` | `vite.config.ts` | **YES** |

### 6.5 Ownership Transfer

When a task transfers from one agent to another (e.g., Kimi → Codex for repair):

```
1. Current owner commits all work
2. Current owner pushes branch
3. Hermes records current commit as transfer point
4. Hermes releases ownership from current owner
5. Hermes assigns ownership to new owner
6. New owner receives worktree at recorded commit
7. New owner's task contract lists only files requiring repair
```

Ownership transfer must be an explicit Hermes operation, never an agent-to-agent handoff.

---

## 7. Shared Files

### 7.1 Definition

A shared file is one that genuinely requires changes from multiple subtasks and cannot be cleanly partitioned. Shared files indicate a decomposition failure.

### 7.2 Shared-File Protocol

If a shared file is unavoidable:

1. **Do not parallelize.** Mark the parent task as sequential.
2. If parallelism is critical:
   - Assign the shared file to the **first** subtask in the dependency chain
   - All dependent subtasks list it as `read_only_reference`
   - Dependent subtasks must not modify the shared file; they read it for context only
   - If dependent subtasks discover they need to modify the shared file, they must stop and escalate to Hermes

### 7.3 Read-Only References

A subtask may reference files it does not own:

```yaml
subtask_id: "TASK-0042-S3"
allowed_files: ["components/quotes/QuoteReviewFooter.tsx"]
read_only_references:
  - "components/quotes/QuoteReviewHeader.tsx"  # owned by S1, read for context
  - "lib/types/quote.ts"                       # shared types, read-only
```

Read-only references are for context only. Modifying a read-only reference is a scope violation.

---

## 8. Integration Branch Protocol

### 8.1 Absolute Prohibition

> **Sub-agents must never write to the integration branch.**

The integration branch is Hermes's exclusive domain. Any sub-agent write to the integration branch is a protocol violation that must:

1. Immediately halt all active agents
2. Trigger a repository audit
3. Require explicit Hermes remediation before work resumes
4. Be recorded as a violation on the offending agent's scorecard

### 8.2 Integration Branch Hierarchy

```
main (protected)
  │
  └── integration/hermes-os-v3.1  ← Hermes only
        │
        ├── task/0041-user-dashboard (merged ✅)
        ├── task/0042-quote-redesign (in progress)
        │     ├── task/0042-s1-quote-header (agent worktree)
        │     └── task/0042-s2-quote-table (agent worktree)
        └── task/0043-fix-pricing (pending)
```

### 8.3 Merge Protocol

Only Hermes merges into the integration branch:

```
1. Agent submits work → pushes to task branch
2. Agent notifies Hermes: "IMPLEMENTATION_SUBMITTED"
3. Hermes verifies:
   - Branch is ahead of base commit
   - Changed files match allowed set
   - No protected zone files modified
   - Tests pass on agent branch
4. Hermes merges agent branch into integration branch
   - Fast-forward if clean
   - Hermes resolves trivial conflicts (formatting, imports)
   - Returns to agent if conflicts are structural
5. Hermes runs integration tests
6. Hermes updates task state
```

### 8.4 Kimi K3 as Integration Owner

Kimi K3 has a special role as the **designated integration owner** for tasks where it is the primary builder. This means:

- Kimi K3 is the first agent whose work is merged into the integration branch
- Subsequent agents rebase onto Kimi's merged work
- If Kimi's work introduces issues that cascade, Kimi is responsible for the first correction cycle
- This role is per-task, not global — Codex may be integration owner for tasks where it is the primary builder

**This does not mean Kimi writes to the integration branch directly.** Kimi still works in its own worktree. Hermes still performs the merge. Kimi is the "owner" in the sense that its work forms the base that other agents build upon.

---

## 9. Collision Detection

### 9.1 Runtime Collision Detection

During parallel execution, Hermes must detect collisions:

```python
def detect_runtime_collisions(active_agents: list) -> list[Collision]:
    collisions = []
    for i, agent_a in enumerate(active_agents):
        for agent_b in active_agents[i+1:]:
            # Check if any agent's actual changes overlap another's owned files
            a_actual_files = get_actual_changed_files(agent_a.worktree)
            b_owned_files = agent_b.owned_files

            overlap = set(a_actual_files) & set(b_owned_files)
            if overlap:
                collisions.append(Collision(
                    agent_a=agent_a.id,
                    agent_b=agent_b.id,
                    overlapping_files=list(overlap),
                    severity="BLOCKER"
                ))

    return collisions
```

### 9.2 Collision Response

| Collision Type | Response |
|---|---|
| Agent modifies file owned by another active agent | **Immediate abort** of offending agent; pause sibling |
| Agent creates new file in another agent's owned folder | **Stop and re-scope**; Hermes determines owner |
| Agent modifies a protected zone file | **Immediate abort of entire group** |
| Agent modifies file not in any allowed set | **Stop agent**; Hermes determines if scope expansion is warranted |

---

## 10. Worktree Permissions

### 10.1 Agent Access Matrix

| Agent Role | Own Worktree | Other Worktrees | Integration Branch | Main Branch |
|---|---|---|---|---|
| Hermes | Read/Write | Read/Write (admin) | Read/Write | Read only |
| Kimi K3 (builder) | Read/Write | Read only | Read only | Read only |
| Codex (builder) | Read/Write | Read only | Read only | Read only |
| Claude Code (reviewer) | Read only | Read only | Read only | Read only |
| Scout Agent (pilot) | Read only | Read only | Read only | Read only |
| Test Agent (pilot) | Read only | Read only | Read only | Read only |
| Doc Agent (pilot) | Read/Write (docs only) | Read only | Read only | Read only |
| Visual QA (pilot) | Read only | Read only | Read only | Read only |

### 10.2 Enforcement

Worktree permissions are enforced through:

1. **Prompt-level**: Agent system prompts include explicit worktree boundaries
2. **Git-level**: Branch protection rules on integration and main branches
3. **Filesystem-level** (future): Directory permissions on worktree paths
4. **CI-level** (future): Pre-push hooks that verify file ownership

---

## 11. Worktree State Machine

```
                 ┌─────────┐
                 │ ALLOCATED│ ← Hermes creates worktree, assigns to task
                 └────┬─────┘
                      │
                      ▼
                 ┌─────────┐
                 │ PREPPED │ ← Base commit checked out, verified clean
                 └────┬─────┘
                      │
                      ▼
                 ┌─────────┐
                 │ ACTIVE  │ ← Agent dispatched, working
                 └────┬─────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │SUBMITTED│ │ PAUSED  │ │ ABORTED │
     └────┬─────┘ └────┬─────┘ └────┬─────┘
          │           │           │
          ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │ MERGED  │ │ ACTIVE  │ │ARCHIVED │
     └────┬─────┘ └─────────┘ └─────────┘
          │
          ▼
     ┌─────────┐
     │ARCHIVED │ ← 7 days after task CLOSED
     └─────────┘
```

**State transitions are controlled by Hermes only.** Agents must not change their worktree state.

---

## 12. Cleanup and Retention

### 12.1 Retention Policy

| Worktree Status | Retention Period | Action After |
|---|---|---|
| ACTIVE | Until task state changes | — |
| SUBMITTED | Until merged or task closed | Merge or discard |
| MERGED | 7 days after task CLOSED | Remove worktree, delete branch |
| PAUSED | Until resumed or 24h timeout | Resume or abort |
| ABORTED | 30 days (for post-mortem) | Archive then remove |
| ARCHIVED | 90 days | Permanent deletion |

### 12.2 Cleanup Command

```bash
# Hermes runs after retention period
cd /avoa-connect
git worktree remove /avoa-connect-worktrees/wt-task-0042-s1 --force
git branch -D task/0042-s1-quote-header

# Verify cleanup
git worktree list
# Should no longer show the removed worktree
```

### 12.3 Orphaned Worktree Detection

Hermes must periodically scan for orphaned worktrees:

```bash
# List all worktrees
git worktree list

# Cross-reference with active task registry
# Any worktree not in the active registry is orphaned
```

Orphaned worktrees (from crashed agents, interrupted sessions) must be investigated before removal.

---

## 13. Cross-References

| Reference | Document |
|---|---|
| Parallel execution controller | `09_PARALLEL_EXECUTION_STANDARD.md` |
| Task contract file ownership | `04_TASK_CONTRACT_STANDARD.md` |
| Protected zones | `08_PROTECTED_ZONES_AND_SCOPE_CONTROL.md` |
| Evidence packages | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` |
| Builder routing and scorecards | `19_AGENT_ROUTING_AND_SCORECARDS.md` |
| Rollback safety (baseline commits) | `20_ROLLBACK_AND_DEPLOYMENT_SAFETY.md` |

---

*Version 3.1 — Specification. Part of Hermes Engineering OS v3.1. Awaiting implementation authorization.*