# 22 — Command Center Information Architecture

**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 21 (Command Center PRD)
**Feeds into:** 23 (Command Center Data Model)

---

## 1. Purpose

This document defines the information architecture of the Hermes Command Center: the module hierarchy, navigation structure, user flows for key operational tasks, empty state designs, alert patterns, and the dashboard layout concept.

It does **not** define visual design (colors, typography, spacing), component library choices, or implementation technology. It defines what information lives where, how users move through it, and what they see when there's nothing to show.

---

## 2. Module Structure

### 2.1 Module Hierarchy

```
Hermes Command Center
│
├── 1. Executive Overview           ← Landing / default view
│
├── 2. Portfolio                    ← Project & release planning
│   ├── Project List
│   ├── Project Detail
│   │   ├── Release Timeline
│   │   ├── Task Distribution
│   │   └── Risk Breakdown
│   └── Release Detail
│       ├── Task List
│       └── Deployment History
│
├── 3. Product                      ← Task management
│   ├── Task List (filterable)
│   └── Task Detail
│       ├── Contract Tab
│       ├── State History Tab
│       ├── Evidence Tab
│       ├── Findings Tab
│       └── Relationships Tab (subtasks, parent, decisions, regressions)
│
├── 4. Design Studio                ← Design operations
│   ├── Design Briefs
│   ├── UI Contracts
│   ├── Design Artifacts
│   ├── Design Reviews
│   ├── Visual Findings
│   ├── Design System
│   │   ├── Version History
│   │   ├── Component Catalog
│   │   └── Token Explorer
│   └── Accessibility
│       ├── Component Results
│       └── Page-Level Audits
│
├── 5. Engineering Mission Control  ← Real-time engineering operations
│   ├── Active Tasks Dashboard
│   │   ├── Parent Tasks
│   │   ├── Subtasks
│   │   └── Blocked Tasks
│   ├── Agent Runs
│   │   ├── Active Agents
│   │   └── Agent Detail (scorecard, history, current worktree)
│   ├── Worktrees
│   ├── File Ownership Map
│   ├── Dependencies Graph
│   ├── Collisions
│   ├── Validation
│   │   ├── Build Results
│   │   ├── Test Results
│   │   └── Gate Status
│   ├── Review Queue
│   │   ├── Pending Reviews
│   │   ├── Findings by Severity
│   │   └── Finding Decisions
│   ├── Integration
│   └── Rollback & Deploy
│
├── 6. Quality and Evidence         ← Quality metrics and trends
│   ├── Gate Dashboard
│   ├── Review Trends
│   ├── Test Coverage
│   ├── Security Scans
│   └── Performance Benchmarks
│
├── 7. Commercial Safety            ← Amjad-exclusive
│   ├── Commercial Task Monitor
│   ├── Pricing Change Log
│   ├── Business Fixtures
│   └── Protected Zone Status
│
├── 8. Knowledge                    ← Decisions, regressions, patterns
│   ├── Decision Register
│   ├── Regression Register
│   ├── Pattern Library
│   ├── Documentation Index
│   └── Research Notes
│
├── 9. Releases                     ← Release management
│   ├── Release Calendar
│   ├── Release Detail
│   │   ├── Task Readiness
│   │   └── Deployment History
│   ├── Feature Flags
│   └── Rollback History
│
└── 10. Operations                  ← System and fleet health
    ├── Agent Fleet Status
    ├── CI/CD Pipeline Monitor
    ├── Deployment Target Health
    ├── Incident Log
    ├── Cost Tracker
    └── Rate Limit Monitor
```

### 2.2 Navigation Model

**Primary Navigation:** Left sidebar with the 10 modules as top-level items. Each module item shows a badge count when there are actionable items:

| Module | Badge Content |
|---|---|
| Executive Overview | Count of tasks needing Amjad approval |
| Portfolio | Count of active projects |
| Product | Count of tasks in non-terminal states |
| Design Studio | Count of unreviewed design briefs + unresolved visual findings |
| Engineering Mission Control | Count of active agent runs + blocked tasks + unresolved blocker findings |
| Quality and Evidence | Count of failed gates in last 24h |
| Commercial Safety | Count of R4 commercial tasks (Amjad only) |
| Knowledge | Count of proposed decisions awaiting ratification |
| Releases | Count of releases approaching target date |
| Operations | Count of active incidents + offline agents |

**Secondary Navigation:** Within each module, horizontal tabs or a secondary sidebar for sub-sections.

**Breadcrumb trail:** Always visible. Format: `Command Center > Module > Section > Entity`

**Global elements (always visible):**
- Search bar (top)
- Alert bell (top-right, with count of unacknowledged critical alerts)
- Current user identity (top-right)
- Data freshness indicator (top-right: "Live" / "Stale (>60s)" / "Disconnected")
- Mobile toggle (switches to read-only Executive Overview)

---

## 3. User Flows

### 3.1 Flow: Monitor Active Tasks

```
Entry: Executive Overview (default landing)
  │
  ├─ User sees: "Active agents: N" and task counts by state
  │
  ├─ User clicks: "Active tasks" count → Product module (filtered to active states)
  │     │
  │     └─ User sees: Task list filtered to BUILDING, TESTING, REVIEWING
  │           │
  │           ├─ User clicks a specific task → Task Detail
  │           │     │
  │           │     ├─ Contract Tab: What is being built, by whom, risk level
  │           │     ├─ State History Tab: Timeline of state transitions
  │           │     ├─ Evidence Tab: What gates have passed/failed
  │           │     ├─ Findings Tab: Review findings and decisions
  │           │     └─ Relationships Tab: Subtasks, dependencies, linked decisions
  │           │
  │           └─ User returns to list, or drills deeper via Engineering Mission Control
  │
  └─ Alternative: User clicks directly to Engineering Mission Control → Active Tasks Dashboard
        │
        └─ Broader view: Parent tasks, subtasks, agent assignments, worktree status
```

**Key decision points:**
- Product module is for "what is happening" (task-centric)
- Engineering Mission Control is for "how it's happening" (execution-centric)
- User chooses based on whether they care about the task outcome or the execution details

### 3.2 Flow: Review Blocked Tasks

```
Entry: Executive Overview → "Blocked tasks: N"
  │
  └─ User clicks badge → Engineering Mission Control → Blocked Tasks view
        │
        ├── Blocked tasks listed with:
        │   ├── Task ID and title
        │   ├── Blocking reason (depends on TASK-XXXX, scope violation, merge conflict, etc.)
        │   ├── Time blocked (duration since BLOCKED state entered)
        │   └── Blocker detail (which dependency, which file, which agent)
        │
        ├── User clicks a blocked task → Task Detail
        │     │
        │     └── Relationships Tab shows dependency graph with the blocking edge highlighted
        │
        └── User actions from this view:
              ├── If dependency-blocked: Navigate to the blocking task
              ├── If collision-blocked: Navigate to Collisions view to resolve
              ├── If scope-blocked: Navigate to scope violation detail
              └── No "force unblock" action — block must be genuinely resolved
```

### 3.3 Flow: Approve Ready-for-Amjad

```
Entry: Executive Overview → "Tasks awaiting your approval: N"
  │
  └─ User clicks badge → Product module filtered to READY_FOR_AMJAD state
        │
        ├── Task list shows:
        │   ├── Task ID, title, project, risk level
        │   ├── Time in READY_FOR_AMJAD (how long awaiting approval)
        │   ├── Summary indicators: gates (green/red), findings (resolved/unresolved), rollback (ready/missing)
        │   └── Visual tasks: screenshot thumbnail
        │
        └── User clicks a task → Task Detail → Evidence Tab
              │
              ├── Evidence Tab shows complete evidence package:
              │   ├── Acceptance criteria: met / unmet / partial
              │   ├── Scope compliance: pass / violations listed
              │   ├── Automated gates: per-gate pass/fail with links to raw output
              │   ├── Visual evidence: screenshots at all required breakpoints
              │   ├── Review summary: findings by severity with decisions
              │   └── Readiness: preview URL, rollback package, known limitations
              │
              ├── User reviews evidence
              │
              ├── User clicks "Approve" → Confirmation modal:
              │     "Approve TASK-XXXX? This will trigger merge to [branch]."
              │     Requires: reason (optional), confirm button
              │
              ├── User clicks "Reject" → Rejection modal:
              │     "Reject TASK-XXXX? This returns the task to the builder."
              │     Requires: reason (required), confirm button
              │
              └── On confirm:
                    ├── State transitions to APPROVED or REJECTED
                    ├── Audit log records the action
                    ├── If APPROVED + R4 commercial: Additional confirmation required in Commercial Safety
                    └── If APPROVED: Hermes proceeds to merge
```

### 3.4 Flow: Inspect Agent Runs

```
Entry: Executive Overview → "Active agents: N" or Operations → Agent Fleet Status
  │
  └─ User navigates to Engineering Mission Control → Agent Runs
        │
        ├── Active agents listed with:
        │   ├── Agent name and type (Kimi K3, Codex, Claude Code, etc.)
        │   ├── Current task (ID + title)
        │   ├── Worktree
        │   ├── Current state (IDLE, DISPATCHED, BUILDING, SUBMITTED, REVIEWING)
        │   ├── Session duration
        │   ├── Last heartbeat (with color: green <5m, yellow 5-10m, red >10m)
        │   └── Files currently touched
        │
        ├── User clicks an agent → Agent Detail
        │     │
        │     ├── Agent identity and capabilities
        │     ├── Scorecard summary (last 10 tasks, per-category metrics)
        │     ├── Current task detail (contract, state, evidence so far)
        │     ├── Worktree detail (branch, base commit, current HEAD, dirty files)
        │     ├── File ownership map (what this agent owns vs other agents)
        │     └── Session log (recent agent actions, timestamps)
        │
        └── User actions:
              ├── Terminate agent run (only if silent >30 min or stuck — requires confirmation)
              └── View full scorecard history
```

### 3.5 Flow: View Decisions and Regressions

```
Entry: Knowledge module
  │
  ├── Decision Register
  │     │
  │     ├── Filterable by: status (proposed, approved, locked, superseded, deprecated),
  │     │   category (architecture, product, commercial, security, governance, design),
  │     │   project (avoa, hermes-os)
  │     │
  │     ├── Decision cards show: ID, title, status badge, category, date, owner
  │     │
  │     └── Click a decision → Decision Detail
  │           ├── Full decision text
  │           ├── Rationale
  │           ├── Alternatives considered (with rejection reasons)
  │           ├── Supersedes / superseded by chain
  │           ├── Related tasks
  │           └── Status history
  │
  └── Regression Register
        │
        ├── Filterable by: status (unresolved, resolved, false_positive, wont_fix),
        │   severity, task, date range
        │
        ├── Regression cards show: ID, title, severity, status, detected date, source task
        │
        └── Click a regression → Regression Detail
              ├── Description of the regression
              ├── Detection method (test failure, monitoring alert, manual report)
              ├── Evidence (failing test output, error logs, screenshots)
              ├── Root cause analysis
              ├── Resolution (if resolved)
              └── Linked tasks (source task, fix task)
```

---

## 4. Empty State Designs

### 4.1 No Tasks Exist

**Where:** Product module, filtered views with no results.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                    📋  No Tasks Yet                      │
│                                                         │
│   No tasks match your current filters.                  │
│                                                         │
│   Tasks are created when Hermes converts a product       │
│   intent into a structured task contract.               │
│                                                         │
│   [Clear Filters]    [Go to Executive Overview]         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 No Agents Running

**Where:** Engineering Mission Control → Agent Runs, Operations → Agent Fleet Status.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                 🤖  No Active Agents                    │
│                                                         │
│   All agents are idle. No tasks are currently being      │
│   built, tested, or reviewed.                           │
│                                                         │
│   Agents activate when Hermes dispatches a task to       │
│   a builder, reviewer, or specialist agent.             │
│                                                         │
│   [View Agent Fleet]    [View Task Queue]               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.3 No Reviews Pending

**Where:** Engineering Mission Control → Review Queue.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                 ✅  No Pending Reviews                   │
│                                                         │
│   All submitted implementations have been reviewed.      │
│   Review queue is clear.                                │
│                                                         │
│   Reviews are triggered when a builder submits their     │
│   implementation and the automated gates pass.           │
│                                                         │
│   [View Recently Reviewed]                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.4 No Decisions Recorded

**Where:** Knowledge → Decision Register.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                 📝  No Decisions Yet                     │
│                                                         │
│   The decision register is empty. Decisions are          │
│   created by Hermes when significant architectural,      │
│   product, or commercial choices are made.               │
│                                                         │
│   Each decision is recorded with its rationale,          │
│   alternatives considered, and approval status.          │
│                                                         │
│   Decisions survive across tasks, sessions, and agents.  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.5 No Regressions Recorded (Positive Empty State)

**Where:** Knowledge → Regression Register.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              🎉  No Regressions Detected                 │
│                                                         │
│   This is the desired state. No previously working       │
│   behavior has broken.                                  │
│                                                         │
│   Regressions are automatically detected through:        │
│   • Test suite failures on changed code                 │
│   • Visual regression detection on UI changes            │
│   • Monitoring alerts on deployed features              │
│   • Business fixture validation failures                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.6 No Design Briefs

**Where:** Design Studio → Design Briefs.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                 🎨  No Design Briefs                     │
│                                                         │
│   Design briefs are created when a task requires          │
│   visual UI work. The Design Studio agents produce       │
│   briefs, UI contracts, and design artifacts.            │
│                                                         │
│   [View Design System]    [View Product Tasks]           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.7 No Active Incidents

**Where:** Operations → Incident Log.

**Display:**
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              ✅  No Active Incidents                     │
│                                                         │
│   All systems operational. No incidents in progress.     │
│                                                         │
│   [View Past Incidents]                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Alert Patterns

### 5.1 Alert Classification

| Severity | Visual Treatment | Behavior | Examples |
|---|---|---|---|
| **Critical** | Red badge, persistent banner, interruptive if appropriate | Must be acknowledged (not just dismissed). Surfaces in Executive Overview. | Blocker finding unresolved, agent offline >30 min, protected zone violation, deployment failure |
| **Warning** | Amber badge, banner (dismissible) | Should be reviewed within 4 hours. Surfaces in module badge. | Build failure, scope violation, review overdue, gate pass rate drop |
| **Info** | Blue badge, non-intrusive | Advisory only. No action required. | Task entered new state, release approaching, worktree stale, feature flag aged |

### 5.2 Alert Delivery

| Channel | Critical | Warning | Info |
|---|---|---|---|
| In-app bell icon | ✓ (with count) | ✓ (aggregated) | — |
| Module sidebar badge | ✓ (module-specific) | ✓ (module-specific) | ✓ (module-specific) |
| Executive Overview card | ✓ | ✓ | ✓ |
| In-module banner | ✓ (persistent until acknowledged) | ✓ (dismissible) | — |

### 5.3 Specific Alert Patterns

#### Pattern: Blocked Task

```
Trigger: Task enters BLOCKED state
Severity: Warning (Info if dependency-blocked by a known in-progress task)

Alert content:
  ⚠️  TASK-0042 is BLOCKED
  Reason: Merge conflict in components/quotes/QuoteReviewHeader.tsx
  Blocking: Subtask TASK-0042-S1 and TASK-0042-S2 both modified this file
  Duration: 15 minutes
  
  [View Task]  [View Collision]
```

#### Pattern: Failed Gate

```
Trigger: Any automated gate returns non-pass status
Severity: Warning (Critical if R4 task or deployment gate)

Alert content:
  ❌  Gate Failure: TASK-0042
  Gate: Tests
  Details: 3 failed, 0 errors, 12 passed
  Failed: QuoteTotalTest, TaxCalculationTest, DiscountRoundTest
  
  [View Results]  [View Task]
```

#### Pattern: Scope Violation

```
Trigger: Agent writes to file outside allowed set
Severity: Warning

Alert content:
  ⚠️  Scope Violation: Codex on TASK-0042
  Allowed files: components/quotes/QuoteHeader.tsx
  Actually modified: components/quotes/QuoteHeader.tsx, utils/pricing.ts
  Unauthorized file: utils/pricing.ts is NOT in the allowed set
  
  [View Violation]  [View Task Contract]
```

#### Pattern: Unreviewed Finding

```
Trigger: Review finding with severity=blocker and decision=pending for >2h
Severity: Critical

Alert content:
  🔴  Unreviewed Blocker Finding
  Task: TASK-0042
  Finding: "Missing null check in pricing calculation — could produce NaN"
  Reviewer: Claude Code
  Time in review: 3h 15m
  
  [View Finding]  [Trigger Re-review]
```

#### Pattern: Agent Silent

```
Trigger: No heartbeat from agent for >10 min (warning) or >30 min (critical)
Severity: Warning → Critical

Alert content (10 min):
  ⚠️  Agent Unresponsive: Kimi K3
  Task: TASK-0042-S1
  Last heartbeat: 12 minutes ago
  Worktree: wt-task-0042-s1
  
  [View Agent]  [Investigate]

Alert content (30 min):
  🔴  Agent Silent: Kimi K3
  Task: TASK-0042-S1
  Last heartbeat: 32 minutes ago
  Subtask may need reassignment or termination.
  
  [View Agent]  [Terminate Run]
```

---

## 6. Dashboard Layout Concept

### 6.1 Executive Overview Layout (Default Landing)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Hermes CC]  [Search...]                        [🔔 3] [Amjad] [●Live]│
├────────┬─────────────────────────────────────────────────────────────┤
│        │                                                             │
│  📊    │  EXECUTIVE OVERVIEW                          [Last updated]  │
│  Over  │                                                             │
│        │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  📂    │  │ 🟢 Awaiting  │ │ ⚠️  Blocked   │ │ 🔴 Failed    │         │
│  Port  │  │  Approval    │ │   Tasks      │ │   Gates      │         │
│        │  │     3        │ │     2        │ │     1        │         │
│  📋    │  └──────────────┘ └──────────────┘ └──────────────┘         │
│  Prod  │                                                             │
│        │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  🎨    │  │ 🟡 Review     │ │ 📝 Decisions  │ │ 🚨 Regressions│        │
│  Design│  │  Findings    │ │  Pending     │ │  (7 days)    │         │
│        │  │     4        │ │     2        │ │     0        │         │
│  ⚙️    │  └──────────────┘ └──────────────┘ └──────────────┘         │
│  EMC   │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐   │
│  📈    │  │  Active Agents                                        │   │
│  Qual  │  │  Kimi K3 ● │ Codex ◐ │ Claude Code ○ │ Gemini ○      │   │
│        │  │  3 more agents idle                                   │   │
│  🔒    │  └──────────────────────────────────────────────────────┘   │
│  Comm  │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐   │
│  📚    │  │  Recent Activity                                       │   │
│  Knowl │  │  14:32  TASK-0051 entered REVIEWING                   │   │
│        │  │  14:28  TASK-0042 gate FAILED (tests)                  │   │
│  🚀    │  │  14:15  TASK-0039 APPROVED by Amjad                   │   │
│  Release│  │  14:02  TASK-0048 entered BUILDING (Kimi K3)         │   │
│        │  │  13:55  Decision DEC-HOS-017 proposed                 │   │
│  ⚡    │  └──────────────────────────────────────────────────────┘   │
│  Ops   │                                                             │
│        │                                                             │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Information architecture principles for this layout:**
- **Top row:** Three critical-status cards (approval queue, blocked, gate failures) — these are the "what needs attention" answer
- **Middle row:** Three secondary-status cards (findings, pending decisions, regressions)
- **Agent strip:** Visual pulse of the agent fleet — green = active, half = dispatched/idle, empty = offline
- **Activity feed:** Chronological, reverse-order event log — the heartbeat of the system
- **Sidebar:** Persistently visible with badge counts, enabling one-click navigation to any module

### 6.2 Engineering Mission Control Layout (Deep Operations View)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Hermes CC]  [Search...]                        [🔔 3] [Amjad] [●Live]│
├────────┬─────────────────────────────────────────────────────────────┤
│        │  ENGINEERING MISSION CONTROL                                │
│  📊    │  [Active Tasks] [Agents] [Worktrees] [Reviews] [Validation] │
│  Over  │                                                             │
│        │  ┌──────────────────────┐ ┌──────────────────────────────┐  │
│  ...   │  │  PARENT TASKS        │ │  SUBTASKS                    │  │
│        │  │                      │ │                              │  │
│  ⚙️    │  │  TASK-0042 BUILDING  │ │  S1: Kimi K3 ● BUILDING     │  │
│  EMC   │  │  └─ 3 subtasks       │ │  S2: Codex ◐ SUBMITTED      │  │
│  active│  │                      │ │  S3: Kimi K3 ○ BLOCKED      │  │
│        │  │  TASK-0048 REVIEWING │ │     └─ awaits S1            │  │
│  ...   │  │  └─ 1 task           │ │                              │  │
│        │  │                      │ │  TASK-0048-S1: Codex ● REV   │  │
│        │  └──────────────────────┘ └──────────────────────────────┘  │
│        │                                                             │
│        │  ┌──────────────────────┐ ┌──────────────────────────────┐  │
│        │  │  AGENT RUNS          │ │  WORKTREES                   │  │
│        │  │                      │ │                              │  │
│        │  │  Kimi K3 (2 tasks)   │ │  wt-task-0042-s1 ● active    │  │
│        │  │  Codex (1 task)      │ │  wt-task-0048-s1 ● active    │  │
│        │  │  Claude Code (1 rev) │ │  wt-task-0042-s2 ◐ stale     │  │
│        │  │  Gemini Code (idle)  │ │  wt-task-0039 ○ archived     │  │
│        │  │  15 more idle        │ │                              │  │
│        │  └──────────────────────┘ └──────────────────────────────┘  │
│        │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐   │
│        │  │  DEPENDENCY GRAPH (TASK-0042)                        │   │
│        │  │                                                      │   │
│        │  │     S1 (BUILDING) ──┬──▶ S3 (BLOCKED)               │   │
│        │  │         │           │                                 │   │
│        │  │         └───────────┼──▶ S4 (PENDING)                │   │
│        │  │                     │                                 │   │
│        │  │     S2 (SUBMITTED) ─┘                                 │   │
│        │  └──────────────────────────────────────────────────────┘   │
│        │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐   │
│        │  │  FILE OWNERSHIP                                       │   │
│        │  │  components/quotes/QuoteHeader.tsx     → S1 (Kimi)   │   │
│        │  │  components/quotes/QuoteTable.tsx      → S2 (Codex)  │   │
│        │  │  components/quotes/QuoteFooter.tsx     → S3 (Kimi)   │   │
│        │  │  ⚠️  utils/pricing.ts  — OVERLAP DETECTED           │   │
│        │  └──────────────────────────────────────────────────────┘   │
│        │                                                             │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Information architecture principles for this layout:**
- **Tab bar:** Sub-sections as tabs — user can focus on one dimension at a time
- **Multi-pane:** When screen width allows, show related panes side by side (parent/subtask, agents/worktrees)
- **Dependency graph:** Visual DAG showing blocking relationships — the most information-dense element
- **File ownership:** Simple mapping table — green when clean partition, red when overlap
- **Live indicators:** Colored dots (● ○ ◐) convey state at a glance without reading text

### 6.3 Mobile Read-Only View

```
┌─────────────────────┐
│ HERMES CC           │
│                     │
│ ┌─────────────────┐ │
│ │ ⏰ Awaiting You  │ │
│ │                 │ │
│ │ 🔴 3 approvals  │ │
│ │ ⚠️  2 blocked    │ │
│ │ ⚠️  1 gate fail  │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Active Agents    │ │
│ │ Kimi K3 ●       │ │
│ │ Codex ◐         │ │
│ │ Claude Code ○   │ │
│ │ +3 idle          │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Recent           │ │
│ │ 14:32 REVIEWING  │ │
│ │ 14:28 GATE FAIL  │ │
│ │ 14:15 APPROVED   │ │
│ └─────────────────┘ │
│                     │
│ No actions available│
│ in mobile view      │
└─────────────────────┘
```

---

## 7. Navigation Principles

1. **Three-click rule.** Any entity (task, decision, agent run, finding) should be reachable in ≤ 3 clicks from the landing page.

2. **Consistent entity linking.** Whenever a task ID, decision ID, or agent name appears, it is a clickable link to that entity's detail view.

3. **Filter persistence.** Filters in Product, Knowledge, and Quality modules persist within the session. Returning to the module restores the last filter state.

4. **Back-button safety.** Browser back button must return to the previous view with filters intact. No destructive navigation.

5. **Deep linking.** Every entity detail view has a stable URL that can be bookmarked or shared. Example: `/command-center/product/task/TASK-0042`

6. **Module isolation.** Actions in one module do not unexpectedly change state in another module. If approving a task in Product triggers a deployment in Releases, the user sees a clear "task approved → deployment triggered" notification but is not forcibly navigated.

7. **Progressive disclosure.** Overview shows summaries. Module views show filtered lists. Detail views show full records. Raw YAML/JSON available behind an "Inspect Raw" toggle on every detail view.

---

## 8. Search Architecture

### 8.1 Search Scope

Global search indexes across:
- Task IDs, titles, descriptions, acceptance criteria text
- Decision IDs, titles, decision text, categories
- Regression IDs, titles, descriptions
- Agent names, scorecard categories
- File paths (from file ownership and change records)
- Finding descriptions (review findings, visual findings)
- Release names and descriptions
- Project names

### 8.2 Search Behavior

- **As-you-type:** Results appear after 2+ characters, debounced at 300ms
- **Result grouping:** Results grouped by entity type (Tasks, Decisions, Agents, Files, Findings, Releases)
- **Quick navigation:** Each result is directly clickable to its detail view
- **Recent searches:** Last 5 searches stored per user session
- **No results:** "No results for '[query]'. Try a task ID, agent name, or keyword."

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*