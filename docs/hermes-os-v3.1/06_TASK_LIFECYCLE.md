# 06 — Task Lifecycle

**Document ID:** HERMES-OS-V3.1-06
**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Authority:** Hermes Engineering OS v3.1

---

## Purpose

This document defines the complete Hermes OS v3.1 task lifecycle — a 22-state primary state machine with 8 exception states. Every Hermes-managed task moves through these states. Hermes owns ALL state transitions. No agent may advance or regress a task's state except Hermes.

---

## 1. Complete State Machine (ASCII Diagram)

```
                              REQUEST RECEIVED
                                    │
                                    ▼
                            ◄── REQUESTED ───►
                                    │
                           (Amjad clarifies)
                                    ▼
                          CONTEXT_RETRIEVED
                                    │
                                    ▼
                            CLASSIFYING
                                    │
                                    ▼
                             CLASSIFIED
                                    │
                           ┌────────┼────────┐
                           ▼        ▼        ▼
                     RISK_      RISK_     RISK_
                    ASSESSED  ASSESSED  ASSESSED
                    (R1-R2)   (R3)     (R4)
                           │        │        │
                           └────────┼────────┘
                                    ▼
                          CONTRACT_DRAFTED
                                    │
                           (Amjad reviews)
                                    ▼
                    ┌───────► APPROVED ◄───────┐
                    │                          │
                    │   (R1 auto; R2-R4 Amjad) │
                    │                          │
                    ▼                          │
                  READY                        │
                    │                          │
                    ▼                          │
         ┌──► DISPATCHING ◄──┐                │
         │        │           │                │
         │        ▼           │                │
         │  IN_PROGRESS ──────┤ (re-dispatch)  │
         │        │           │                │
         │        ▼           │                │
         │  IMPLEMENTED       │                │
         │        │           │                │
         │        ▼           │                │
         │  SELF_CHECKED      │                │
         │        │           │                │
         │        ▼           │                │
         │    COMMITTED       │                │
         │        │           │                │
         │        ▼           │                │
         │  GATE_CHECKING     │                │
         │        │           │                │
         │        ▼           │                │
         │  GATES_PASSED      │                │
         │        │           │                │
         │        ▼           │                │
         │   REVIEWING        │                │
         │        │           │                │
         │        ▼           │                │
         │   REVIEWED         │                │
         │        │           │                │
         │   ┌────┴────┐      │                │
         │   ▼         ▼      │                │
         │  FINDINGS  FINDINGS│                │
         │  CLEAN    FOUND    │                │
         │   │         │      │                │
         │   │    ┌────▼────┐ │                │
         │   │    │FIXING   │ │                │
         │   │    │(repair  │─┤ (re-dispatch)  │
         │   │    │ cycle)  │ │  if 2 repairs  │
         │   │    └────┬────┘ │  fail → REPAIR_│
         │   │         │      │  FAILED        │
         │   └────┬────┘      │                │
         │        ▼           │                │
         │   CORRECTIONS      │                │
         │    APPLIED         │                │
         │        │           │                │
         │        ▼           │                │
         │  PREVIEW_READY     │                │
         │        │           │                │
         │   (Amjad preview)  │                │
         │        │           │                │
         │   ┌────┴────┐      │                │
         │   ▼         ▼      │                │
         │  AMJAD_    AMJAD_  │                │
         │  APPROVED  CHANGES │                │
         │   │         │      │                │
         │   │    ┌────▼────┐ │                │
         │   │    │ADJUSTING│─┤                │
         │   │    └────┬────┘ │                │
         │   │         │      │                │
         │   └────┬────┘      │                │
         │        ▼           │                │
         │   READY_TO_MERGE   │                │
         │        │           │                │
         │        ▼           │                │
         │     MERGED         │                │
         │        │           │                │
         │        ▼           │                │
         │   DEPLOYING        │ ◄──────────────┘
         │        │           │   (amend &
         │        ▼           │    re-approve)
         │    DEPLOYED        │
         │        │           │
         │        ▼           │
         │    OBSERVING       │
         │        │           │
         │        ▼           │
         │    RECORDING       │
         │        │           │
         │        ▼           │
         │     CLOSED         │
         │                    │
         └────────────────────┘


            ── EXCEPTION STATES (8) ──

    REQUESTED ───► NEEDS_CLARIFICATION
                        │
                        └──► REQUESTED (clarified)

    CLASSIFYING ───► NEEDS_DECISION
                        │
                        └──► CLASSIFIED (resolved)

    CONTRACT_DRAFTED ───► BLOCKED_BY_DEPENDENCY
                              │
                              └──► CONTRACT_DRAFTED (unblocked)

    IN_PROGRESS ───► BLOCKED_BY_EXTERNAL
    IMPLEMENTED         │
    SELF_CHECKED        └──► IN_PROGRESS (resolved)

    IN_PROGRESS ───► SCOPE_EXCEEDED
                        │
                        └──► CONTRACT_DRAFTED (amended)

    IN_PROGRESS ───► STOP_CONDITION_TRIGGERED
                        │
                        └──► REQUESTED (re-scoped)
                        └──► CANCELLED (unresolvable)

    ANY STATE ───► CANCELLED
    (except CLOSED)

    IN_PROGRESS ───► REPAIR_FAILED
    (after 2          │
     repair cycles)   └──► REQUESTED (re-scoped)
                      └──► CANCELLED

    APPROVED ───► SUPERSEDED
                      │
                      └──► CLOSED (with SUPERSEDED outcome)
```

---

## 2. State Definitions

### 2.1 Primary States (22)

#### STATE-01: REQUESTED

**Entry criteria:** Amjad or Hermes initiates a new task request.

**Required records:**
- Conversation context capturing the request
- Initial requirement statement
- Product and department identification

**Permitted actions:**
- Hermes may clarify with Amjad (→ `NEEDS_CLARIFICATION` → back to `REQUESTED`)
- Hermes may begin context retrieval
- Hermes may cancel the request (Amjad-directed)

**Exit criteria:**
- Request is unambiguous enough to begin context retrieval
- Product and department are identified

**Allowed transitions:**
- → CONTEXT_RETRIEVED
- → NEEDS_CLARIFICATION
- → CANCELLED

**Owner:** Hermes

---

#### STATE-02: CONTEXT_RETRIEVED

**Entry criteria:** Hermes has retrieved relevant product knowledge, locked decisions, regression records, and architectural context.

**Required records:**
- List of applicable locked decisions (referenced by ID)
- List of relevant regression records
- Current repository state (branch, commit SHA)
- Active worktrees and in-flight tasks that may conflict

**Permitted actions:**
- Hermes may load additional context if gaps are found
- Hermes may return to REQUESTED if context reveals the request is invalid

**Exit criteria:**
- All relevant locked decisions are identified
- Regression risks are mapped
- Repository baseline is known

**Allowed transitions:**
- → CLASSIFYING
- → REQUESTED (if context invalidates request)

**Owner:** Hermes

---

#### STATE-03: CLASSIFYING

**Entry criteria:** Context is loaded; task classification is underway.

**Required records:**
- Proposed `primary_class`
- Proposed `risk_level`
- Classification reasoning

**Permitted actions:**
- Hermes evaluates against risk classification rules (per 07_RISK_CLASSIFICATION)
- Hermes assesses commercial impact
- Hermes determines parallelism eligibility

**Exit criteria:**
- `primary_class` assigned
- `risk_level` assigned (R1-R4)
- `commercial_impact` determined
- `parallel_eligible` determined

**Allowed transitions:**
- → CLASSIFIED
- → NEEDS_DECISION

**Owner:** Hermes

---

#### STATE-04: CLASSIFIED

**Entry criteria:** Risk and classification are finalized.

**Required records:**
- Final `primary_class`
- Final `risk_level`
- Commercial impact flag
- Parallel eligibility flag
- Classification justification

**Permitted actions:**
- Hermes proceeds to risk assessment (R1-R2, R3, R4 sub-states)

**Exit criteria:**
- Classification is recorded and immutable until potential amendment

**Allowed transitions:**
- → RISK_ASSESSED (implicit sub-state completion; proceeds to CONTRACT_DRAFTED)

**Owner:** Hermes

---

#### STATE-05: CONTRACT_DRAFTED

**Entry criteria:** Full task contract YAML (per 04_TASK_CONTRACT_STANDARD) has been drafted.

**Required records:**
- Complete task contract in `.hermes/contracts/TASK-{PRODUCT}-{NNNN}.yaml`
- UI contract (if visual work) in `.hermes/contracts/UI-{PRODUCT}-{NNNN}.yaml`
- Schema validation passing

**Permitted actions:**
- Hermes validates contract against schema
- Hermes presents contract to Amjad for R2-R4 tasks
- Hermes self-approves R1 tasks

**Exit criteria:**
- Contract passes all schema validation checks
- Contract is either auto-approved (R1) or submitted to Amjad (R2-R4)

**Allowed transitions:**
- → APPROVED
- → NEEDS_CLARIFICATION (Amjad asks questions)
- → BLOCKED_BY_DEPENDENCY
- → CANCELLED

**Owner:** Hermes

---

#### STATE-06: APPROVED

**Entry criteria:** Contract has been approved (by Hermes for R1; by Amjad for R2-R4).

**Required records:**
- Approval record with role, date, and any notes
- Locked contract file (no further modification without formal amendment)

**Permitted actions:**
- Hermes prepares builder dispatch
- Hermes creates working branch
- Hermes sets up worktree if parallel

**Exit criteria:**
- Contract is immutable (until formal amendment)
- Working branch exists

**Allowed transitions:**
- → READY
- → SUPERSEDED (newer contract obsoletes this one)
- → CANCELLED

**Owner:** Hermes (R1) or Amjad (R2-R4)

---

#### STATE-07: READY

**Entry criteria:** Contract approved, branch/worktree ready, builder selected.

**Required records:**
- Builder assignment (primary + fallback)
- Branch name and base commit
- Sanitized builder-view contract excerpt generated

**Permitted actions:**
- Hermes dispatches to builder

**Exit criteria:**
- Dispatch command issued to builder agent

**Allowed transitions:**
- → DISPATCHING

**Owner:** Hermes

---

#### STATE-08: DISPATCHING

**Entry criteria:** Builder dispatch is in progress.

**Required records:**
- Dispatch timestamp
- Builder model, mode, and sanitized contract excerpt
- Worktree or branch assignment

**Permitted actions:**
- Hermes monitors dispatch success
- Hermes may re-dispatch if builder fails to start

**Exit criteria:**
- Builder acknowledges receipt of contract
- Builder begins implementation

**Allowed transitions:**
- → IN_PROGRESS
- → DISPATCHING (re-dispatch on failure to start)
- → REQUESTED (escalate if builder unavailable)

**Owner:** Hermes

---

#### STATE-09: IN_PROGRESS

**Entry criteria:** Builder is actively implementing.

**Required records:**
- Builder session identifier
- Active worktree path
- Start timestamp

**Permitted actions:**
- Builder works within contract scope
- Hermes monitors for stop conditions
- Builder may request clarification (routed through Hermes)

**Exit criteria:**
- Builder declares implementation complete
- OR a stop condition is triggered
- OR scope is exceeded

**Allowed transitions:**
- → IMPLEMENTED
- → STOP_CONDITION_TRIGGERED
- → SCOPE_EXCEEDED
- → BLOCKED_BY_EXTERNAL
- → REPAIR_FAILED
- → CANCELLED

**Owner:** Builder (execution), Hermes (monitoring and transition authority)

---

#### STATE-10: IMPLEMENTED

**Entry criteria:** Builder has completed implementation and submitted results.

**Required records:**
- Builder report (per Builder Report Template)
- Changed files list
- Implementation notes and assumptions

**Permitted actions:**
- Hermes reviews builder report for completeness
- Hermes returns to builder if report is incomplete

**Exit criteria:**
- Builder report is complete and references all changed files

**Allowed transitions:**
- → SELF_CHECKED
- → IN_PROGRESS (report rejected as incomplete)

**Owner:** Hermes

---

#### STATE-11: SELF_CHECKED

**Entry criteria:** Builder has run automated self-checks.

**Required records:**
- Build output (pass/fail)
- Lint output (pass/fail)
- Type-check output (pass/fail)
- Self-test results (if builder ran tests)

**Permitted actions:**
- Hermes validates self-check evidence
- Hermes proceeds to commit

**Exit criteria:**
- Self-check evidence is present and parsable

**Allowed transitions:**
- → COMMITTED
- → IN_PROGRESS (self-checks failed; repair)

**Owner:** Hermes

---

#### STATE-12: COMMITTED

**Entry criteria:** Implementation has been committed to the working branch.

**Required records:**
- Commit SHA(s)
- Commit message(s)
- Diff summary (files changed, lines added/removed)

**Permitted actions:**
- Hermes triggers automated gate pipeline

**Exit criteria:**
- Commit exists on working branch
- Diff is available for inspection

**Allowed transitions:**
- → GATE_CHECKING

**Owner:** Hermes

---

#### STATE-13: GATE_CHECKING

**Entry criteria:** Automated gate pipeline is running.

**Required records:**
- CI run identifier
- Gate configuration (which gates per risk level)

**Permitted actions:**
- CI executes gates: build, lint, typecheck, existing tests, new tests, fixture check, scope check
- Hermes monitors gate status

**Exit criteria:**
- All required gates (per risk level and contract) have completed
- Gate results are collected

**Allowed transitions:**
- → GATES_PASSED
- → IN_PROGRESS (gates failed; repair needed)
- → STOP_CONDITION_TRIGGERED (gates fail for unclear reason)

**Owner:** Hermes (orchestration), CI (execution)

---

#### STATE-14: GATES_PASSED

**Entry criteria:** All required automated gates passed.

**Required records:**
- Gate report (per-gate pass/fail with output)
- Timestamp of gate completion

**Permitted actions:**
- Hermes assembles review package
- Hermes dispatches to reviewer

**Exit criteria:**
- Review package is assembled (contract, diff, gate report, builder report, evidence)

**Allowed transitions:**
- → REVIEWING

**Owner:** Hermes

---

#### STATE-15: REVIEWING

**Entry criteria:** Reviewer (Claude Code or Hermes) has received the review package.

**Required records:**
- Review dispatch timestamp
- Review package contents (contract, diff, reports, evidence)

**Permitted actions:**
- Reviewer inspects code, diff, tests, and evidence
- Reviewer cross-references against locked decisions and regression records

**Exit criteria:**
- Reviewer submits structured findings to Hermes

**Allowed transitions:**
- → REVIEWED

**Owner:** Reviewer (Claude Code / Hermes)

---

#### STATE-16: REVIEWED

**Entry criteria:** Reviewer has submitted findings.

**Required records:**
- Structured findings document (per 15_TECHNICAL_REVIEW_AND_FINDINGS_PROTOCOL)
- Per-finding severity (BLOCKER, HIGH, MEDIUM, LOW, OPTIONAL)
- Reviewer recommendation (APPROVE, CHANGES_REQUESTED, REJECT)

**Permitted actions:**
- Hermes adjudicates findings:
  - ACCEPT: finding requires correction
  - REJECT: finding is incorrect or out of scope
  - DEFER: finding is valid but out of scope for this contract
- Hermes determines next state

**Exit criteria:**
- All findings are triaged (accepted, rejected, or deferred)

**Allowed transitions:**
- → FINDINGS_CLEAN (no accepted findings)
- → FINDINGS_FOUND (accepted findings require correction)

**Owner:** Hermes (adjudication)

---

#### STATE-17: FINDINGS_CLEAN

**Entry criteria:** No accepted findings; code is review-clean.

**Required records:**
- Findings adjudication record
- Rejected/deferred findings with justification

**Permitted actions:**
- Hermes proceeds to preview readiness

**Exit criteria:**
- Adjudication record is complete

**Allowed transitions:**
- → PREVIEW_READY

**Owner:** Hermes

---

#### STATE-18: FINDINGS_FOUND

**Entry criteria:** Accepted findings require correction.

**Required records:**
- List of approved corrections
- Per-correction severity and priority

**Permitted actions:**
- Hermes sends approved corrections to builder
- Builder enters repair cycle

**Exit criteria:**
- Corrections dispatched to builder

**Allowed transitions:**
- → FIXING

**Owner:** Hermes

---

#### STATE-19: FIXING

**Entry criteria:** Builder is implementing approved corrections.

**Required records:**
- Repair cycle number (1 or 2)
- List of approved corrections
- Repair dispatch timestamp

**Permitted actions:**
- Builder implements ONLY approved corrections
- Builder may not expand scope or address non-approved findings
- Hermes tracks repair cycle count

**Exit criteria:**
- Builder submits corrected code
- OR repair cycle fails

**Allowed transitions:**
- → SELF_CHECKED (repair complete; re-enter gate/review pipeline)
- → REPAIR_FAILED (2 repair cycles exhausted)

**Owner:** Builder (execution), Hermes (monitoring)

---

#### STATE-20: CORRECTIONS_APPLIED

**Entry criteria:** Post-repair review cycle complete; corrections verified.

**Required records:**
- Correction verification report
- Updated diff and gate results

**Permitted actions:**
- Hermes prepares preview

**Exit criteria:**
- All approved corrections applied and verified

**Allowed transitions:**
- → PREVIEW_READY

**Owner:** Hermes

---

#### STATE-21: PREVIEW_READY

**Entry criteria:** Implementation is complete, gates pass, review is clean, preview is available.

**Required records:**
- Preview URL (Replit or equivalent)
- Screenshot evidence (if visual)
- Full evidence package assembled

**Permitted actions:**
- Hermes presents preview to Amjad
- Amjad may inspect, test, and provide feedback

**Exit criteria:**
- Amjad has reviewed the preview

**Allowed transitions:**
- → AMJAD_APPROVED
- → AMJAD_CHANGES_REQUESTED

**Owner:** Hermes (presentation), Amjad (review)

---

#### STATE-22: AMJAD_APPROVED

**Entry criteria:** Amjad has approved the preview and outcome.

**Required records:**
- Amjad approval record with date and notes

**Permitted actions:**
- Hermes prepares merge

**Exit criteria:**
- Approval recorded

**Allowed transitions:**
- → READY_TO_MERGE

**Owner:** Amjad

---

#### STATE-23: READY_TO_MERGE

**Entry criteria:** All gates passed, Amjad approved, merge is safe.

**Required records:**
- Merge approval record
- Rollback package (if R3 or R4)
- Deployment notes (if applicable)

**Permitted actions:**
- Hermes executes merge (or creates PR for branch-protection flow)

**Exit criteria:**
- Code is on target branch (master/main)

**Allowed transitions:**
- → MERGED

**Owner:** Hermes

---

#### STATE-24: MERGED

**Entry criteria:** Code is merged to the target branch.

**Required records:**
- Merge commit SHA
- Merge timestamp

**Permitted actions:**
- Hermes initiates deployment (if applicable)
- Hermes releases worktree (if parallel)

**Exit criteria:**
- Merge is confirmed on target branch
- Worktree resources released

**Allowed transitions:**
- → DEPLOYING
- → DEPLOYED (if deploy is automatic or not applicable)

**Owner:** Hermes

---

#### STATE-25: DEPLOYING

**Entry criteria:** Deployment is in progress.

**Required records:**
- Deployment target (staging, production)
- Deployment method
- Feature flag status (if applicable)

**Permitted actions:**
- Deployment executes
- Hermes monitors deployment health

**Exit criteria:**
- Deployment confirmed successful

**Allowed transitions:**
- → DEPLOYED
- → MERGED (deploy failed; rollback to merge state)

**Owner:** Hermes (orchestration)

---

#### STATE-26: DEPLOYED

**Entry criteria:** Deployment confirmed successful.

**Required records:**
- Deployment confirmation
- Deployment timestamp
- Health check results

**Permitted actions:**
- Hermes begins observation period

**Exit criteria:**
- Health checks pass

**Allowed transitions:**
- → OBSERVING

**Owner:** Hermes

---

#### STATE-27: OBSERVING

**Entry criteria:** Post-deployment observation period is active.

**Required records:**
- Observation start timestamp
- Monitoring configuration
- Key metrics baseline

**Permitted actions:**
- Hermes monitors for regressions, errors, or anomalies
- Hermes may trigger rollback if regression detected

**Exit criteria:**
- Observation period completed without issues
- OR a regression is detected (→ rollback)

**Allowed transitions:**
- → RECORDING (observation period clean)
- → MERGED (regression detected; rollback triggered)

**Owner:** Hermes

---

#### STATE-28: RECORDING

**Entry criteria:** Task execution is complete; learning and records phase begins.

**Required records:**
- Post-task learning record (per 05_Learning_OS/POST_TASK_LEARNING_TEMPLATE.md)
- Builder scorecard update (per BUILDER_SCORECARD_TEMPLATE.md)
- Regression records (if any defects found)
- Decision records (if any decisions made during execution)

**Permitted actions:**
- Hermes populates learning record
- Hermes updates builder scorecard
- Hermes creates regression records
- Hermes archives evidence package

**Exit criteria:**
- All records created and stored
- Scorecard updated

**Allowed transitions:**
- → CLOSED

**Owner:** Hermes

---

#### STATE-29: CLOSED

**Entry criteria:** All records complete; task is finished.

**Required records:**
- Closure record with `outcome` (SUCCESS, PARTIAL, FAILED, CANCELLED, SUPERSEDED)
- Final evidence package archived
- All learning artifacts stored

**Permitted actions:**
- Hermes releases all resources
- Hermes reports task outcome to Amjad
- Task is removed from active task board
- Task is archived in task history

**Exit criteria:**
- Task is terminal — no further transitions

**Allowed transitions:**
- None (terminal state)

**Owner:** Hermes

---

### 2.2 Exception States (8)

#### EXC-01: NEEDS_CLARIFICATION

**Trigger:** Request, classification, or contract details are ambiguous.

**Entry from:** REQUESTED, CLASSIFYING, CONTRACT_DRAFTED

**Required records:**
- Specific questions for Amjad
- What is unclear and why
- Potential interpretations

**Resolution:** Amjad provides clarification → return to source state

**Allowed transitions:**
- → REQUESTED (clarified)
- → CANCELLED (Amjad cancels)

---

#### EXC-02: NEEDS_DECISION

**Trigger:** Classification reveals a conflict with a locked decision or an architectural choice that requires Amjad authority.

**Entry from:** CLASSIFYING

**Required records:**
- Conflicting locked decisions (if any)
- Decision options presented to Amjad
- Hermes recommendation

**Resolution:** Amjad makes decision → return to CLASSIFYING

**Allowed transitions:**
- → CLASSIFIED (decision made)
- → CANCELLED (Amjad decides not to proceed)

---

#### EXC-03: BLOCKED_BY_DEPENDENCY

**Trigger:** Task depends on another in-flight task, external system availability, or a prerequisite that is not yet met.

**Entry from:** CONTRACT_DRAFTED

**Required records:**
- Dependency identifier (task ID, system name, commit SHA)
- Expected resolution date/time
- Impact on contract

**Resolution:** Dependency resolves → return to CONTRACT_DRAFTED; contract may need amendment

**Allowed transitions:**
- → CONTRACT_DRAFTED (unblocked)
- → CANCELLED (dependency unresolvable)

---

#### EXC-04: BLOCKED_BY_EXTERNAL

**Trigger:** External service is unavailable, API is down, or third-party dependency is blocking progress.

**Entry from:** IN_PROGRESS, IMPLEMENTED, SELF_CHECKED

**Required records:**
- External service/API name
- Error details
- Expected resolution time
- Whether work can continue in other areas

**Resolution:** External issue resolves → return to IN_PROGRESS

**Allowed transitions:**
- → IN_PROGRESS (resolved)
- → CANCELLED (external dependency permanently unavailable)

---

#### EXC-05: SCOPE_EXCEEDED

**Trigger:** Builder reports (or Hermes detects) that the work requires changes beyond the contract's `allowed_files`, `max_files`, `max_lines`, or `must_remain_unchanged` boundaries.

**Entry from:** IN_PROGRESS

**Required records:**
- What was attempted
- What boundary was crossed
- What additional scope is required
- Whether the scope change is essential or optional

**Resolution:** Hermes evaluates:
- If essential and low-risk: amend contract, re-approve, re-dispatch
- If complex: return to REQUESTED for re-scoping
- If builder error: re-dispatch with stricter instructions

**Allowed transitions:**
- → CONTRACT_DRAFTED (amended; re-approval)
- → REQUESTED (re-scoping required)
- → IN_PROGRESS (builder correction; no contract change needed)

---

#### EXC-06: STOP_CONDITION_TRIGGERED

**Trigger:** A contract-defined stop condition is detected during execution.

**Entry from:** IN_PROGRESS

**Required records:**
- Which stop condition triggered
- Current state of work
- Whether work is salvageable
- Whether contract needs amendment or task needs cancellation

**Resolution:** Hermes evaluates severity:
- **IMMEDIATE** severity → builder must stop now; Hermes evaluates next action
- **AFTER_CURRENT_STEP** → builder may complete current step, then stop

**Allowed transitions:**
- → REQUESTED (re-scoped; resolvable)
- → CANCELLED (unresolvable)

---

#### EXC-07: REPAIR_FAILED

**Trigger:** Builder has attempted 2 repair cycles and findings still exist.

**Entry from:** FIXING (after 2 cycles)

**Required records:**
- Both repair cycle results
- Remaining unresolved findings
- Why repairs failed

**Resolution:** Hermes evaluates:
- Escalate to fallback builder (if available)
- Return to REQUESTED for re-scoping
- Cancel task

**Allowed transitions:**
- → REQUESTED (re-scoped for different approach)
- → CANCELLED (unresolvable by any builder)

---

#### EXC-08: SUPERSEDED

**Trigger:** A newer contract obsoletes this one (e.g., a higher-priority task renders this one irrelevant).

**Entry from:** APPROVED, READY

**Required records:**
- Superseding task ID
- Reason for supersession
- What work is preserved vs. discarded

**Resolution:** Task is closed with `SUPERSEDED` outcome.

**Allowed transitions:**
- → CLOSED (outcome: SUPERSEDED)

---

#### EXC-09: CANCELLED

**Trigger:** Amjad cancels the task, or Hermes determines it is unresolvable.

**Entry from:** ANY state except CLOSED

**Required records:**
- Cancellation reason
- Cancellation authority (AMJAD or HERMES)
- Work preservation decision (keep branch? delete branch?)
- Any learning to extract

**Resolution:** Task is closed with `CANCELLED` outcome.

**Allowed transitions:**
- → CLOSED (outcome: CANCELLED)

---

### 2.3 Additional Internal Transitions

#### AMJAD_CHANGES_REQUESTED

**Entry criteria:** Amjad requests changes after preview.

**Required records:**
- Change requests from Amjad
- Priority and scope of changes

**Resolution:** If within existing contract scope → ADJUSTING. If new scope → contract amendment.

**Allowed transitions:**
- → ADJUSTING (within scope)
- → CONTRACT_DRAFTED (amendment needed)

---

#### ADJUSTING

**Entry criteria:** Builder is implementing Amjad-requested adjustments.

**Entry from:** PREVIEW_READY (via AMJAD_CHANGES_REQUESTED)

**Required records:**
- Adjustment list
- Adjustment dispatch timestamp

**Resolution:** Adjustments complete → SELF_CHECKED → gate/review pipeline

**Allowed transitions:**
- → SELF_CHECKED (adjustments done)

---

## 3. Transition Authority

**Hermes owns ALL state transitions.** This is non-negotiable.

| Role | Can... | Cannot... |
|---|---|---|
| Hermes | Initiate any transition, approve R1 contracts, triage findings, cancel tasks, amend contracts | — |
| Amjad | Approve/reject R2-R4 contracts, approve/reject previews, request changes, cancel tasks | Transition task state directly |
| Builder (Kimi K3 / Codex) | Report implementation complete, trigger stop conditions, request clarification | Transition task state |
| Reviewer (Claude Code) | Submit findings | Transition task state, instruct builder directly |
| CI | Report gate results | Transition task state |

---

## 4. Event Log

Every transition MUST be logged to `.hermes/events/task-{task_id}.jsonl`:

```jsonl
{"ts":"2026-07-31T10:00:00Z","task_id":"TASK-AVOA-0001","from":"REQUESTED","to":"CONTEXT_RETRIEVED","by":"HERMES","reason":"Context loaded"}
{"ts":"2026-07-31T10:05:00Z","task_id":"TASK-AVOA-0001","from":"CONTEXT_RETRIEVED","to":"CLASSIFYING","by":"HERMES","reason":"Classification started"}
```

---

## 5. Lifecycle Rules

1. **No state skipping.** Every state must be entered and exited in order (exception states are forks, not skips).
2. **No self-transition without justification.** A state may only transition to itself (e.g., DISPATCHING → DISPATCHING for re-dispatch) with a logged reason.
3. **No resurrection.** CLOSED is terminal. Once closed, the task cannot re-enter any state.
4. **Parallel gate.** A task can only be `parallel_eligible: true` if it enters DISPATCHING while another task is already IN_PROGRESS (per 09_PARALLEL_EXECUTION_STANDARD).
5. **Repair limit.** Maximum 2 repair cycles. Third failure triggers REPAIR_FAILED.
6. **Stop conditions are sacred.** Any triggered stop condition forces the builder to halt. Hermes decides the path forward.
7. **Amjad is the final gate.** No production-facing change merges without AMJAD_APPROVED (R1 tasks may be auto-approved if Amjad has delegated).

---

## 6. Mapping: v1.0 to v3.1

| v1.0 State (18 states) | v3.1 State (22 + 8 exception) | Notes |
|---|---|---|
| REQUESTED | REQUESTED | No change |
| CONTEXT_RETRIEVED | CONTEXT_RETRIEVED | No change |
| CLASSIFIED | CLASSIFYING + CLASSIFIED | Split into two states: classification process + classification complete |
| CONTRACT_DRAFTED | CONTRACT_DRAFTED | No change |
| APPROVED | APPROVED | No change |
| READY | READY | No change |
| — | DISPATCHING | **NEW** — explicit dispatch tracking |
| IN_PROGRESS | IN_PROGRESS | No change |
| BUILT | IMPLEMENTED | Renamed for clarity |
| AUTOMATED_CHECKED | SELF_CHECKED | Renamed; builder self-check distinct from CI gates |
| COMMITTED | COMMITTED | No change |
| — | GATE_CHECKING | **NEW** — explicit CI gate execution state |
| — | GATES_PASSED | **NEW** — explicit gate completion state |
| REVIEWED | REVIEWING + REVIEWED | Split into two states |
| — | FINDINGS_CLEAN / FINDINGS_FOUND | **NEW** — explicit findings triage |
| — | FIXING | **NEW** — explicit repair cycle state |
| — | CORRECTIONS_APPLIED | **NEW** — explicit post-repair verification |
| PREVIEW_READY | PREVIEW_READY | No change |
| HUMAN_APPROVED | AMJAD_APPROVED + AMJAD_CHANGES_REQUESTED + ADJUSTING | Expanded for change-request flow |
| MERGED | READY_TO_MERGE + MERGED | Split: merge approval + merge execution |
| DEPLOYED_OR_HELD | DEPLOYING + DEPLOYED | Split: deployment + deployment confirmed |
| OBSERVED | OBSERVING | Renamed |
| LEARNED | RECORDING | Renamed for clarity |
| CLOSED | CLOSED | No change |

**New exception states (8):**
- NEEDS_CLARIFICATION
- NEEDS_DECISION
- BLOCKED_BY_DEPENDENCY
- BLOCKED_BY_EXTERNAL
- SCOPE_EXCEEDED
- STOP_CONDITION_TRIGGERED
- REPAIR_FAILED
- SUPERSEDED

---

## 7. Relationship to Other Documents

| Document | Relationship |
|---|---|
| 04_TASK_CONTRACT_STANDARD | Contract `status` field tracks this state machine |
| 07_RISK_CLASSIFICATION | Risk level determines required gates and approval path |
| 08_PROTECTED_ZONES | SCOPE_EXCEEDED is triggered by protected zone violations |
| 09_PARALLEL_EXECUTION | Parallel execution depends on task state compatibility |
| 15_TECHNICAL_REVIEW | REVIEWING state feeds into review findings protocol |
| 18_EVIDENCE_AND_COMPLETION | Evidence package assembled before PREVIEW_READY |

---

*Document 06 of 26. See 00_HERMES_OS_V3_1_INDEX.md for the full package.*