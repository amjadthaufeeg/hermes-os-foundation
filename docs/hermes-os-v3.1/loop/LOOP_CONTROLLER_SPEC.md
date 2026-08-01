# Loop Controller — Responsibility Specification

**Status:** Planning | **Release:** Loop Engineering

---

## Authority

The Loop Controller is a **subordinate** Hermes capability. It operates only within bounds defined by approved loop contracts. Hermes delegates execution authority; it does not delegate orchestration authority.

## Permitted Operations

| Operation | Description |
|---|---|
| `evaluate_eligibility` | Check whether a loop contract's trigger conditions are met |
| `initialize_run` | Create isolated run state from contract template |
| `load_prior_state` | Restore state from prior loop run if continuation is appropriate |
| `discover_work` | Query defined sources for eligible work items |
| `select_item` | Pick highest-priority eligible work item |
| `draft_task_contract` | Create proposed task contract from contract template + discovered context |
| `dispatch_builder` | Route validated contract to approved builder agent |
| `track_execution` | Monitor builder progress and collect output |
| `run_verification` | Execute deterministic checks specified in loop contract |
| `invoke_evaluator` | Dispatch independent evaluator with evidence package |
| `triage_findings` | Route evaluator findings to Hermes for accept/reject/defer |
| `enforce_budget` | Halt execution if runtime, retry, or scope budgets are exceeded |
| `save_state` | Persist loop run state and evidence |
| `stop_and_escalate` | Halt execution, preserve state, return to human gate |

## Prohibited Operations

| Operation | Reason |
|---|---|
| `approve_own_contract` | Contracts must pass Hermes or Amjad approval gate |
| `unlock_protected` | Protected zones require explicit authorization |
| `accept_review_findings` | Hermes alone decides finding disposition |
| `merge` | Only Hermes may merge after all gates |
| `deploy` | Production deployment requires Amjad authorization |
| `close_high_risk` | R3-R4 tasks require Amjad approval |
| `override_amjad` | Amjad is final authority — no override possible |
| `become_orchestrator` | Loop Controller is a tool, not a second orchestrator |

## State Ownership

Hermes controls all state transitions. The Loop Controller may propose transitions; Hermes executes them.

---

*Part of Hermes Product OS v3.1 — Loop Engineering Planning.*