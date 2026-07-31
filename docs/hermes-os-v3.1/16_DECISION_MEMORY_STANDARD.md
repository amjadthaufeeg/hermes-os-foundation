# 16 — Decision Memory Standard

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

Durable architectural, product, and commercial decisions that survive across tasks, sessions, and agents. The Decision Register prevents re-litigation and ensures all agents operate from the same authority baseline.

---

## Decision Record Schema

```yaml
decision_id: DEC-XXX-NNN
title:
status: proposed|approved|locked|superseded|deprecated
date:
owner: amjad
applies_to: avoa|hermes-os|all
category: architecture|product|commercial|security|governance|design

decision: >
  Full text of the decision.

reason: >
  Why this decision was made.

alternatives_considered:
  - option:
    rejected_because:

supersedes:
  - DEC-XXX-NNN

superseded_by:
  - DEC-XXX-NNN

related_tasks:
  - TASK-XXXX
  - TASK-YYYY

last_reviewed:
```

---

## Status Lifecycle

```
proposed → approved → locked
                        ↓
                    superseded → deprecated
```

- **Proposed:** Drafted, not yet approved
- **Approved:** Amjad has approved; effective but can be amended
- **Locked:** Cannot be changed without explicit Amjad authorization; treated as binding authority
- **Superseded:** Replaced by a newer decision
- **Deprecated:** No longer applicable

---

## Proposed v3.1 Decisions

| ID | Title | Category |
|---|---|---|
| DEC-HOS-001 | Hermes remains the sole orchestrator | governance |
| DEC-HOS-002 | Kimi K3 is the primary builder | governance |
| DEC-HOS-003 | Claude Code is review-only initially | governance |
| DEC-HOS-004 | Codex is precision, fallback and recovery builder | governance |
| DEC-HOS-005 | GitHub is the authoritative source of truth | architecture |
| DEC-HOS-006 | Evidence determines readiness | governance |
| DEC-HOS-007 | Hermes uses a department-based operating model | governance |
| DEC-HOS-008 | Hermes includes a formal Design Studio | governance |
| DEC-HOS-009 | Parallel Controller is subordinate to Hermes | governance |
| DEC-HOS-010 | Single-writer file ownership is mandatory | architecture |
| DEC-HOS-011 | Writing sub-agents use isolated worktrees | architecture |
| DEC-HOS-012 | R4 parallel production-code editing is prohibited initially | governance |
| DEC-HOS-013 | Engineering Mission Control is a module inside Command Center | architecture |
| DEC-HOS-014 | Material UI work requires a UI contract and visual evidence | governance |
| DEC-HOS-015 | Minimum CI belongs in the first foundation release | architecture |
| DEC-HOS-016 | Routine direct agent pushes to master are prohibited | architecture |
| DEC-AVOA-PRICING-001 | Final commercial calculations remain deterministic | commercial |

DEC-HOS-001 and DEC-AVOA-PRICING-001 are already **locked**. Remaining records are **proposed** — awaiting Amjad approval.

---

## Usage

- Hermes retrieves relevant decisions before drafting task contracts
- Task contracts cite applicable decision IDs
- Claude receives relevant decisions in review package
- New decisions are proposed by Hermes, approved by Amjad
- Locked decisions require explicit Amjad authorization to change

---

## Storage

```
.hermes/registers/decisions/
├── DEC-HOS-001.yaml
├── DEC-HOS-002.yaml
├── ...
└── DEC-AVOA-PRICING-001.yaml
```

Each file is a self-contained YAML record.

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*