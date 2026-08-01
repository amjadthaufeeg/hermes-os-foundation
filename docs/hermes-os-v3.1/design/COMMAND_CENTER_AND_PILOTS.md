# Command Center Wireframes

**Status:** HOS-2 Planning | **Note:** Design only — no implementation

---

## Information Architecture

```
Hermes Command Center
├── Executive Overview
├── Portfolio
├── Product
├── Design Studio
├── Engineering Mission Control
│   ├── Active Tasks
│   ├── Agents & Worktrees
│   ├── File Ownership
│   └── Integration Queue
├── Quality & Evidence
│   ├── Gate Results
│   ├── Review Findings
│   └── Fixture Health
├── Commercial Safety
├── Knowledge
├── Releases
└── Operations
```

---

## Dashboard Wireframes (Text-Based)

### Executive Overview
```
┌─────────────────────────────────────────────────────────┐
│ EXECUTIVE OVERVIEW                    Last updated: 2m ago │
├──────────────────┬──────────────────┬──────────────────┤
│ ACTIVE TASKS     │ BLOCKED          │ READY FOR AMJAD  │
│ 3                │ 1                │ 2                │
│ [View all →]     │ [Unblock →]      │ [Review →]       │
├──────────────────┴──────────────────┴──────────────────┤
│ RECENT ACTIVITY                                         │
│ ● TASK-UI-007 merged (2h ago)                          │
│ ● TASK-HOS-001.1 closed (4h ago)                       │
│ ● Review submitted for TASK-AVOA-012 (6h ago)           │
├─────────────────────────────────────────────────────────┤
│ CI STATUS: ✅ All checks passing                        │
│ PROTECTED ZONES: ✅ No violations                       │
│ LAST DEPLOY: N/A (pre-production)                       │
└─────────────────────────────────────────────────────────┘
```

### Engineering Mission Control
```
┌─────────────────────────────────────────────────────────┐
│ ENGINEERING MISSION CONTROL                              │
├─────────────────────────────────────────────────────────┤
│ PARENT TASK: TASK-AVOA-014 — Quote Engine UI Reset      │
│ ├── Subtask 1: Wizard (Kimi K3) ✅ COMPLETE              │
│ ├── Subtask 2: Review (Kimi K3) ⏳ IN PROGRESS           │
│ └── Subtask 3: Negotiation 🔒 LOCKED                    │
├─────────────────────────────────────────────────────────┤
│ AGENTS & WORKTREES                                       │
│ ┌──────────┬──────────────┬──────────┬─────────────┐   │
│ │ Agent    │ Worktree     │ Task     │ Status       │   │
│ ├──────────┼──────────────┼──────────┼─────────────┤   │
│ │ Kimi K3  │ wt-AVOA-014  │ Subtask2 │ Building     │   │
│ │ Scout    │ (read-only)   │ —       │ Idle         │   │
│ └──────────┴──────────────┴──────────┴─────────────┘   │
│                                                         │
│ FILE OWNERSHIP: No conflicts detected                    │
│ INTEGRATION QUEUE: Empty                                 │
└─────────────────────────────────────────────────────────┘
```

### Quality & Evidence
```
┌─────────────────────────────────────────────────────────┐
│ QUALITY & EVIDENCE                                       │
├─────────────────────────────────────────────────────────┤
│ GATE RESULTS (TASK-AVOA-014)                             │
│ ✅ Build  ✅ TypeCheck  ✅ Lint  ✅ Tests                 │
│ ✅ Scope  ✅ ProtectedZones  ✅ Screenshots               │
│ ⏳ Independent Review (dispatched 30m ago)               │
├─────────────────────────────────────────────────────────┤
│ FIXTURE HEALTH                                           │
│ Pricing: 12/12 ✅  Occupancy: N/A  Tax: N/A              │
│ Offers: N/A       Commission: N/A                        │
└─────────────────────────────────────────────────────────┘
```

### Design Dashboard
```
┌─────────────────────────────────────────────────────────┐
│ DESIGN STUDIO                                            │
├─────────────────────────────────────────────────────────┤
│ DESIGN BRIEFS: 2 active                                  │
│ ● Quote Detail redesign (Wireframe stage)                │
│ ● Dashboard layout (Research stage)                      │
│                                                         │
│ REVIEW QUEUE: 1 pending                                  │
│ ● Navigation component — awaiting Visual QA              │
│                                                         │
│ DESIGN SYSTEM                                            │
│ Components: 25 specified, 4 implemented                  │
│ Last update: 2 days ago                                  │
└─────────────────────────────────────────────────────────┘
```

### Commercial Safety
```
┌─────────────────────────────────────────────────────────┐
│ COMMERCIAL SAFETY                                        │
├─────────────────────────────────────────────────────────┤
│ PROTECTED ZONES: ✅ All intact                           │
│ ● Pricing engine: 0 changes                             │
│ ● Offers: 0 changes                                     │
│ ● Occupancy: 0 changes                                  │
│ ● Tax/Commission: 0 changes                             │
│                                                         │
│ R4 TASKS: 0 active                                       │
│ FIXTURE HEALTH: ✅ All passing                           │
│ AUDIT LOG: 0 events today                                │
└─────────────────────────────────────────────────────────┘
```

### Operations Dashboard
```
┌─────────────────────────────────────────────────────────┐
│ OPERATIONS                                               │
├─────────────────────────────────────────────────────────┤
│ CI/CD                                                    │
│ ● Main: ✅ Passing (last run 5m ago)                     │
│ ● Feature branches: 2 active, all passing                │
│                                                         │
│ DEPLOYMENTS                                              │
│ ● Last: N/A (pre-production)                             │
│ ● Rollback packages: 3 available                         │
│                                                         │
│ PREVIEW ENVIRONMENTS: None active                        │
│ MONITORING: N/A (pre-production)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Pilot Candidates

### Candidate 1: Quote Wizard (Slice 1-6)
- **Current problems:** Inconsistent spacing, no loading states, no error handling display
- **Business value:** Core AVOA workflow; most-used screen
- **Risk:** R2 (established behaviour, no logic changes)
- **Scope:** Apply Design System V1 tokens, add states
- **Recommendation:** **Strong** — highest impact

### Candidate 2: Quote Detail (Slice 7)
- **Current problems:** Being built now; opportunity to apply design system from scratch
- **Business value:** Pricing display — commercial importance
- **Risk:** R2-R3 (pricing data displayed)
- **Scope:** Full Design System application
- **Recommendation:** **Conditional** — wait for Slice 7 completion

### Candidate 3: Navigation Component
- **Current problems:** Basic implementation, no responsive polish
- **Business value:** Used on every page
- **Risk:** R1 (presentation only)
- **Scope:** Redesign with Design System tokens
- **Recommendation:** **Good** — low risk, high visibility

---

*Part of Hermes Product OS v3.1 — HOS-2.*