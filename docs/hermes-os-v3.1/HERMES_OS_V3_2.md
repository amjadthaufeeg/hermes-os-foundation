# Hermes Product OS v3.2 — Operating Model Refinement

**Status:** Specification | **Version:** 3.2 | **Date:** 1 Aug 2026

---

## 1. Purpose

v3.2 removes ambiguity from the v3.1 operating model. It introduces earned authority, clarifies the human-control boundary, formally separates agents from tools, and adds delivery-oriented maturity tracking.

This is a planning and documentation refinement. No runtime activation. No new architectural layers beyond what is specified here.

After v3.2 is merged, the operating model is **feature-frozen** until real operational evidence justifies another change.

---

## 2. Maturity Model

Every capability, loop, agent role, and operational component must carry its current maturity state.

### State Definitions

| Dimension | Values |
|---|---|
| **SPECIFICATION** | COMPLETE / PARTIAL / PLACEHOLDER / NOT_DEFINED |
| **IMPLEMENTATION** | IMPLEMENTED / NOT_IMPLEMENTED |
| **ACTIVATION** | ACTIVE / INACTIVE / PAUSED |
| **OPERATIONAL MATURITY** | UNPROVEN / PILOT / PROBATION / PROVEN / SUSPENDED |

### How Maturity Tracks

```
SPECIFICATION: NOT_DEFINED → PLACEHOLDER → PARTIAL → COMPLETE
IMPLEMENTATION: NOT_IMPLEMENTED → IMPLEMENTED
ACTIVATION: INACTIVE → ACTIVE (requires Amjad)
OPERATIONAL MATURITY: UNPROVEN → PILOT → PROBATION → PROVEN
                                                    ↘ SUSPENDED
```

- **UNPROVEN:** Spec exists, never run in real conditions.
- **PILOT:** Running in controlled, read-only or test-only scope. No production impact.
- **PROBATION:** Running in production scope but under heightened oversight. Status reviewed every cycle.
- **PROVEN:** Demonstrated reliability over ≥3 consecutive successful cycles with clean independent review and no human override. Earned, not declared.
- **SUSPENDED:** Previously proven but paused due to failure, evidence gap, or human decision.

### Maturity Cannot Be Self-Declared

An agent cannot declare itself PROVEN. Operational maturity is assigned by Hermes after independent review and Amjad acknowledgment. PROVEN status can be revoked by Hermes or Amjad at any time.

---

## 3. Agents vs. Tools — Formal Separation

### Agents (Directed Actors)

Agents are AI systems that receive task contracts, make implementation decisions, and produce work. They operate within Hermes-defined bounds.

| Agent | Type | Role | Maturity |
|---|---|---|---|
| **Kimi K3** | Agent | Primary Builder | UNPROVEN (pilot pending) |
| **Codex** | Agent | Precision Builder | UNPROVEN (pilot pending) |

### Tools (Directed Instruments)

Tools are deterministic or AI-based systems that perform specific verification, review, or rendering functions. They do not make implementation decisions. They are invoked and their output is adjudicated.

| Tool | Type | Function | Maturity |
|---|---|---|---|
| **Claude Code** | Tool | Independent Reviewer (read-only) | UNPROVEN (pilot pending) |
| **Replit** | Tool | Live Preview (read-only) | UNPROVEN |
| **GitHub Actions** | Tool | CI/CD, validation gates | PROVEN |
| **GitHub** | Tool | Source of truth, branch protection | PROVEN |
| **OpenCode** | Tool | Review path when native Claude unavailable | UNPROVEN |
| **DeepSeek V4 Pro** | Tool | Optional non-blocking research/challenger | PILOT |

### The Distinction Matters

- An **Agent** earns trust through proven delivery. Its output goes through review.
- A **Tool** produces output that is either accepted or rejected by Hermes. It does not earn trust — it is validated every time.

Agents may advance in maturity. Tools remain tools — their output is evidence, not authority.

---

## 4. Earned Authority

Agents do not start with full authority. Authority is earned through demonstrated reliable performance in controlled conditions.

### Authority Progression

```
PILOT (read-only or R1)
  ↓ (clean review, no scope violations, all evidence passes)
PROBATION (R1-R2, heightened oversight)
  ↓ (≥3 consecutive cycles, all gates pass, no human override)
PROVEN (R1-R4, standard oversight)
  ↓ (failure, evidence gap, scope violation)
SUSPENDED (requires investigation, may return to PILOT)
```

### What Earned Authority Grants

| Level | Scope | Oversight | Review | Merge |
|---|---|---|---|---|
| PILOT | Read-only or R1 only | Hermes reviews every output | Mandatory | Never |
| PROBATION | R1-R2 | Hermes reviews evidence package | Mandatory | Hermes-only |
| PROVEN | R1-R4 | Standard gates | Mandatory for R3+ | Hermes with Amjad for R4 |

### What Earned Authority Never Grants

No agent — regardless of maturity — may:
- Approve its own task contracts
- Unlock protected zones without authorization
- Accept its own review findings
- Merge into protected branches independently
- Deploy to production
- Override Amjad

Earned authority reduces oversight depth, not oversight existence.

---

## 5. Human Control Clarification

### Amjad's Irrevocable Authority

Amjad is the Product Owner and final authority. The following can only be authorized by Amjad:

| Decision | Delegable? |
|---|---|
| Product direction | No — Amjad only |
| Business rule changes | No — Amjad only |
| Commercial behaviour changes | No — Amjad only |
| Pricing changes | No — Amjad only |
| Protected zone unlock (R4) | No — Amjad only |
| PROVEN status conferral | No — Amjad acknowledgment required |
| Activation of new capability | No — Amjad only |
| Activation of new loop | No — Amjad only |
| Production deployment | No — Amjad only |
| Irreversible actions | No — Amjad only |
| v3.3 feature-unfreeze | No — Amjad only |

### Hermes's Derived Authority

Hermes derives authority from Amjad. Hermes may:

| Decision | Scope |
|---|---|
| Task contract approval | Within approved capability and risk ceiling |
| Builder routing | Based on documented routing rules |
| Review finding adjudication | Accept/reject/defer reviewer findings |
| Merge (R1-R3) | After all gates pass |
| Activation freeze/thaw | Temporary within a cycle |
| PROVEN status recommendation | Submitted to Amjad for acknowledgment |
| Evidence rejection | On stale, missing, or commit-mismatched evidence |

### Human Gate Is Not a Suggestion

Every human gate is mandatory. No timeout override. No auto-approval. No silent escalation. When a human gate is pending, the loop or task pauses and waits.

---

## 6. Delivery Measures

Success is measured by delivered, verified, reviewed, accepted work — not by activity.

### Cycle Completion Definition

A task cycle is complete when:
1. Implementation submitted with evidence
2. All automated gates pass
3. Independent review complete
4. All accepted findings resolved
5. Hermes marks READY_FOR_AMJAD
6. Amjad approves (for R2+ or when required by contract)

### Delivery Metrics (Advisory)

| Metric | Definition |
|---|---|
| **Cycle success rate** | Completed cycles / started cycles |
| **First-pass rate** | Cycles passing all gates on first submission |
| **Review burden** | Average findings per cycle (trending down = improvement) |
| **Scope compliance** | Cycles without scope violations / total cycles |
| **Correction cycles** | Average corrections per cycle |
| **Human overrides** | Count of Amjad interventions (trending down = trust earned) |
| **Evidence rejections** | Count of stale/missing evidence incidents |
| **Time to proven** | Cycles from PILOT to PROVEN |

These are advisory. They inform routing and maturity decisions. They do not replace human judgment.

### What Delivery Is Not

- Task count is not delivery.
- Agent activity is not delivery.
- Lines of code written is not delivery.
- Promises or self-assessments are not delivery.

Only completed, verified, reviewed, and accepted evidence constitutes delivery.

---

## 7. v3.2 Operating Principles

### P1 — Evidence Before Trust
Trust is earned through repeated evidence of reliable performance. No agent starts trusted.

### P2 — Human Gate Is Absolute
No automated bypass. No timeout override. No silent escalation. When human judgment is required, the system waits.

### P3 — Separation of Generation and Evaluation
The agent that produces work is never the sole evaluator of that work. Every output faces independent verification.

### P4 — Default Closed
All protected zones, elevated permissions, and autonomous actions default to closed. They are opened only by explicit, recorded authorization.

### P5 — Delivery Over Activity
What is delivered, verified, and accepted is the only measure of progress. Activity without evidence is not progress.

### P6 — Maturity Is Earned
Operational maturity advances through demonstrated reliable performance in controlled conditions. It is never self-declared and can be revoked.

### P7 — Feature Freeze Is Binding
After v3.2 merge, the operating model is frozen. Changes require real operational evidence — not speculation, not redesign impulse, not preference.

---

## 8. Implementation Scope

v3.2 changes no production code. It updates:

| File | Change |
|---|---|
| `docs/hermes-os-v3.1/02_ORGANIZATIONAL_MODEL.md` | Maturity states, agent/tool separation, earned authority |
| `docs/hermes-os-v3.1/HERMES_OS_V3_2.md` | This document — operating model refinement |

No new divisions. No new agents. No new architectural layers. No runtime activation.

---

## 9. Rollback

```bash
git revert <merge-commit>
```

Documentation-only. No production impact.

---

*Hermes Product OS v3.2 — Feature-frozen after merge. Changes require real operational evidence.*