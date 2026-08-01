# Hermes Product OS v3.1 — Loop Engineering Architecture

**Status:** Planning | **Release:** Loop Engineering

---

## 1. What Is Loop Engineering

Loop engineering is a governed execution capability that formalizes repeatable, evidence-gated, agent-based loops. Each loop is bounded by explicit contracts, budgets, human gates, and proof requirements. Loops reduce repeated manual prompting without reducing accountability.

A loop is not autonomous. Hermes remains the sole orchestrator. Every irreversible or high-risk action returns to a human gate.

---

## 2. Architecture

```
                     AMJAD
                Product Owner
                      |
                 ┌────┴────┐
                 │  HERMES │ ← Sole Orchestrator
                 └────┬────┘
                      |
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  Capability      Capability     Capability
  Manager         Manager        Manager     ← Organizational layer
  (Commercial)    (Design)       (Health)
        │             │             │
        └─────────────┼─────────────┘
                      |
            ┌─────────┴──────────┐
            │ Loop Controller    │ ← Execution layer
            │ (per capability)   │
            └─────────┬──────────┘
                      |
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   DISCOVERY     EXECUTION     VERIFICATION
                      │
                      ▼
                 HUMAN GATE
                      |
                 LOOP MEMORY
```

Each Capability owns one or more loops. Capability Managers report health and status upward. Loop Controllers execute downward. Hermes retains final authority over all transitions.

---

## 3. Capability Engineering

Capability Engineering is the organizational layer above Loop Engineering. A Capability represents an enduring business responsibility. Capabilities own loops. Loops execute. Capabilities report.

### Capability Hierarchy

```
Hermes
 ↓
Capability Manager
 ↓
Loop Controller
 ↓
Task Controller
 ↓
Approved Builders and Reviewers
```

### Defined Capabilities

| Capability | Purpose | Owner |
|---|---|---|
| **Commercial Safety** | Pricing, offers, occupancy, taxes, commissions, reconciliation integrity | Hermes |
| **Design Quality** | Design-system compliance, visual QA, accessibility, interaction polish | Design Studio |
| **Documentation Health** | Spec consistency, schema accuracy, policy currency, decision freshness | Hermes |
| **Release Readiness** | CI health, fixture pass rates, rollback readiness, deployment safety | Hermes |
| **Engineering Health** | Build health, test coverage, scope compliance, protected-zone integrity | Hermes |
| **Research Intelligence** | Competitive analysis, UX patterns, technology assessment, evidence briefs | Research Division |
| **Knowledge Integrity** | Decision register, regression register, memory accuracy, archival health | Hermes |
| **Operations** | Deployment status, preview environments, monitoring readiness, cost tracking | Hermes |

### Capability Specification

Every Capability must define:

```yaml
capability_id: CAP-XXX
name: "Design Quality"
purpose: "Ensure visual and interaction quality across all products"
owner: design-studio
participating_roles: [ux-architect, product-designer, visual-designer, visual-qa]
managed_loops:
  - LOOP-XXX-001  # Visual regression check
  - LOOP-XXX-002  # Accessibility audit
success_metrics:
  - "Design-system compliance score >= 4"
  - "Accessibility baseline met on all active screens"
health_status: HEALTHY | DEGRADED | AT_RISK | UNKNOWN
evidence_sources:
  - "Visual QA reports"
  - "Accessibility audit logs"
  - "Design review findings"
escalation_rules:
  - "Status AT_RISK for >24h → alert Amjad"
human_gates:
  - before_merge: true
  - before_deploy: true
```

### Capability Health Status

| Status | Meaning |
|---|---|
| HEALTHY | All managed loops passing, metrics within targets |
| DEGRADED | One or more loops in non-blocking failure |
| AT_RISK | Blocking failure or budget exceeded on critical loop |
| UNKNOWN | Insufficient evidence to determine health |

Health status rolls up to Command Center Capability Dashboard. The dashboard reports capability health, not raw loop counts.

---

## 4. Loop Controller

The Loop Controller is a subordinate Hermes capability. It does not replace Hermes — it operates within bounds Hermes defines.

### Permitted

- Evaluate loop eligibility for approved loop contracts
- Initialize loop runs with isolated state
- Discover eligible work items from defined sources
- Create proposed task contracts from loop templates
- Dispatch approved builder agents
- Track execution progress
- Invoke deterministic verification
- Enforce budgets (runtime, retries, scope)
- Save run state and evidence
- Stop and escalate when gates are not met

### Prohibited

- Change product objectives
- Approve its own task contracts (always requires Hermes or Amjad)
- Unlock protected zones
- Accept independent-review findings
- Merge code
- Deploy
- Close high-risk work
- Override Amjad decisions
- Become a second orchestrator

---

## 4. Loop Lifecycle

```
LOOP_PROPOSED ──→ LOOP_APPROVED
                       │
                       ▼
                  DISCOVERING
                       │
                       ▼
              TASK_SELECTED
                       │
                       ▼
              CONTRACT_DRAFTED
                       │
                       ▼ (human gate)
          AWAITING_CONTRACT_APPROVAL
                       │
                       ▼
                   EXECUTING
                       │
                       ▼
                  VALIDATING
                       │
                   ┌───┴───┐
                   ▼       ▼
              EVALUATING  CORRECTING
                   │       │
                   ▼       ▼ (up to max_repair_cycles)
          AWAITING_HUMAN_GATE
                   │
           ┌───────┼───────┐
           ▼       ▼       ▼
      SUCCEEDED   FAILED   CANCELLED
           │       │       │
           └───────┴───────┘
                   │
                   ▼
              ARCHIVED
```

Failure states: BUDGET_EXCEEDED, SCOPE_EXCEEDED, PROVIDER_TIMEOUT, EVIDENCE_REJECTED.

---

## 5. Proof-or-Stop Rule

Agent output is a claim, not proof. A loop advances only when current evidence tied to the exact source commit satisfies the relevant gate.

Required evidence may include: task contract, source commit, changed-file report, scope result, protected-zone result, build, tests, fixtures, review, finding decisions, rollback, human approval.

When required evidence is absent, stale, or tied to a different commit → **STOP**. Set **EVIDENCE_REJECTED**.

---

## 6. Generator-Evaluator Separation

The agent implementing work is never the sole evaluator.

Required path: Builder → Deterministic validation → Independent evaluator → Hermes finding triage → Approved corrections → Builder.

The evaluator is review-only initially. Hermes accepts, rejects, or defers every material finding.

---

## 7. Isolation

Every loop run operates in an isolated context:

- Feature branch (never main)
- Dedicated worktree or equivalent workspace boundary
- Explicit file-ownership boundary
- Single-writer rule enforced

No loop may merge itself or write directly to main.

---

## 9. Initial Pilots (Planning Only)

| ID | Name | Capability | Risk | Purpose |
|---|---|---|---|---|
| LOOP-PILOT-001 | CI Failure Triage | Engineering Health | R1 | Inspect failed checks, classify causes, propose contract. Read-only. |
| LOOP-PILOT-002 | Governance Drift Check | Documentation Health | R1 | Check schema/policy/decision consistency. Read-only. |
| LOOP-PILOT-003 | Regression Verification | Engineering Health | R1-R2 | Run approved fixtures, report failures. No production code changes. |
| LOOP-PILOT-004 | Documentation Drift | Knowledge Integrity | R1 | Identify docs conflicting with schemas/policies. Propose corrections only. |

---

## 10. Migration Path

Loop Engineering was architected first. Capability Engineering is the layer above it.

**Phase 1 (current):** Loop Engineering architecture. Pilots operate as standalone loops with direct Hermes oversight.

**Phase 2:** Capability Engineering specification. Capability definitions formalized. Loop contracts assigned to capabilities.

**Phase 3:** Capability Managers activated. Loops report through capabilities. Command Center shows capability health.

**Phase 4:** Full Capability Dashboard. All 8 capabilities reporting. Health status drives prioritization.

No loop behavior changes are required at each phase. Capabilities are organizational — loops execute identically regardless.

---

*Part of Hermes Product OS v3.1 — Loop Engineering Planning.*