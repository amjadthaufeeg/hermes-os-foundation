# 21 — Hermes Command Center PRD

**Status:** SPECIFICATION  
**Version:** 3.1  

## Purpose

The Hermes Command Center is the operational interface for the Hermes Engineering OS. It is NOT merely a chat interface — it is an evidence-backed dashboard displaying real engineering state from actual task, evidence, review, and deployment records.

---

## Module Overview

| # | Module | Users | Goal |
|---|---|---|---|
| 1 | **Executive Overview** | Amjad | High-level project health, active tasks, blocked items, decisions pending |
| 2 | **Portfolio** | Amjad, Hermes | Multi-project view: AVOA, Maldives Experts, Nauvis Labs |
| 3 | **Product** | Amjad | Feature disposition, roadmap, specifications, business rules |
| 4 | **Design Studio** | Design Studio team | Design briefs, wireframes, visual QA results, design system |
| 5 | **Engineering Mission Control** | Hermes, Kimi K3, Codex | Active tasks, subtasks, agents, worktrees, file ownership, validation |
| 6 | **Quality and Evidence** | Hermes, Claude Code | Test results, gate status, review findings, evidence packages |
| 7 | **Commercial Safety** | Amjad, Hermes | Protected zone status, R4 task state, fixture health, pricing integrity |
| 8 | **Knowledge** | All | Decision register, regression register, architecture, design system |
| 9 | **Releases** | Amjad, Hermes | Deployment history, release notes, rollback packages |
| 10 | **Operations** | Hermes | CI/CD status, GitHub integration, preview environments, monitoring |

---

## Core Principles

1. **No invented progress numbers.** Do not show "72% complete" without a documented formula.
2. **Evidence-backed states.** Every status must derive from actual records.
3. **Prefer stage progress.** "Contract: complete, Implementation: complete, Review: in progress"
4. **Read from source records.** Task contracts, evidence packages, review findings, deployment logs.
5. **No inference from conversation text alone.** Dashboard data must come from structured records.

---

## Module Details

### 1. Executive Overview

- Active tasks count by state
- Blocked tasks requiring attention
- Tasks ready for Amjad approval
- Recent deployments
- Critical alerts (failed gates, scope violations)
- Prohibited: don't show "velocity" or "productivity" without defined metrics

### 5. Engineering Mission Control

- Parent task → subtask hierarchy
- Active agents and their current task
- Worktree assignments per agent
- File ownership map (who owns which files)
- Dependency graph (which subtasks depend on which)
- Collision alerts (overlapping file ownership)
- Validation status per subtask
- Integration status
- Rollback readiness

### 7. Commercial Safety

- Protected zone integrity status
- R4 task lifecycle (serialized, no parallel writes)
- Business fixture pass/fail dashboard
- Pricing reproducibility check
- Audit event log (recent protected zone accesses)

### 8. Knowledge

- **Decision Register:** Searchable, filterable list of DEC-XXX-NNN records with status
- **Regression Register:** Active/guarded/retired regressions, last verified dates
- **Architecture:** System diagrams, component maps, technology decisions
- **Design System:** Token library, component catalog, version history

---

## Empty States

Every module must handle the empty state gracefully:
- "No active tasks" — not an error, just nothing in flight
- "No agents running" — all worktrees idle
- "No reviews pending" — quality gates clear
- "No decisions recorded" — register is empty

---

## Alerts

Real-time notifications for:
- Task blocked (state = BLOCKED)
- Gate failure (any required gate)
- Scope violation (SCOPE_EXCEEDED)
- Unreviewed finding (finding without adjudication)
- Protected zone access (audit event)
- Stale worktree (>24h inactive)

---

## Data Architecture

All dashboard data sources from `.hermes/`:
- Task states from task-state-event log
- Evidence from evidence packages
- Reviews from review reports
- Decisions from decision register files
- Regressions from regression register files

---

## Deferred to HOS-4

Full UI implementation deferred. HOS-1 implements only the event foundation and data schemas that power it. HOS-4 delivers the MVP dashboard.

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*