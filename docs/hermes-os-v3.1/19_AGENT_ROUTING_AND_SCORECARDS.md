# 19 — Agent Routing and Scorecards

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

Evidence-based agent routing replaces intuition-based builder selection. Scorecards track per-builder performance so Hermes can route tasks to the agent with the strongest historical record for that task category.

---

## Default Routing Rules

| Task Type | Risk | Primary | Fallback |
|---|---|---|---|
| New feature, multi-file | R1-R2 | Kimi K3 | Codex |
| Vertical slice (front+back) | R1-R2 | Kimi K3 | Codex |
| Large-context repo work | Any | Kimi K3 | — |
| Controlled refactor | R2 | Kimi K3 | Codex |
| Narrow bug fix (1-3 files) | R1-R2 | Codex | Kimi K3 |
| Sensitive behavior preservation | R2-R3 | Codex | Kimi K3 |
| Kimi fails 2 correction cycles | Any | Codex | — |
| Kimi exceeds scope | Any | Codex | — |
| Independent challenger implementation | R3-R4 | Codex | — |
| Documentation | R0-R1 | Documentation Agent | Kimi K3 |
| Test creation | R1-R2 | Test Agent | Kimi K3 |

---

## Builder Scorecard Schema

```yaml
scorecard:
  agent: kimi-k3|codex
  reporting_period:
    start:
    end:
  
  tasks:
    total: N
    by_category:
      visual: N
      bug_fix: N
      feature: N
      business_logic: N
      data_model: N
      infrastructure: N
    
    by_risk:
      r1: N
      r2: N
      r3: N
      r4: N
  
  performance:
    first_pass_build_rate: 0.N
    first_pass_test_rate: 0.N
    scope_violations: N
    protected_zone_violations: N
    reviewer_blockers_per_task: N.N
    reviewer_high_findings_per_task: N.N
    avg_correction_cycles: N.N
    regression_introduced: N
    human_acceptance_rate: 0.N
  
  cost:
    avg_cost_per_task: $N.NN
    total_cost: $N.NN
    avg_execution_time_minutes: N
  
  outcomes:
    merged_without_correction: N
    merged_after_correction: N
    rejected: N
    cancelled: N
```

---

## Routing Decision Rules

1. **Sample size matters.** Do not route from scores until ≥5 tasks in the category.
2. **Default routing applies** until scorecard data is sufficient.
3. **Risk overrides score.** R3-R4 tasks default to Kimi K3 regardless of Codex scores unless Codex has demonstrated superior R3-R4 performance.
4. **Correction cycles are a strong signal.** An agent with >2 avg correction cycles in a category should not be routed there.
5. **Scope violations are disqualifying for that category.** If Kimi exceeds scope 2+ times in business_logic tasks, route to Codex for that category.
6. **Hermes documents routing decision** with reason and supporting scorecard data in the task contract.

---

## Current State

No scorecards are populated. The v1.0 BUILDER_SCORECARD_TEMPLATE.md is a 17-line template with no data.

First scorecards should be created after HOS-1 implementation, populated from the first 5 tasks that use the new contract standard.

---

## What Agents Must Not Do

- No agent may route work to itself
- No agent may select its own reviewer
- No agent may influence routing by reporting inflated performance
- Hermes owns routing decisions exclusively

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*