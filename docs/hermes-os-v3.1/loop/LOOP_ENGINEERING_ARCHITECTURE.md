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
            ┌─────────┴──────────┐
            │ Loop Controller    │ ← Subordinate capability
            │ (Hermes delegates) │
            └─────────┬──────────┘
                      |
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   DISCOVERY     EXECUTION     VERIFICATION
   (eligible      (builder      (independent
    work)          agent)        evaluator)
        │             │             │
        └─────────────┼─────────────┘
                      ▼
                 HUMAN GATE
                 (approval)
                      |
                 LOOP MEMORY
                 (state + evidence + decisions)
```

---

## 3. Loop Controller

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

## 8. Initial Pilots (Planning Only)

| ID | Name | Risk | Purpose |
|---|---|---|---|
| LOOP-PILOT-001 | CI Failure Triage | R1 | Inspect failed checks, classify causes, propose contract. Read-only. |
| LOOP-PILOT-002 | Governance Drift Check | R1 | Check schema/policy/decision consistency. Read-only. |
| LOOP-PILOT-003 | Regression Verification | R1-R2 | Run approved fixtures, report failures. No production code changes. |
| LOOP-PILOT-004 | Documentation Drift | R1 | Identify docs conflicting with schemas/policies. Propose corrections only. |

---

*Part of Hermes Product OS v3.1 — Loop Engineering Planning.*