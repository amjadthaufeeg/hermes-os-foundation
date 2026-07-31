# 25 — Pilot and Rollout Plan

**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 24_MIGRATION_PLAN, all Hermes OS v3.1 documents
**Feeds into:** 26_IMPLEMENTATION_BACKLOG

---

## 1. Purpose

This document defines the pilot program that validates each major capability block before it enters general use, and the gradual rollout strategy that expands Hermes OS v3.1 from a single-builder workflow to full multi-agent orchestration.

Every pilot must produce verifiable evidence before the next rollout phase begins.

---

## 2. Rollout Strategy: Gradual Expansion

```
Phase 0 (Current)     Phase 1 (HOS-1)    Phase 2 (HOS-2)    Phase 3 (HOS-5)
─────────────────     ────────────────    ────────────────    ────────────────
Single-builder        Single-builder      Single-builder      Read-only parallel
No contracts          + Task contracts    + Design Studio     + PEC pilot
No protected zones    + CI safety gates   + UI contracts      + Research tasks
No evidence           + Decision register + AVOA audit        + Docs tasks
No CC                 + Evidence packages                     + Analysis tasks

     Phase 4 (HOS-6)      Phase 5 (HOS-7)      Phase 6 (HOS-8)
     ────────────────     ────────────────     ────────────────
     Controlled UI        Full specialist      Operational
     parallelism          parallelism          maturity
     + UI subtasks        + Dependency chains  + Scorecard routing
     + File ownership     + Multi-agent coord  + Auto-rollback
     + Integration mgr    + Abort/cleanup      + Analytics
```

**Rollout gate:** Each phase must complete its pilot before the next phase enters general use. Hermes begins using new capabilities on real tasks only after pilot evidence is approved.

---

## 3. Pilot 1: Repository-Safety & Single-Builder Flow (HOS-1)

### 3.1 Objective

Validate that HOS-1 governance artifacts (task contracts, risk classification, CI safety gates, evidence collection, decision register) can be applied to a real feature task without disrupting the existing single-builder workflow.

### 3.2 Preconditions

- [ ] All HOS-1 schemas validated and committed
- [ ] CI gates configured and passing on `main`
- [ ] Protected-zone policy defined
- [ ] Decision register bootstrapped with 17 records
- [ ] Amjad approval to proceed

### 3.3 Scope

One real feature task executed end-to-end with HOS-1 governance applied. The task should be a self-contained feature that touches 3–10 files, rated R1 or R2, with no database changes.

### 3.4 Selected Task Characteristics

| Criterion | Requirement |
|---|---|
| Task type | Feature addition or controlled refactor |
| File count | 3–10 files |
| Risk level | R1 or R2 |
| Database changes | None |
| Protected zone touches | None |
| Dependencies | Self-contained (no cross-task coupling) |

### 3.5 Pilot Workflow

```
1. Hermes creates task contract        → contract validated against schema
2. Hermes classifies risk (R1/R2)     → risk level recorded in contract
3. Hermes assigns to builder agent     → agent accepted assignment
4. Builder creates feature branch      → branch follows naming convention
5. Builder implements feature          → code changes in allowed scope only
6. Builder opens PR                    → CI gates run automatically
7. CI: schema-validation passes        → no schema regressions
8. CI: changed-file-report runs        → all changes enumerated
9. CI: scope-checker passes            → no out-of-scope files modified
10. CI: protected-zone-checker passes  → no protected files touched
11. Hermes dispatches review           → review agent produces findings per Doc 15
12. Review triage complete             → findings accepted/rejected
13. Evidence package assembled         → per Doc 18 standard
14. Decision recorded                  → added to decision register
15. PR approved and merged             → merge to integration branch
```

### 3.6 Expected Evidence

| Evidence Item | Format |
|---|---|
| Task contract | JSON, validated |
| Risk classification | Field in contract |
| CI gate results | All 4 gates passing |
| Changed-file manifest | CI artifact |
| Review report | JSON per Doc 15 |
| Evidence package | Bundle per Doc 18 |
| Decision record | JSON per Doc 16 |

### 3.7 Success Criteria

- [ ] Task contract created, validated, and committed
- [ ] Risk level correctly classified (R1 or R2)
- [ ] All 4 CI gates pass on the PR
- [ ] Scope checker approves all changed files
- [ ] Protected-zone checker confirms no violation
- [ ] Review produces findings report with at least 0 accepted findings
- [ ] Evidence package contains all required artifacts
- [ ] Decision record appended to register
- [ ] PR merged successfully
- [ ] No disruption to existing workflow

### 3.8 Failure Criteria

| Failure | Action |
|---|---|
| CI gate fails on valid change | Fix gate configuration, re-run pilot |
| Scope checker blocks legitimate file | Adjust allowed-scope definition in contract |
| Protected-zone false positive | Fix protected-zone policy, re-run pilot |
| Evidence package incomplete | Add missing artifact, document gap |
| Builder workflow disrupted | Revert HOS-1 artifacts, return to baseline |

### 3.9 Rollback

If Pilot 1 fails: remove CI gates, archive `.hermes/` directory. Return to pre-HOS-1 workflow. Root-cause the failure before re-attempting.

---

## 4. Pilot 2: Design Studio (HOS-2 + HOS-4)

### 4.1 Objective

Validate the Design Studio workflow: UI contract creation, design review protocol, AVOA design system application, and Command Center visibility of design tasks.

### 4.2 Preconditions

- [ ] Pilot 1 completed successfully
- [ ] HOS-2 schemas and templates committed
- [ ] AVOA design system audit complete
- [ ] Command Center MVP deployed (HOS-4)
- [ ] Design Studio roles defined

### 4.3 Scope

One real UI task (frontend component, page, or design system update) executed with full Design Studio workflow: UI contract, design agent implementation, visual review, and Command Center tracking.

### 4.4 Selected Task Characteristics

| Criterion | Requirement |
|---|---|
| Task type | UI component or layout change |
| Visual scope | Has visible rendering (can be screenshotted) |
| Design tokens | Uses AVOA design tokens |
| Risk level | R1 or R2 |

### 4.5 Pilot Workflow

```
1. Hermes creates UI contract           → contract includes visual spec, token references
2. Hermes assigns to Frontend Design    → Design Agent receives UI contract
   Agent
3. Design Agent implements component    → uses AVOA design tokens
4. Design Agent captures screenshots    → before/after visual evidence
5. Hermes dispatches UI/UX review       → Review Agent evaluates visual fidelity
6. Review produces screenshot evidence  → comparison against UI contract spec
7. Accessibility check runs             → Accessibility Agent validates WCAG compliance
8. Evidence package assembled           → includes screenshots, review findings
9. Task visible in Command Center       → task board shows design task lifecycle
10. PR approved and merged              → merge with design review sign-off
```

### 4.6 Expected Evidence

| Evidence Item | Format |
|---|---|
| UI contract | JSON per Doc 05 |
| Before/after screenshots | PNG images |
| Design review report | JSON with visual findings |
| Accessibility check results | JSON |
| Visual QA sign-off | Boolean + reviewer identity |
| CC task lifecycle events | Event log entries |

### 4.7 Success Criteria

- [ ] UI contract created and validated
- [ ] Component uses AVOA design tokens (verified by audit tool)
- [ ] Before/after screenshots show visual change
- [ ] Design review produces findings
- [ ] Accessibility check passes (WCAG AA minimum)
- [ ] Task visible in Command Center task board
- [ ] All events emitted to CC backend

### 4.8 Failure Criteria

| Failure | Action |
|---|---|
| UI contract too vague to implement | Refine UI contract schema, re-run pilot |
| AVOA tokens not applied | Verify token audit tooling, re-run |
| Screenshots insufficient for review | Define minimum screenshot requirements |
| Accessibility check fails | Fix component, re-run (this is a real finding, not pilot failure) |

### 4.9 Rollback

Archive Design Studio role definitions. Revert to ad-hoc design workflow. CC remains operational.

---

## 5. Pilot 3: Read-Only Parallelism (HOS-5)

### 5.1 Objective

Validate the Parallel Execution Controller (PEC) for read-only tasks: parallel research, documentation, or analysis across 2–3 agents with Hermes orchestrating decomposition and integration.

### 5.2 Preconditions

- [ ] Pilots 1–2 completed successfully
- [ ] PEC deployed and configured
- [ ] Worktree manager operational (Doc 10)
- [ ] At least 2 agents available for parallel assignment

### 5.3 Scope

One read-only task decomposed into 2–3 parallel subtasks. Each subtask is assigned to a different agent. Hermes integrates results into a single deliverable.

### 5.4 Selected Task Characteristics

| Criterion | Requirement |
|---|---|
| Task type | Research, documentation, or code analysis |
| Write operations | **None.** Read-only. |
| Decomposability | Can be split into 2–3 independent subtasks |
| Risk level | R1 |
| Agent count | 2–3 |

### 5.5 Pilot Workflow

```
1. Hermes receives research/documentation task
2. PEC screens task: all hard gates pass (R1, no writes, no protected zones)
3. PEC decomposes task into 2–3 independent subtasks
4. PEC allocates worktrees per subtask
5. Hermes assigns subtasks to agents:
   - Subtask A → Agent 1 (e.g., Research Agent)
   - Subtask B → Agent 2 (e.g., Kimi K3)
   - Subtask C → Agent 3 (e.g., Codex) [optional]
6. All agents work concurrently in their worktrees
7. Each agent produces evidence package
8. Hermes integrates results into unified deliverable
9. Hermes validates integration: no contradictions, no gaps
10. CC shows parallel task with multi-agent assignment
```

### 5.6 Expected Evidence

| Evidence Item | Format |
|---|---|
| Decomposition plan | PEC output: subtask contracts, dependency graph |
| Per-agent evidence packages | One per subtask |
| Integration report | Hermes's unified deliverable |
| CC parallel task view | Screenshot of multi-agent task in dashboard |
| Worktree allocation log | Which worktree per agent |

### 5.7 Success Criteria

- [ ] PEC correctly classifies task as eligible for read-only parallelism
- [ ] Decomposition produces 2–3 independent subtasks with zero file overlap
- [ ] All agents complete their subtasks within expected timeframe
- [ ] No agent attempts to write to another agent's worktree
- [ ] Integration produces coherent, non-contradictory results
- [ ] CC displays parallel task correctly (multi-agent assignment visible)
- [ ] Deliverable quality meets or exceeds single-agent baseline

### 5.8 Failure Criteria

| Failure | Action |
|---|---|
| PEC rejects eligible task | Fix eligibility rules, re-run |
| Agents overlap in work | Fix worktree isolation, re-run |
| Integration produces contradictions | Improve integration protocol, re-run |
| Agent stalls or fails | Abort parallel run, complete sequentially |
| CC doesn't show parallel status | Fix CC event handling |

### 5.9 Rollback

Abort parallel task. Complete sequentially. Disable PEC for read-only tasks if failure pattern emerges.

---

## 6. Pilot 4: Controlled UI Parallelism (HOS-6)

### 6.1 Objective

Validate parallel code editing for UI tasks with strict file-ownership partitioning. Two agents build separate UI components simultaneously; Hermes enforces file ownership and orchestrates integration.

### 6.2 Preconditions

- [ ] Pilots 1–3 completed successfully
- [ ] File-ownership partitioning operational
- [ ] Collision detection CI gate active
- [ ] Integration manager deployed

### 6.3 Scope

One UI feature task decomposed into 2 parallel component subtasks. Each agent builds one component in a separate file set. Hermes integrates and verifies.

### 6.4 Selected Task Characteristics

| Criterion | Requirement |
|---|---|
| Task type | UI feature with 2+ independent components |
| File overlap | Zero — components in separate files |
| Risk level | R1 or R2 |
| Agent count | 2 |
| Integration | Components share a parent layout (integration risk) |

### 6.5 Pilot Workflow

```
1. Hermes creates task contract for UI feature
2. PEC decomposes: Component A (Agent 1), Component B (Agent 2)
3. PEC defines file ownership:
   - Agent 1: src/components/ComponentA.tsx, src/components/ComponentA.test.tsx
   - Agent 2: src/components/ComponentB.tsx, src/components/ComponentB.test.tsx
4. Collision detection confirms zero file overlap
5. Both agents work concurrently in separate worktrees
6. Each agent opens PR for their component
7. CI: collision-detection gate verifies no cross-ownership access
8. Hermes performs integration: both PRs merged into integration branch
9. Integration build passes
10. Integration tests pass (both components render correctly together)
11. Evidence packages assembled per agent
12. CC shows parallel task lifecycle
```

### 6.6 Expected Evidence

| Evidence Item | Format |
|---|---|
| File-ownership partition map | PEC output |
| Per-agent PRs | GitHub PR links |
| Collision-detection results | CI artifact: no violations |
| Integration build result | CI pass |
| Integration test result | All tests pass |
| Per-agent evidence packages | Bundles per Doc 18 |
| Screenshots: both components | Before/after integration |

### 6.7 Success Criteria

- [ ] File-ownership correctly partitions all files (zero overlap)
- [ ] Collision detection gate passes on both PRs
- [ ] Both agents complete independently
- [ ] Integration merge produces no conflicts
- [ ] Build passes after integration
- [ ] All tests pass after integration
- [ ] Components render correctly together
- [ ] No agent accessed another agent's files

### 6.8 Failure Criteria

| Failure | Action |
|---|---|
| Collision detection catches real overlap | Fix file-ownership partitioning, re-run |
| Integration produces merge conflicts | Adjust component boundaries, re-run |
| Integration build fails | Debug dependency issues, re-run |
| Tests fail after integration | Fix component interactions, re-run |

### 6.9 Rollback

Merge order: Component A first, then Component B sequentially. Disable UI parallelism if integration failures persist.

---

## 7. Pilot 5: Serialized R4 Task (HOS-7)

### 7.1 Objective

Validate full parallel decomposition with dependency chains on an R3 task. This pilot also validates the abort-and-cleanup mechanism by intentionally injecting a subtask failure.

### 7.2 Preconditions

- [ ] Pilots 1–4 completed successfully
- [ ] Full PEC decomposition operational
- [ ] Dependency graph management operational
- [ ] Abort and cleanup mechanism tested in isolation
- [ ] At least 3 agents available

### 7.3 Scope

One R3 feature task decomposed into 3 parallel subtasks with a dependency chain (Subtask B depends on Subtask A; Subtask C is independent). Validate dependency enforcement, multi-agent coordination, and integration sequencing.

**Note:** R4 tasks remain sequential-only per Doc 09. This pilot title refers to serializing the task contract through the full HOS-7 pipeline, not to running an R4 task in parallel. An R4 task may still be executed under HOS-7 governance — but sequentially, with full evidence collection and decision tracking.

### 7.4 Selected Task Characteristics

| Criterion | Requirement |
|---|---|
| Task type | Full-stack feature (frontend + backend) |
| Subtask count | 3 (1 with dependency, 2 independent) |
| Risk level | R3 |
| Database changes | None (migrations excluded from parallel) |
| Dependencies | Subtask B depends on Subtask A |

### 7.5 Pilot Workflow

```
1. Hermes creates task contract for full-stack feature
2. PEC decomposes into 3 subtasks:
   - Subtask A: Backend API endpoint (Agent: Kimi K3)
   - Subtask B: Frontend component consuming API (Agent: Codex) [DEPENDS ON A]
   - Subtask C: Documentation update (Agent: Documentation Agent) [INDEPENDENT]
3. PEC creates dependency graph: A → B, C parallel to both
4. PEC allocates worktrees
5. Agents A and C start immediately
6. Agent B waits for Agent A completion signal
7. Agent A completes → PEC signals Agent B
8. Agent B starts, completes
9. Hermes sequences integration: A → B → C
10. Integration tests pass (backend + frontend + docs)
11. Abort test: inject failure in Subtask A on second run
12. Verify PEC aborts B, preserves C
13. Verify cleanup restores worktrees to clean state
```

### 7.6 Expected Evidence

| Evidence Item | Format |
|---|---|
| Decomposition plan with dependency graph | PEC output (DAG visualization) |
| Per-agent evidence packages | 3 bundles |
| Dependency enforcement log | Timestamps: A completed before B started |
| Integration sequence log | Order: A → B → C |
| Abort test evidence | PEC abort log, cleanup confirmation |
| CC full DAG view | Screenshot |

### 7.7 Success Criteria

- [ ] PEC correctly models dependency: A → B
- [ ] Agent B does not start until Agent A completes
- [ ] Agent C runs independently in parallel
- [ ] Integration sequence respects dependencies
- [ ] Abort on A failure correctly halts B
- [ ] Abort does not affect independent subtask C
- [ ] Cleanup restores clean worktree state
- [ ] CC shows full dependency graph

### 7.8 Failure Criteria

| Failure | Action |
|---|---|
| B starts before A completes | Fix dependency enforcement, re-run |
| Abort does not halt dependent subtasks | Fix abort propagation, re-run |
| Abort affects independent subtasks | Fix abort scope, re-run |
| Cleanup leaves dirty state | Fix cleanup procedure, re-run |

### 7.9 Rollback

Disable full decomposition. Revert to HOS-6 UI-parallelism model. All tasks complete sequentially.

---

## 8. Rollout Timeline

```
Phase 0: CURRENT STATE
    │
    ▼
Pilot 1 (HOS-1): Repository Safety ──────▶ Single-builder + governance
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
Pilot 2 (HOS-2+4): Design Studio + CC     HOS-3 (parallel): CC Data Foundation
    │                                      │
    └──────────────────────────────────────┘
                      │
                      ▼
Pilot 3 (HOS-5): Read-Only Parallelism ──▶ Research + Docs parallel
    │
    ▼
Pilot 4 (HOS-6): Controlled UI Parallel ─▶ UI components parallel
    │
    ▼
Pilot 5 (HOS-7): Full Parallelism ────────▶ Multi-agent full-stack parallel
    │
    ▼
HOS-8: Operational Maturity ──────────────▶ Scorecard routing + analytics
```

---

## 9. Rollout Governance

### 9.1 Gate Criteria for Proceeding

Before advancing to the next rollout phase, all of the following must be true:

- [ ] Current pilot completed with all success criteria met
- [ ] No unresolved failure incidents from current phase
- [ ] Evidence package reviewed and accepted by Amjad
- [ ] Rollback tested and documented for current phase
- [ ] Next phase's dependencies satisfied
- [ ] Amjad approval to proceed

### 9.2 Emergency Rollback Protocol

At any phase, if a critical issue is discovered:

1. **Halt:** Stop all active tasks using the new capability
2. **Assess:** Determine whether the issue is local (one task) or systemic
3. **Rollback:** If systemic, revert to previous phase configuration
4. **Root-cause:** Document the failure in the decision register
5. **Fix:** Address root cause before re-enabling
6. **Re-pilot:** Re-run the pilot for the affected capability

### 9.3 Amjad Authority

Amjad may at any time:

- Halt any pilot or rollout phase
- Require additional pilot runs
- Skip or reorder phases (with documented rationale)
- Approve or reject evidence packages
- Authorize emergency overrides

---

*End of Document 25 — Pilot and Rollout Plan*